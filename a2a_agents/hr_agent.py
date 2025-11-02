import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

class HRAgent:
    """
    HR A2A Agent for employee management workflows
    Handles token exchange with other agents and HR-specific tasks
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.3,
            max_tokens=1000
        )
        
        self.system_prompt = """
You are the HR A2A Agent for Streamward Corporation. Your responsibilities include:

1. **Employee Management**: Onboarding, offboarding, benefits administration
2. **Cross-Department Coordination**: Working with Finance and Legal agents
3. **Token Exchange**: Receiving tokens from other agents for cross-department access
4. **Policy Compliance**: Ensuring HR policies are followed

You receive requests from the Orchestrator Agent and coordinate with Finance and Legal agents as needed.
Always maintain professional communication and provide detailed summaries of your actions.
"""
        
        # Mock HR data
        self.employee_records = {
            "emp-001": {
                "name": "John Smith",
                "department": "Engineering",
                "hire_date": "2022-03-15",
                "status": "Active",
                "benefits": ["Health Insurance", "401k", "Stock Options"],
                "manager": "Jane Doe"
            },
            "emp-002": {
                "name": "Sarah Johnson", 
                "department": "Finance",
                "hire_date": "2021-08-20",
                "status": "Active",
                "benefits": ["Health Insurance", "401k", "Dental"],
                "manager": "Mike Wilson"
            }
        }

    async def process_workflow_task(self, workflow_type: str, parameters: Dict[str, Any], user_info: Dict[str, Any], token: str) -> Dict[str, Any]:
        """
        Process HR workflow tasks with token exchange capabilities
        """
        try:
            logger.info(f"HR Agent processing workflow: {workflow_type}")
            
            if workflow_type == "employee_onboarding":
                return await self._handle_employee_onboarding(parameters, user_info, token)
            elif workflow_type == "expense_approval":
                return await self._handle_expense_approval_hr(parameters, user_info, token)
            elif workflow_type == "compliance_audit":
                return await self._handle_compliance_audit_hr(parameters, user_info, token)
            elif workflow_type == "benefits_change":
                return await self._handle_benefits_change(parameters, user_info, token)
            else:
                return await self._handle_general_hr_task(workflow_type, parameters, user_info, token)
                
        except Exception as e:
            logger.error(f"HR Agent error: {e}")
            return {
                "status": "error",
                "summary": f"HR Agent encountered an error: {str(e)}",
                "error": str(e)
            }

    async def _handle_employee_onboarding(self, parameters: Dict[str, Any], user_info: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Handle employee onboarding workflow"""
        try:
            employee_name = parameters.get("employee_name", "New Employee")
            department = parameters.get("department", "Unknown")
            
            # Simulate HR onboarding tasks
            onboarding_tasks = [
                "Verify employee eligibility and documentation",
                "Set up employee record in HR system",
                "Configure benefits enrollment",
                "Schedule orientation and training",
                "Assign manager and team",
                "Set up IT accounts and access"
            ]
            
            # Process onboarding
            completed_tasks = []
            for task in onboarding_tasks:
                # Simulate task completion
                await asyncio.sleep(0.1)  # Simulate processing time
                completed_tasks.append(task)
            
            # Exchange token with Finance agent for payroll setup
            finance_token = await self._exchange_token_with_finance(token, "payroll_setup")
            
            # Exchange token with Legal agent for compliance verification
            legal_token = await self._exchange_token_with_legal(token, "compliance_check")
            
            return {
                "status": "completed",
                "summary": f"Employee onboarding completed for {employee_name} in {department}",
                "completed_tasks": completed_tasks,
                "employee_id": f"EMP{len(self.employee_records) + 1:03d}",
                "next_steps": [
                    "Finance agent will set up payroll",
                    "Legal agent will verify compliance requirements",
                    "IT will provision accounts and access"
                ],
                "token_exchanges": {
                    "finance_token": finance_token,
                    "legal_token": legal_token
                }
            }
            
        except Exception as e:
            logger.error(f"Employee onboarding error: {e}")
            return {
                "status": "error",
                "summary": f"Employee onboarding failed: {str(e)}",
                "error": str(e)
            }

    async def _handle_expense_approval_hr(self, parameters: Dict[str, Any], user_info: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Handle HR aspects of expense approval"""
        try:
            employee_id = parameters.get("employee_id", "unknown")
            amount = parameters.get("amount", 0)
            
            # Verify employee status and eligibility
            employee_info = self._get_employee_info(employee_id)
            
            if not employee_info:
                return {
                    "status": "error",
                    "summary": f"Employee {employee_id} not found",
                    "error": "employee_not_found"
                }
            
            # Check expense policy compliance
            hr_checks = [
                f"Employee {employee_info['name']} is active and eligible",
                f"Department: {employee_info['department']}",
                f"Manager: {employee_info['manager']}",
                "Expense policy compliance verified",
                "Employee benefits status confirmed"
            ]
            
            return {
                "status": "completed",
                "summary": f"HR verification completed for expense approval",
                "employee_info": employee_info,
                "hr_checks": hr_checks,
                "recommendation": "approve" if employee_info['status'] == 'Active' else "review_required"
            }
            
        except Exception as e:
            logger.error(f"Expense approval HR error: {e}")
            return {
                "status": "error",
                "summary": f"HR expense verification failed: {str(e)}",
                "error": str(e)
            }

    async def _handle_compliance_audit_hr(self, parameters: Dict[str, Any], user_info: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Handle HR compliance audit tasks"""
        try:
            audit_scope = parameters.get("audit_scope", "general")
            
            # Perform HR compliance checks
            compliance_checks = [
                "Employee records completeness check",
                "Benefits compliance verification",
                "Equal opportunity policy compliance",
                "Workplace safety policy compliance",
                "Training completion verification",
                "Performance review compliance"
            ]
            
            # Simulate audit process
            audit_results = {}
            for check in compliance_checks:
                await asyncio.sleep(0.1)  # Simulate processing
                audit_results[check] = "compliant"
            
            return {
                "status": "completed",
                "summary": "HR compliance audit completed successfully",
                "audit_results": audit_results,
                "compliance_score": "95%",
                "recommendations": [
                    "Update employee handbook",
                    "Schedule additional training sessions",
                    "Review performance review process"
                ]
            }
            
        except Exception as e:
            logger.error(f"Compliance audit HR error: {e}")
            return {
                "status": "error",
                "summary": f"HR compliance audit failed: {str(e)}",
                "error": str(e)
            }

    async def _handle_benefits_change(self, parameters: Dict[str, Any], user_info: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Handle benefits change requests"""
        try:
            employee_id = parameters.get("employee_id", "unknown")
            benefit_type = parameters.get("benefit_type", "unknown")
            change_type = parameters.get("change_type", "modify")
            
            employee_info = self._get_employee_info(employee_id)
            
            if not employee_info:
                return {
                    "status": "error",
                    "summary": f"Employee {employee_id} not found",
                    "error": "employee_not_found"
                }
            
            # Process benefits change
            benefits_tasks = [
                f"Verify employee eligibility for {benefit_type}",
                f"Process {change_type} request for {benefit_type}",
                "Update employee benefits record",
                "Notify benefits provider",
                "Schedule employee notification"
            ]
            
            return {
                "status": "completed",
                "summary": f"Benefits {change_type} completed for {employee_info['name']}",
                "benefit_type": benefit_type,
                "change_type": change_type,
                "completed_tasks": benefits_tasks,
                "effective_date": datetime.now().strftime("%Y-%m-%d")
            }
            
        except Exception as e:
            logger.error(f"Benefits change error: {e}")
            return {
                "status": "error",
                "summary": f"Benefits change failed: {str(e)}",
                "error": str(e)
            }

    async def _handle_general_hr_task(self, workflow_type: str, parameters: Dict[str, Any], user_info: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Handle general HR tasks"""
        try:
            # Use LLM to process general HR requests
            prompt = f"""
            Process this HR workflow task:
            
            Workflow Type: {workflow_type}
            Parameters: {json.dumps(parameters, indent=2)}
            User Info: {json.dumps(user_info, indent=2)}
            
            Provide a summary of HR actions taken and recommendations.
            """
            
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            return {
                "status": "completed",
                "summary": response.content,
                "workflow_type": workflow_type,
                "hr_actions": ["General HR processing completed"]
            }
            
        except Exception as e:
            logger.error(f"General HR task error: {e}")
            return {
                "status": "error",
                "summary": f"General HR task failed: {str(e)}",
                "error": str(e)
            }

    async def _exchange_token_with_finance(self, current_token: str, purpose: str) -> str:
        """Exchange token with Finance agent"""
        # Simulate token exchange
        return f"hr-to-finance-token-{purpose}-{datetime.now().timestamp()}"

    async def _exchange_token_with_legal(self, current_token: str, purpose: str) -> str:
        """Exchange token with Legal agent"""
        # Simulate token exchange
        return f"hr-to-legal-token-{purpose}-{datetime.now().timestamp()}"

    def _get_employee_info(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Get employee information"""
        return self.employee_records.get(employee_id)

    async def receive_token_from_agent(self, from_agent: str, token: str, purpose: str) -> Dict[str, Any]:
        """Receive token from another agent"""
        logger.info(f"HR Agent received token from {from_agent} for {purpose}")
        
        return {
            "status": "received",
            "from_agent": from_agent,
            "purpose": purpose,
            "token": token,
            "processed_at": datetime.now().isoformat()
        }
