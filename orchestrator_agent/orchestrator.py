import asyncio
import logging
import os
import hashlib
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
import uuid
import json

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from a2a_agents.hr_agent import HRAgent
from a2a_agents.finance_agent import FinanceAgent
from a2a_agents.legal_agent import LegalAgent
from auth.okta_auth import OktaAuth
from auth.okta_scopes import OKTA_SCOPES, get_default_hr_scopes, get_default_finance_scopes, get_default_legal_scopes

logger = logging.getLogger(__name__)

class OrchestratorAgent:
    """
    Orchestrator Agent for coordinating complex multi-department workflows
    Uses LangGraph for workflow orchestration and A2A token exchange
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.3,
            max_tokens=1500
        )
        
        # Initialize auth first
        self.okta_auth = OktaAuth()
        
        # Initialize A2A agents with OktaAuth for token exchange
        self.hr_agent = HRAgent(okta_auth=self.okta_auth)
        self.finance_agent = FinanceAgent(okta_auth=self.okta_auth)
        self.legal_agent = LegalAgent(okta_auth=self.okta_auth)
        
        # Workflow state management
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        
        # Build LangGraph workflow
        self.workflow_graph = self._build_workflow_graph()
    
    def _create_minimal_user_info(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create minimal user_info for LLM with privacy controls.
        Security: Remove all token claims, internal IDs, and unnecessary metadata.
        
        Privacy Levels (controlled by env var ALLOW_PII_IN_LLM_PROMPTS):
        - False (default): Anonymous user ID only (maximum privacy, GDPR compliant)
        - True: Email + name (enhanced UX, requires consent)
        """
        minimal = {}
        
        # Privacy setting: Check if PII (email/name) is allowed in LLM prompts
        # Default: False (maximum privacy - use anonymous ID only)
        allow_pii = os.getenv("ALLOW_PII_IN_LLM_PROMPTS", "false").lower() == "true"
        
        if allow_pii:
            # Privacy Level 3: Enhanced UX - Include email/name (with consent)
            # WARNING: This sends PII to third-party LLM. Ensure user consent and org policy allows.
            if user_info.get("email"):
                minimal["email"] = user_info["email"]
            if user_info.get("name"):
                minimal["name"] = user_info["name"]
            logger.info("[PRIVACY] PII enabled: sending email/name to LLM")
        else:
            # Privacy Level 1: Maximum Privacy - Anonymous ID only
            # Generate consistent anonymous ID from email hash (non-reversible)
            email = user_info.get("email", "anonymous")
            # Use consistent salt from env or default
            salt = os.getenv("ANONYMOUS_ID_SALT", "streamward-privacy-salt")
            anonymous_id = hashlib.sha256(f"{email}{salt}".encode()).hexdigest()[:16]
            minimal["user_id"] = f"user_{anonymous_id}"  # e.g., "user_a3f5b2c1d9e8f7a6"
            logger.info(f"[PRIVACY] PII disabled: using anonymous user_id={minimal['user_id']}")
        
        logger.debug(f"[USER_INFO] Sanitized: includes={list(minimal.keys())}")
        
        return minimal

    def _build_workflow_graph(self) -> StateGraph:
        """Build LangGraph workflow for orchestrating multi-agent processes"""
        
        # Define the state as TypedDict (required by LangGraph)
        class WorkflowState(TypedDict):
            messages: List[Any]
            workflow_type: str
            parameters: Dict[str, Any]
            user_info: Dict[str, Any]
            workflow_id: str
            current_step: str
            hr_result: Optional[Dict[str, Any]]
            finance_result: Optional[Dict[str, Any]]
            legal_result: Optional[Dict[str, Any]]
            final_result: Optional[Dict[str, Any]]
            error: Optional[str]
            agent_flow: List[Dict[str, Any]]  # Track agent call sequence
            token_exchanges: List[Dict[str, Any]]  # Track all token exchanges
        
        # Create the graph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("orchestrator", self._orchestrator_node)
        workflow.add_node("hr_agent", self._hr_agent_node)
        workflow.add_node("finance_agent", self._finance_agent_node)
        workflow.add_node("legal_agent", self._legal_agent_node)
        workflow.add_node("coordination", self._coordination_node)
        workflow.add_node("finalization", self._finalization_node)
        
        # Set entry point (graph needs an entry point from START)
        workflow.set_entry_point("orchestrator")
        
        # Add conditional routing from orchestrator to agent(s) based on workflow type
        def route_to_agent(state: Dict[str, Any]) -> str:
            """Route to specific agent(s) based on workflow type"""
            workflow_type = state.get("workflow_type", "")
            
            # For employee_onboarding, we need all 3 agents - route to HR first
            if "employee" in workflow_type or "onboard" in workflow_type:
                return "hr_agent"
            elif "hr" in workflow_type:
                return "hr_agent"
            elif "financial" in workflow_type or "finance" in workflow_type or "transaction" in workflow_type or "compliance" in workflow_type or "review" in workflow_type:
                return "finance_agent"
            elif "legal" in workflow_type:
                return "legal_agent"
            else:
                # Default to finance for now
                return "finance_agent"
        
        workflow.add_conditional_edges(
            "orchestrator",
            route_to_agent,
            {
                "hr_agent": "hr_agent",
                "finance_agent": "finance_agent",
                "legal_agent": "legal_agent"
            }
        )
        
        # Add conditional routing from HR agent - if employee_onboarding, continue to Finance
        def route_from_hr(state: Dict[str, Any]) -> str:
            """Route from HR agent - if employee_onboarding, continue to Finance and Legal"""
            workflow_type = state.get("workflow_type", "")
            hr_result = state.get("hr_result")
            
            # If employee onboarding and HR is done, continue to Finance
            if ("employee" in workflow_type or "onboard" in workflow_type) and hr_result:
                logger.info("[WORKFLOW_ROUTING] HR complete, routing to Finance Agent")
                return "finance_agent"
            else:
                return "coordination"
        
        workflow.add_conditional_edges(
            "hr_agent",
            route_from_hr,
            {
                "finance_agent": "finance_agent",
                "coordination": "coordination"
            }
        )
        
        # Add conditional routing from Finance agent - if employee_onboarding or compliance_review, continue to Legal
        def route_from_finance(state: Dict[str, Any]) -> str:
            """Route from Finance agent - if employee_onboarding or compliance_review, continue to Legal"""
            workflow_type = state.get("workflow_type", "")
            finance_result = state.get("finance_result")
            
            # If employee onboarding or compliance review and Finance is done, continue to Legal
            if (("employee" in workflow_type or "onboard" in workflow_type) or ("compliance" in workflow_type or "review" in workflow_type)) and finance_result:
                logger.info("[WORKFLOW_ROUTING] Finance complete, routing to Legal Agent")
                return "legal_agent"
            else:
                return "coordination"
        
        workflow.add_conditional_edges(
            "finance_agent",
            route_from_finance,
            {
                "legal_agent": "legal_agent",
                "coordination": "coordination"
            }
        )
        
        # From Legal agent, always go to coordination
        workflow.add_edge("legal_agent", "coordination")
        workflow.add_edge("coordination", "finalization")
        workflow.add_edge("finalization", END)
        
        return workflow.compile()

    async def execute_workflow(self, workflow_type: str, parameters: Dict[str, Any], user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a complex multi-agent workflow
        """
        try:
            workflow_id = str(uuid.uuid4())
            
            logger.info(f"[WORKFLOW] Starting {workflow_type} workflow_id={workflow_id}")
            
            # Initialize workflow state
            initial_state = {
                "messages": [HumanMessage(content=f"Workflow: {workflow_type} with parameters: {parameters}")],
                "workflow_type": workflow_type,
                "parameters": parameters,
                "user_info": user_info,
                "workflow_id": workflow_id,
                "current_step": "orchestrator",
                "agent_flow": [],  # Track agent calls and token exchanges
                "token_exchanges": []  # Track all token exchanges
            }
            
            # Store active workflow
            self.active_workflows[workflow_id] = {
                "type": workflow_type,
                "status": "running",
                "started_at": datetime.now(),
                "user_info": user_info,
                "parameters": parameters
            }
            
            # Execute workflow
            result = await self.workflow_graph.ainvoke(initial_state)
            
            # Update workflow status
            self.active_workflows[workflow_id]["status"] = "completed"
            self.active_workflows[workflow_id]["completed_at"] = datetime.now()
            self.active_workflows[workflow_id]["result"] = result.get("final_result")
            
            # Capture source user token (for display in UI)
            source_user_token = user_info.get("token")
            
            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "response": result.get("final_result", {}).get("response", "Workflow completed successfully"),
                "metadata": {
                    "workflow_type": workflow_type,
                    "execution_time": (datetime.now() - self.active_workflows[workflow_id]["started_at"]).total_seconds(),
                    "agents_involved": ["hr_agent", "finance_agent", "legal_agent"]
                },
                "agent_flow": result.get("agent_flow", []),  # Agent call sequence
                "token_exchanges": result.get("token_exchanges", []),  # All token exchanges
                "source_user_token": source_user_token  # Original user token that initiated the flow
            }
            
        except Exception as e:
            logger.error(f"[WORKFLOW] FAILED workflow_id={workflow_id}: {str(e)}", exc_info=True)
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id]["status"] = "failed"
                self.active_workflows[workflow_id]["error"] = str(e)
            
            return {
                "workflow_id": workflow_id,
                "status": "failed",
                "response": f"Workflow failed: {str(e)}",
                "metadata": {"error": str(e)}
            }

    async def _orchestrator_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrator node - analyzes workflow and prepares for agent coordination"""
        try:
            workflow_type = state["workflow_type"]
            parameters = state["parameters"]
            
            logger.info(f"[ORCHESTRATOR_NODE] Analyzing workflow_type={workflow_type}")
            
            # Analyze workflow requirements
            analysis_prompt = f"""
            Analyze this workflow request and determine which agents need to be involved:
            
            Workflow Type: {workflow_type}
            Parameters: {json.dumps(parameters, indent=2)}
            
            Available Agents:
            - HR Agent: Employee management, benefits, onboarding
            - Finance Agent: Financial transactions, approvals, budgeting
            - Legal Agent: Compliance, contracts, regulatory requirements
            
            Determine which agents should be involved and what information they need.
            """
            
            messages = [
                SystemMessage(content="You are an orchestrator agent that coordinates multi-agent workflows."),
                HumanMessage(content=analysis_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Update state
            state["messages"].append(AIMessage(content=response.content))
            state["current_step"] = "agent_coordination"
            
            return state
            
        except Exception as e:
            logger.error(f"[ORCHESTRATOR_NODE] ERROR: {str(e)}", exc_info=True)
            state["error"] = str(e)
            return state

    async def _hr_agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """HR Agent node - handles HR-related workflow tasks"""
        try:
            workflow_type = state["workflow_type"]
            parameters = state["parameters"]
            user_info = state["user_info"]
            
            logger.info(f"HR Agent processing workflow: {workflow_type}")
            
            # Extract token before sanitizing user_info (security: don't send tokens to LLM)
            user_token = user_info.get("token", "mock-token")
            
            # Create minimal user_info with only essential fields (security: minimize data exposure)
            minimal_user_info = self._create_minimal_user_info(user_info)
            
            # Exchange token for HR agent access (Chat Assistant credentials, HR server scopes)
            hr_token = await self.okta_auth.exchange_token(
                user_token,
                self.okta_auth.hr_audience,
                scope=get_default_hr_scopes()  # HR server scopes
            )
            
            # Track token exchange
            if "token_exchanges" not in state:
                state["token_exchanges"] = []
            state["token_exchanges"].append({
                "from": "Orchestrator",
                "to": "HR Agent",
                "audience": self.okta_auth.hr_audience,
                "scope": get_default_hr_scopes(),
                "token": hr_token
            })
            
            # Track agent call
            if "agent_flow" not in state:
                state["agent_flow"] = []
            state["agent_flow"].append({
                "agent": "hr_agent",
                "step": len(state.get("agent_flow", [])) + 1,
                "timestamp": datetime.now().isoformat(),
                "token_exchange": {
                    "from": "Orchestrator",
                    "to": "HR Agent",
                    "audience": self.okta_auth.hr_audience
                }
            })
            
            # Process through HR agent (pass minimal user_info - only email/name, no token/claims)
            hr_result = await self.hr_agent.process_workflow_task(
                workflow_type,
                parameters,
                minimal_user_info,  # Security: Minimal data - only email/name
                hr_token
            )
            
            state["hr_result"] = hr_result
            state["messages"].append(AIMessage(content=f"HR Agent completed: {hr_result.get('summary', 'Task completed')}"))
            
            return state
            
        except Exception as e:
            logger.error(f"HR Agent node error: {e}")
            state["hr_result"] = {"error": str(e)}
            return state

    async def _finance_agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Finance Agent node - handles financial workflow tasks"""
        try:
            workflow_type = state["workflow_type"]
            parameters = state["parameters"]
            user_info = state["user_info"]
            
            logger.info(f"Finance Agent processing workflow: {workflow_type}")
            
            # Extract token before sanitizing user_info (security: don't send tokens to LLM)
            user_token = user_info.get("token", "mock-token")
            
            # Create minimal user_info with only essential fields (security: minimize data exposure)
            minimal_user_info = self._create_minimal_user_info(user_info)
            
            # Exchange token for Finance agent access (Chat Assistant credentials, Finance server scopes)
            finance_token = await self.okta_auth.exchange_token(
                user_token,
                self.okta_auth.finance_audience,
                scope=get_default_finance_scopes()  # Finance server scopes
            )
            
            # Track token exchange
            if "token_exchanges" not in state:
                state["token_exchanges"] = []
            # Determine source: Orchestrator if first agent, otherwise from previous agent
            previous_agent = state.get("agent_flow", [])[-1]["agent"] if state.get("agent_flow") else None
            source = f"Previous Agent (from agent_flow)" if previous_agent else "Orchestrator"
            if previous_agent == "hr_agent":
                source = "HR Agent"
            
            state["token_exchanges"].append({
                "from": source,
                "to": "Finance Agent",
                "audience": self.okta_auth.finance_audience,
                "scope": get_default_finance_scopes(),
                "token": finance_token
            })
            
            # Track agent call
            if "agent_flow" not in state:
                state["agent_flow"] = []
            state["agent_flow"].append({
                "agent": "finance_agent",
                "step": len(state.get("agent_flow", [])) + 1,
                "timestamp": datetime.now().isoformat(),
                "token_exchange": {
                    "from": source,
                    "to": "Finance Agent",
                    "audience": self.okta_auth.finance_audience
                }
            })
            
            # Process through Finance agent (pass minimal user_info - only email/name, no token/claims)
            finance_result = await self.finance_agent.process_workflow_task(
                workflow_type,
                parameters,
                minimal_user_info,  # Security: Minimal data - only email/name
                finance_token
            )
            
            state["finance_result"] = finance_result
            state["messages"].append(AIMessage(content=f"Finance Agent completed: {finance_result.get('summary', 'Task completed')}"))
            
            return state
            
        except Exception as e:
            logger.error(f"Finance Agent node error: {e}")
            state["finance_result"] = {"error": str(e)}
            return state

    async def _legal_agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Legal Agent node - handles legal workflow tasks"""
        try:
            workflow_type = state["workflow_type"]
            parameters = state["parameters"]
            user_info = state["user_info"]
            
            logger.info(f"Legal Agent processing workflow: {workflow_type}")
            
            # Extract token before sanitizing user_info (security: don't send tokens to LLM)
            user_token = user_info.get("token", "mock-token")
            
            # Create minimal user_info with only essential fields (security: minimize data exposure)
            minimal_user_info = self._create_minimal_user_info(user_info)
            
            # Exchange token for Legal agent access (Chat Assistant credentials, Legal server scopes)
            legal_token = await self.okta_auth.exchange_token(
                user_token,
                self.okta_auth.legal_audience,
                scope=get_default_legal_scopes()  # Legal server scopes
            )
            
            # Track token exchange
            if "token_exchanges" not in state:
                state["token_exchanges"] = []
            # Determine source: from previous agent in flow
            previous_agent = state.get("agent_flow", [])[-1]["agent"] if state.get("agent_flow") else None
            source = "Orchestrator"
            if previous_agent == "hr_agent":
                source = "HR Agent"
            elif previous_agent == "finance_agent":
                source = "Finance Agent"
            
            state["token_exchanges"].append({
                "from": source,
                "to": "Legal Agent",
                "audience": self.okta_auth.legal_audience,
                "scope": get_default_legal_scopes(),
                "token": legal_token
            })
            
            # Track agent call
            if "agent_flow" not in state:
                state["agent_flow"] = []
            state["agent_flow"].append({
                "agent": "legal_agent",
                "step": len(state.get("agent_flow", [])) + 1,
                "timestamp": datetime.now().isoformat(),
                "token_exchange": {
                    "from": source,
                    "to": "Legal Agent",
                    "audience": self.okta_auth.legal_audience
                }
            })
            
            # Process through Legal agent (pass minimal user_info - only email/name, no token/claims)
            legal_result = await self.legal_agent.process_workflow_task(
                workflow_type,
                parameters,
                minimal_user_info,  # Security: Minimal data - only email/name
                legal_token
            )
            
            state["legal_result"] = legal_result
            state["messages"].append(AIMessage(content=f"Legal Agent completed: {legal_result.get('summary', 'Task completed')}"))
            
            return state
            
        except Exception as e:
            logger.error(f"Legal Agent node error: {e}")
            state["legal_result"] = {"error": str(e)}
            return state

    def _sanitize_agent_result(self, result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Sanitize agent result to remove tokens and sensitive data before sending to LLM"""
        if not result:
            return {}
        
        sanitized = result.copy()
        
        # Remove token_exchanges (contains actual tokens)
        if "token_exchanges" in sanitized:
            # Keep metadata about which exchanges happened, but remove actual tokens
            sanitized["token_exchanges"] = {
                k: "[REDACTED]" for k in sanitized["token_exchanges"].keys()
            }
        
        # Remove any other fields that might contain tokens or sensitive data
        # Keep only: status, summary, workflow_type, completed_tasks, recommendations, etc.
        safe_fields = {
            "status", "summary", "workflow_type", "completed_tasks", 
            "recommendations", "audit_trail", "next_steps", "hr_actions",
            "finance_actions", "legal_actions", "error"
        }
        
        # Only keep safe fields, remove everything else
        filtered = {k: v for k, v in sanitized.items() if k in safe_fields}
        
        # Special handling for audit_trail - remove any token references
        if "audit_trail" in filtered and isinstance(filtered["audit_trail"], dict):
            audit = filtered["audit_trail"].copy()
            for key in ["token", "access_token", "token_id", "auth_token"]:
                audit.pop(key, None)
            filtered["audit_trail"] = audit
        
        return filtered
    
    async def _coordination_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Coordination node - coordinates results from all agents"""
        try:
            hr_result = state.get("hr_result")
            finance_result = state.get("finance_result")
            legal_result = state.get("legal_result")
            
            logger.info("Coordinating results from all agents")
            
            # Sanitize agent results before sending to LLM (security)
            safe_hr_result = self._sanitize_agent_result(hr_result)
            safe_finance_result = self._sanitize_agent_result(finance_result)
            safe_legal_result = self._sanitize_agent_result(legal_result)
            
            # Analyze results and determine next steps
            coordination_prompt = f"""
            Coordinate the results from all agents:
            
            HR Agent Result: {json.dumps(safe_hr_result, indent=2) if safe_hr_result else "No result"}
            Finance Agent Result: {json.dumps(safe_finance_result, indent=2) if safe_finance_result else "No result"}
            Legal Agent Result: {json.dumps(safe_legal_result, indent=2) if safe_legal_result else "No result"}
            
            Determine if the workflow can proceed or if additional steps are needed.
            Provide a summary of the coordination results.
            """
            
            messages = [
                SystemMessage(content="You are coordinating results from multiple agents."),
                HumanMessage(content=coordination_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            state["messages"].append(AIMessage(content=f"Coordination: {response.content}"))
            state["current_step"] = "finalization"
            
            return state
            
        except Exception as e:
            logger.error(f"Coordination node error: {e}")
            state["error"] = str(e)
            return state

    async def _finalization_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Finalization node - creates final workflow result"""
        try:
            workflow_type = state["workflow_type"]
            hr_result = state.get("hr_result")
            finance_result = state.get("finance_result")
            legal_result = state.get("legal_result")
            
            logger.info("Finalizing workflow results")
            
            # Sanitize agent results before including in final result (security)
            safe_hr_result = self._sanitize_agent_result(hr_result)
            safe_finance_result = self._sanitize_agent_result(finance_result)
            safe_legal_result = self._sanitize_agent_result(legal_result)
            
            # Create final result (handle None results safely)
            final_result = {
                "workflow_type": workflow_type,
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "agent_results": {
                    "hr": safe_hr_result,
                    "finance": safe_finance_result,
                    "legal": safe_legal_result
                },
                "summary": f"Workflow {workflow_type} completed successfully.",
                "response": self._generate_final_response(
                    workflow_type, 
                    safe_hr_result, 
                    safe_finance_result, 
                    safe_legal_result
                )
            }
            
            state["final_result"] = final_result
            state["messages"].append(AIMessage(content=f"Finalization: {final_result['summary']}"))
            
            return state
            
        except Exception as e:
            logger.error(f"Finalization node error: {e}")
            state["error"] = str(e)
            state["final_result"] = {"error": str(e)}
            return state

    def _generate_final_response(self, workflow_type: str, hr_result: Dict[str, Any], finance_result: Dict[str, Any], legal_result: Dict[str, Any]) -> str:
        """Generate final response based on workflow results"""
        
        if workflow_type == "employee_onboarding":
            return f"""
**Employee Onboarding Workflow Completed**

 **HR Agent**: {hr_result.get('summary', 'Employee verification completed')}
 **Finance Agent**: {finance_result.get('summary', 'Payroll setup completed')}
 **Legal Agent**: {legal_result.get('summary', 'Compliance verification completed')}

The new employee onboarding process has been successfully completed with all necessary approvals and verifications.
            """
        
        elif workflow_type == "expense_approval":
            return f"""
**Expense Approval Workflow Completed**

 **HR Agent**: {hr_result.get('summary', 'Employee verification completed')}
 **Finance Agent**: {finance_result.get('summary', 'Financial approval completed')}
 **Legal Agent**: {legal_result.get('summary', 'Compliance check completed')}

The expense approval has been processed with all necessary verifications and approvals.
            """
        
        elif workflow_type == "compliance_audit":
            return f"""
**Compliance Audit Workflow Completed**

 **HR Agent**: {hr_result.get('summary', 'HR compliance check completed')}
 **Finance Agent**: {finance_result.get('summary', 'Financial compliance verified')}
 **Legal Agent**: {legal_result.get('summary', 'Legal compliance confirmed')}

The compliance audit has been completed with all departments verified.
            """
        
        else:
            return f"""
**Workflow Completed Successfully**

 **HR Agent**: {hr_result.get('summary', 'HR tasks completed')}
 **Finance Agent**: {finance_result.get('summary', 'Finance tasks completed')}
 **Legal Agent**: {legal_result.get('summary', 'Legal tasks completed')}

The {workflow_type} workflow has been completed with coordination from all relevant departments.
            """

    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific workflow"""
        return self.active_workflows.get(workflow_id)

    async def list_active_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflows"""
        return [
            {
                "workflow_id": workflow_id,
                "type": workflow["type"],
                "status": workflow["status"],
                "started_at": workflow["started_at"],
                "user": workflow["user_info"].get("email", "unknown")
            }
            for workflow_id, workflow in self.active_workflows.items()
        ]

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel an active workflow"""
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id]["status"] = "cancelled"
            self.active_workflows[workflow_id]["cancelled_at"] = datetime.now()
            return True
        return False
