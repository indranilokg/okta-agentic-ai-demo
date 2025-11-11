import logging
import os
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import asyncio

from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from auth.okta_scopes import OKTA_SCOPES, get_cross_agent_scope

logger = logging.getLogger(__name__)

class FinanceAgent:
    """
    Finance A2A Agent for financial transactions and approvals
    Handles token exchange with other agents and includes human approval capability
    """
    
    def __init__(self, okta_auth=None):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.3,
            max_tokens=1000
        )
        self.okta_auth = okta_auth
        
        self.system_prompt = """
You are the Finance A2A Agent for Streamward Corporation. Your responsibilities include:

1. **Financial Transactions**: Processing payments, expenses, budgets
2. **Human Approval**: Initiating CIBA flows for high-value transactions
3. **Cross-Department Coordination**: Working with HR and Legal agents
4. **Token Exchange**: Initiating token exchanges with other agents
5. **Audit Trail**: Maintaining complete transaction logs

You are the only agent with human approval capability for high-value financial operations.
Always maintain detailed audit trails and coordinate with other agents as needed.
"""
        
        # Mock financial data
        self.transactions = {
            "txn-001": {
                "id": "txn-001",
                "type": "expense",
                "amount": 1500.00,
                "employee_id": "emp-001",
                "status": "approved",
                "approval_required": True
            },
            "txn-002": {
                "id": "txn-002", 
                "type": "payroll",
                "amount": 50000.00,
                "employee_id": "emp-001",
                "status": "pending",
                "approval_required": True
            }
        }

    async def process_workflow_task(self, workflow_type: str, parameters: Dict[str, Any], user_info: Dict[str, Any], token: str) -> Dict[str, Any]:
        """
        Process Finance workflow tasks with token exchange and human approval
        """
        try:
            logger.info(f"Finance Agent processing workflow: {workflow_type}")
            
            if workflow_type == "employee_onboarding":
                return await self._handle_employee_onboarding_finance(parameters, user_info, token)
            elif workflow_type == "expense_approval":
                return await self._handle_expense_approval(parameters, user_info, token)
            elif workflow_type == "compliance_audit":
                return await self._handle_compliance_audit_finance(parameters, user_info, token)
            elif workflow_type == "benefits_change":
                return await self._handle_benefits_change_finance(parameters, user_info, token)
            else:
                return await self._handle_general_finance_task(workflow_type, parameters, user_info, token)
                
        except Exception as e:
            logger.error(f"Finance Agent error: {e}")
            return {
                "status": "error",
                "summary": f"Finance Agent encountered an error: {str(e)}",
                "error": str(e)
            }

    async def _handle_employee_onboarding_finance(self, parameters: Dict[str, Any], user_info: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Handle financial aspects of employee onboarding"""
        try:
            employee_name = parameters.get("employee_name", "New Employee")
            department = parameters.get("department", "Unknown")
            salary = parameters.get("salary", 75000)
            
            # Exchange token with HR agent for employee verification
            hr_token = await self._exchange_token_with_hr(token, "employee_verification")
            
            # Exchange token with Legal agent for compliance check
            legal_token = await self._exchange_token_with_legal(token, "compliance_verification")
            
            # Set up payroll
            payroll_tasks = [
                "Create employee payroll record",
                "Set up direct deposit information",
                "Configure tax withholdings",
                "Set up benefits deductions",
                "Schedule first payroll run",
                "Generate employee ID for payroll system"
            ]
            
            # Process payroll setup
            completed_tasks = []
            for task in payroll_tasks:
                await asyncio.sleep(0.1)  # Simulate processing
                completed_tasks.append(task)
            
            # Check if human approval is needed for high-value onboarding
            approval_required = salary > 100000
            approval_status = "pending" if approval_required else "auto_approved"
            
            if approval_required:
                # Initiate CIBA flow for human approval
                ciba_result = await self._initiate_ciba_approval(
                    f"High-value employee onboarding: {employee_name} - ${salary:,}",
                    user_info
                )
                approval_status = ciba_result["status"]
            
            return {
                "status": "completed",
                "summary": f"Financial onboarding completed for {employee_name}",
                "completed_tasks": completed_tasks,
                "salary": salary,
                "approval_status": approval_status,
                "payroll_id": f"PAY{len(self.transactions) + 1:03d}",
                "token_exchanges": {
                    "hr_token": hr_token,
                    "legal_token": legal_token
                },
                "next_steps": [
                    "HR agent will complete benefits setup",
                    "Legal agent will verify compliance",
                    "First payroll will be processed on next cycle"
                ]
            }
            
        except Exception as e:
            logger.error(f"Employee onboarding finance error: {e}")
            return {
                "status": "error",
                "summary": f"Financial onboarding failed: {str(e)}",
                "error": str(e)
            }

    async def _handle_expense_approval(self, parameters: Dict[str, Any], user_info: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Handle expense approval with human approval for high-value transactions"""
        try:
            amount = parameters.get("amount", 0)
            employee_id = parameters.get("employee_id", "unknown")
            category = parameters.get("category", "other")
            description = parameters.get("description", "")
            
            # Exchange token with HR agent for employee verification
            hr_token = await self._exchange_token_with_hr(token, "employee_verification")
            
            # Exchange token with Legal agent for compliance check
            legal_token = await self._exchange_token_with_legal(token, "expense_compliance")
            
            # Financial checks
            financial_checks = [
                f"Amount verification: ${amount:,.2f}",
                f"Category validation: {category}",
                "Budget availability check",
                "Expense policy compliance",
                "Receipt verification status"
            ]
            
            # Determine if human approval is required
            approval_threshold = 1000.00  # $1000 threshold
            approval_required = amount > approval_threshold
            
            approval_status = "auto_approved"
            if approval_required:
                # Initiate CIBA flow for human approval
                ciba_result = await self._initiate_ciba_approval(
                    f"High-value expense approval: ${amount:,.2f} - {description}",
                    user_info
                )
                approval_status = ciba_result["status"]
            
            # Create transaction record
            transaction_id = f"TXN{len(self.transactions) + 1:03d}"
            self.transactions[transaction_id] = {
                "id": transaction_id,
                "type": "expense",
                "amount": amount,
                "employee_id": employee_id,
                "category": category,
                "description": description,
                "status": approval_status,
                "approval_required": approval_required,
                "created_at": datetime.now().isoformat()
            }
            
            return {
                "status": "completed",
                "summary": f"Expense approval processed: ${amount:,.2f}",
                "transaction_id": transaction_id,
                "approval_status": approval_status,
                "approval_required": approval_required,
                "financial_checks": financial_checks,
                "token_exchanges": {
                    "hr_token": hr_token,
                    "legal_token": legal_token
                },
                "audit_trail": {
                    "processed_by": "Finance Agent",
                    "processed_at": datetime.now().isoformat(),
                    "approval_method": "CIBA" if approval_required else "auto",
                    "amount": amount
                }
            }
            
        except Exception as e:
            logger.error(f"Expense approval error: {e}")
            return {
                "status": "error",
                "summary": f"Expense approval failed: {str(e)}",
                "error": str(e)
            }

    async def _handle_compliance_audit_finance(self, parameters: Dict[str, Any], user_info: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Handle financial compliance audit"""
        try:
            audit_scope = parameters.get("audit_scope", "general")
            
            # Exchange tokens with other agents for comprehensive audit
            hr_token = await self._exchange_token_with_hr(token, "hr_audit_coordination")
            legal_token = await self._exchange_token_with_legal(token, "legal_audit_coordination")
            
            # Financial compliance checks
            compliance_checks = [
                "Financial record completeness",
                "SOX compliance verification",
                "Expense policy compliance",
                "Budget adherence verification",
                "Transaction audit trail completeness",
                "Financial reporting accuracy"
            ]
            
            # Simulate audit process
            audit_results = {}
            for check in compliance_checks:
                await asyncio.sleep(0.1)  # Simulate processing
                audit_results[check] = "compliant"
            
            return {
                "status": "completed",
                "summary": "Financial compliance audit completed",
                "audit_results": audit_results,
                "compliance_score": "98%",
                "token_exchanges": {
                    "hr_token": hr_token,
                    "legal_token": legal_token
                },
                "recommendations": [
                    "Implement additional expense controls",
                    "Enhance transaction monitoring",
                    "Update financial policies"
                ]
            }
            
        except Exception as e:
            logger.error(f"Compliance audit finance error: {e}")
            return {
                "status": "error",
                "summary": f"Financial compliance audit failed: {str(e)}",
                "error": str(e)
            }

    async def _handle_benefits_change_finance(self, parameters: Dict[str, Any], user_info: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Handle financial aspects of benefits changes"""
        try:
            employee_id = parameters.get("employee_id", "unknown")
            benefit_type = parameters.get("benefit_type", "unknown")
            change_type = parameters.get("change_type", "modify")
            
            # Exchange token with HR agent
            hr_token = await self._exchange_token_with_hr(token, "benefits_coordination")
            
            # Financial processing tasks
            financial_tasks = [
                f"Calculate {change_type} impact for {benefit_type}",
                "Update payroll deductions",
                "Verify budget availability",
                "Process benefits provider changes",
                "Update employee financial records"
            ]
            
            # Check if human approval is needed for significant changes
            approval_required = change_type == "add" and benefit_type in ["Stock Options", "Executive Benefits"]
            approval_status = "auto_approved"
            
            if approval_required:
                ciba_result = await self._initiate_ciba_approval(
                    f"Benefits change approval: {change_type} {benefit_type}",
                    user_info
                )
                approval_status = ciba_result["status"]
            
            return {
                "status": "completed",
                "summary": f"Financial benefits {change_type} completed",
                "benefit_type": benefit_type,
                "change_type": change_type,
                "approval_status": approval_status,
                "financial_tasks": financial_tasks,
                "token_exchanges": {
                    "hr_token": hr_token
                }
            }
            
        except Exception as e:
            logger.error(f"Benefits change finance error: {e}")
            return {
                "status": "error",
                "summary": f"Financial benefits change failed: {str(e)}",
                "error": str(e)
            }

    def _sanitize_user_info_for_llm(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize user_info with privacy controls (same as orchestrator).
        Privacy Levels (ALLOW_PII_IN_LLM_PROMPTS env var):
        - False (default): Anonymous user ID only (maximum privacy)
        - True: Email + name (enhanced UX, requires consent)
        """
        minimal = {}
        
        # Privacy setting: Check if PII is allowed
        allow_pii = os.getenv("ALLOW_PII_IN_LLM_PROMPTS", "false").lower() == "true"
        
        if allow_pii:
            # Privacy Level 3: Include email/name
            if user_info.get("email"):
                minimal["email"] = user_info["email"]
            if user_info.get("name"):
                minimal["name"] = user_info["name"]
            logger.debug(" Privacy Level 3: Sending email/name to LLM (PII exposure)")
        else:
            # Privacy Level 1: Anonymous ID only
            email = user_info.get("email", "anonymous")
            salt = os.getenv("ANONYMOUS_ID_SALT", "streamward-privacy-salt")
            anonymous_id = hashlib.sha256(f"{email}{salt}".encode()).hexdigest()[:16]
            minimal["user_id"] = f"user_{anonymous_id}"
            logger.debug("🔒 Privacy Level 1: Using anonymous user ID (no PII exposure)")
        
        logger.debug("🔒 Sanitized user_info for LLM: removed token, claims, and PII")
        return minimal
    
    async def _handle_general_finance_task(self, workflow_type: str, parameters: Dict[str, Any], user_info: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Handle general finance tasks"""
        try:
            # Sanitize user_info before sending to LLM (security)
            safe_user_info = self._sanitize_user_info_for_llm(user_info)
            
            # Use LLM to process general finance requests
            prompt = f"""
            Process this Finance workflow task:
            
            Workflow Type: {workflow_type}
            Parameters: {json.dumps(parameters, indent=2)}
            User Info: {json.dumps(safe_user_info, indent=2)}
            
            Provide a summary of financial actions taken and recommendations.
            Consider if human approval is needed for high-value transactions.
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
                "finance_actions": ["General finance processing completed"]
            }
            
        except Exception as e:
            logger.error(f"General finance task error: {e}")
            return {
                "status": "error",
                "summary": f"General finance task failed: {str(e)}",
                "error": str(e)
            }

    async def _initiate_ciba_approval(self, approval_request: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initiate CIBA (Client Initiated Backchannel Authentication) flow for human approval
        This is a simplified implementation - in production, you'd integrate with actual CIBA provider
        """
        try:
            logger.info(f"Initiating CIBA approval: {approval_request}")
            
            # Simulate CIBA flow
            ciba_request_id = f"CIBA-{datetime.now().timestamp()}"
            
            # In production, this would:
            # 1. Send push notification to user's device
            # 2. Wait for user approval/denial
            # 3. Return the result
            
            # For demo purposes, simulate approval after delay
            await asyncio.sleep(1.0)  # Simulate user response time
            
            # Mock approval result (in production, this comes from CIBA response)
            # Use email instead of sub for user identification (security: sub is internal ID)
            approval_result = {
                "ciba_request_id": ciba_request_id,
                "status": "approved",  # or "denied"
                "approved_at": datetime.now().isoformat(),
                "approval_request": approval_request,
                "user_email": user_info.get("email", "unknown")  # Use email, not sub
            }
            
            logger.info(f"CIBA approval completed: {approval_result['status']}")
            
            return approval_result
            
        except Exception as e:
            logger.error(f"CIBA approval error: {e}")
            return {
                "ciba_request_id": f"CIBA-ERROR-{datetime.now().timestamp()}",
                "status": "error",
                "error": str(e)
            }

    async def _exchange_token_with_hr(self, current_token: str, purpose: str) -> str:
        """Exchange token with HR agent using RFC 8693 Token Exchange"""
        if self.okta_auth:
            try:
                # Exchange to HR server - must request HR scopes (not Finance scopes!)
                # HR server only has HR scopes
                exchanged_token = await self.okta_auth.exchange_token(
                    token=current_token,
                    target_audience=self.okta_auth.hr_audience,
                    scope=get_cross_agent_scope("finance", "hr"),  # HR server scope
                    source_agent="finance"  # Use Finance service app credentials
                )
                logger.info(f"Finance Agent exchanged token with HR agent for: {purpose}")
                return exchanged_token
            except Exception as e:
                logger.error(f"Token exchange with HR agent failed: {e}")
                # Fallback to simulated token for demo purposes
                return f"finance-to-hr-token-{purpose}-{datetime.now().timestamp()}"
        else:
            # Fallback to simulated token if okta_auth not available
            logger.warning("OktaAuth not available, using simulated token exchange")
            return f"finance-to-hr-token-{purpose}-{datetime.now().timestamp()}"

    async def _exchange_token_with_legal(self, current_token: str, purpose: str) -> str:
        """Exchange token with Legal agent using RFC 8693 Token Exchange"""
        if self.okta_auth:
            try:
                # Exchange to Legal server - must request Legal scopes (not Finance scopes!)
                # Legal server only has Legal scopes
                exchanged_token = await self.okta_auth.exchange_token(
                    token=current_token,
                    target_audience=self.okta_auth.legal_audience,
                    scope=OKTA_SCOPES.LEGAL.COMPLIANCE_VERIFY,  # Legal server scope
                    source_agent="finance"  # Use Finance service app credentials
                )
                logger.info(f"Finance Agent exchanged token with Legal agent for: {purpose}")
                return exchanged_token
            except Exception as e:
                logger.error(f"Token exchange with Legal agent failed: {e}")
                # Fallback to simulated token for demo purposes
                return f"finance-to-legal-token-{purpose}-{datetime.now().timestamp()}"
        else:
            # Fallback to simulated token if okta_auth not available
            logger.warning("OktaAuth not available, using simulated token exchange")
            return f"finance-to-legal-token-{purpose}-{datetime.now().timestamp()}"

    async def receive_token_from_agent(self, from_agent: str, token: str, purpose: str) -> Dict[str, Any]:
        """Receive token from another agent (internal use - token not returned for security)"""
        logger.info(f"Finance Agent received token from {from_agent} for {purpose}")
        
        # Security: Don't return actual token in response - it's used internally only
        return {
            "status": "received",
            "from_agent": from_agent,
            "purpose": purpose,
            # Token removed - used internally, not returned
            "processed_at": datetime.now().isoformat()
        }

    def get_transaction_history(self, employee_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get transaction history"""
        if employee_id:
            return [txn for txn in self.transactions.values() if txn.get("employee_id") == employee_id]
        return list(self.transactions.values())
