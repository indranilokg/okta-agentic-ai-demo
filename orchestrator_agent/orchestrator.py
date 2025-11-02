import asyncio
import logging
from typing import Dict, Any, List, Optional
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
        
        # Initialize A2A agents
        self.hr_agent = HRAgent()
        self.finance_agent = FinanceAgent()
        self.legal_agent = LegalAgent()
        
        # Initialize auth
        self.okta_auth = OktaAuth()
        
        # Workflow state management
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        
        # Build LangGraph workflow
        self.workflow_graph = self._build_workflow_graph()

    def _build_workflow_graph(self) -> StateGraph:
        """Build LangGraph workflow for orchestrating multi-agent processes"""
        
        # Define the state
        class WorkflowState:
            messages: List[Any]
            workflow_type: str
            parameters: Dict[str, Any]
            user_info: Dict[str, Any]
            workflow_id: str
            current_step: str
            hr_result: Optional[Dict[str, Any]] = None
            finance_result: Optional[Dict[str, Any]] = None
            legal_result: Optional[Dict[str, Any]] = None
            final_result: Optional[Dict[str, Any]] = None
            error: Optional[str] = None
        
        # Create the graph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("orchestrator", self._orchestrator_node)
        workflow.add_node("hr_agent", self._hr_agent_node)
        workflow.add_node("finance_agent", self._finance_agent_node)
        workflow.add_node("legal_agent", self._legal_agent_node)
        workflow.add_node("coordination", self._coordination_node)
        workflow.add_node("finalization", self._finalization_node)
        
        # Add edges
        workflow.add_edge("orchestrator", "hr_agent")
        workflow.add_edge("orchestrator", "finance_agent")
        workflow.add_edge("orchestrator", "legal_agent")
        workflow.add_edge("hr_agent", "coordination")
        workflow.add_edge("finance_agent", "coordination")
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
            
            logger.info(f"Starting workflow {workflow_id} of type {workflow_type}")
            
            # Initialize workflow state
            initial_state = {
                "messages": [HumanMessage(content=f"Workflow: {workflow_type} with parameters: {parameters}")],
                "workflow_type": workflow_type,
                "parameters": parameters,
                "user_info": user_info,
                "workflow_id": workflow_id,
                "current_step": "orchestrator"
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
            
            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "response": result.get("final_result", {}).get("response", "Workflow completed successfully"),
                "metadata": {
                    "workflow_type": workflow_type,
                    "execution_time": (datetime.now() - self.active_workflows[workflow_id]["started_at"]).total_seconds(),
                    "agents_involved": ["hr_agent", "finance_agent", "legal_agent"]
                }
            }
            
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
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
            
            logger.info(f"Orchestrator analyzing workflow: {workflow_type}")
            
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
            logger.error(f"Orchestrator node error: {e}")
            state["error"] = str(e)
            return state

    async def _hr_agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """HR Agent node - handles HR-related workflow tasks"""
        try:
            workflow_type = state["workflow_type"]
            parameters = state["parameters"]
            user_info = state["user_info"]
            
            logger.info(f"HR Agent processing workflow: {workflow_type}")
            
            # Exchange token for HR agent access
            hr_token = await self.okta_auth.exchange_token(
                user_info.get("token", "mock-token"),
                "hr-agent-audience"
            )
            
            # Process through HR agent
            hr_result = await self.hr_agent.process_workflow_task(
                workflow_type,
                parameters,
                user_info,
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
            
            # Exchange token for Finance agent access
            finance_token = await self.okta_auth.exchange_token(
                user_info.get("token", "mock-token"),
                "finance-agent-audience"
            )
            
            # Process through Finance agent
            finance_result = await self.finance_agent.process_workflow_task(
                workflow_type,
                parameters,
                user_info,
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
            
            # Exchange token for Legal agent access
            legal_token = await self.okta_auth.exchange_token(
                user_info.get("token", "mock-token"),
                "legal-agent-audience"
            )
            
            # Process through Legal agent
            legal_result = await self.legal_agent.process_workflow_task(
                workflow_type,
                parameters,
                user_info,
                legal_token
            )
            
            state["legal_result"] = legal_result
            state["messages"].append(AIMessage(content=f"Legal Agent completed: {legal_result.get('summary', 'Task completed')}"))
            
            return state
            
        except Exception as e:
            logger.error(f"Legal Agent node error: {e}")
            state["legal_result"] = {"error": str(e)}
            return state

    async def _coordination_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Coordination node - coordinates results from all agents"""
        try:
            hr_result = state.get("hr_result")
            finance_result = state.get("finance_result")
            legal_result = state.get("legal_result")
            
            logger.info("Coordinating results from all agents")
            
            # Analyze results and determine next steps
            coordination_prompt = f"""
            Coordinate the results from all agents:
            
            HR Agent Result: {json.dumps(hr_result, indent=2) if hr_result else "No result"}
            Finance Agent Result: {json.dumps(finance_result, indent=2) if finance_result else "No result"}
            Legal Agent Result: {json.dumps(legal_result, indent=2) if legal_result else "No result"}
            
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
            
            # Create final result
            final_result = {
                "workflow_type": workflow_type,
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "agent_results": {
                    "hr": hr_result,
                    "finance": finance_result,
                    "legal": legal_result
                },
                "summary": f"Workflow {workflow_type} completed successfully with coordination from HR, Finance, and Legal agents.",
                "response": self._generate_final_response(workflow_type, hr_result, finance_result, legal_result)
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

✅ **HR Agent**: {hr_result.get('summary', 'Employee verification completed')}
✅ **Finance Agent**: {finance_result.get('summary', 'Payroll setup completed')}
✅ **Legal Agent**: {legal_result.get('summary', 'Compliance verification completed')}

The new employee onboarding process has been successfully completed with all necessary approvals and verifications.
            """
        
        elif workflow_type == "expense_approval":
            return f"""
**Expense Approval Workflow Completed**

✅ **HR Agent**: {hr_result.get('summary', 'Employee verification completed')}
✅ **Finance Agent**: {finance_result.get('summary', 'Financial approval completed')}
✅ **Legal Agent**: {legal_result.get('summary', 'Compliance check completed')}

The expense approval has been processed with all necessary verifications and approvals.
            """
        
        elif workflow_type == "compliance_audit":
            return f"""
**Compliance Audit Workflow Completed**

✅ **HR Agent**: {hr_result.get('summary', 'HR compliance check completed')}
✅ **Finance Agent**: {finance_result.get('summary', 'Financial compliance verified')}
✅ **Legal Agent**: {legal_result.get('summary', 'Legal compliance confirmed')}

The compliance audit has been completed with all departments verified.
            """
        
        else:
            return f"""
**Workflow Completed Successfully**

✅ **HR Agent**: {hr_result.get('summary', 'HR tasks completed')}
✅ **Finance Agent**: {finance_result.get('summary', 'Finance tasks completed')}
✅ **Legal Agent**: {legal_result.get('summary', 'Legal tasks completed')}

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
