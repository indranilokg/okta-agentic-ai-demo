import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json
import asyncio

from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

class LegalAgent:
    """
    Legal A2A Agent for compliance verification and legal tasks
    Handles token exchange with other agents and legal compliance checks
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.3,
            max_tokens=1000
        )
        
        self.system_prompt = """
You are the Legal A2A Agent for Streamward Corporation. Your responsibilities include:

1. **Compliance Verification**: Regulatory compliance, policy adherence
2. **Contract Review**: Legal document processing and validation
3. **Cross-Department Coordination**: Working with HR and Finance agents
4. **Token Exchange**: Receiving tokens from other agents for legal verification
5. **Risk Assessment**: Legal risk evaluation and mitigation

You receive requests from the Orchestrator Agent and coordinate with HR and Finance agents as needed.
Always maintain legal accuracy and provide detailed compliance assessments.
"""
        
        # Mock legal data
        self.compliance_records = {
            "comp-001": {
                "id": "comp-001",
                "type": "SOX",
                "status": "compliant",
                "last_review": "2024-01-01",
                "next_review": "2024-07-01"
            },
            "comp-002": {
                "id": "comp-002",
                "type": "GDPR",
                "status": "compliant", 
                "last_review": "2024-01-15",
                "next_review": "2024-07-15"
            }
        }

    async def process_workflow_task(self, workflow_type: str, parameters: Dict[str, Any], user_info: Dict[str, Any], token: str) -> Dict[str, Any]:
        """
        Process Legal workflow tasks with token exchange capabilities
        """
        try:
            logger.info(f"Legal Agent processing workflow: {workflow_type}")
            
            if workflow_type == "employee_onboarding":
                return await self._handle_employee_onboarding_legal(parameters, user_info, token)
            elif workflow_type == "expense_approval":
                return await self._handle_expense_approval_legal(parameters, user_info, token)
            elif workflow_type == "compliance_audit":
                return await self._handle_compliance_audit(parameters, user_info, token)
            elif workflow_type == "benefits_change":
                return await self._handle_benefits_change_legal(parameters, user_info, token)
            else:
                return await self._handle_general_legal_task(workflow_type, parameters, user_info, token)
                
        except Exception as e:
            logger.error(f"Legal Agent error: {e}")
            return {
                "status": "error",
                "summary": f"Legal Agent encountered an error: {str(e)}",
                "error": str(e)
            }

    async def _handle_employee_onboarding_legal(self, parameters: Dict[str, Any], user_info: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Handle legal aspects of employee onboarding"""
        try:
            employee_name = parameters.get("employee_name", "New Employee")
            department = parameters.get("department", "Unknown")
            position = parameters.get("position", "Employee")
            
            # Exchange token with HR agent for employee verification
            hr_token = await self._exchange_token_with_hr(token, "employee_verification")
            
            # Exchange token with Finance agent for financial compliance
            finance_token = await self._exchange_token_with_finance(token, "financial_compliance")
            
            # Legal compliance checks
            legal_checks = [
                "Employment contract compliance",
                "Non-disclosure agreement verification",
                "Background check compliance",
                "Right-to-work verification",
                "Department-specific legal requirements",
                "Data privacy compliance (GDPR, CCPA)",
                "Intellectual property assignment"
            ]
            
            # Process legal verification
            compliance_results = {}
            for check in legal_checks:
                await asyncio.sleep(0.1)  # Simulate processing
                compliance_results[check] = "verified"
            
            # Generate legal documents
            legal_documents = [
                "Employment Agreement",
                "Non-Disclosure Agreement",
                "Intellectual Property Assignment",
                "Data Privacy Consent"
            ]
            
            return {
                "status": "completed",
                "summary": f"Legal onboarding completed for {employee_name}",
                "compliance_results": compliance_results,
                "legal_documents": legal_documents,
                "token_exchanges": {
                    "hr_token": hr_token,
                    "finance_token": finance_token
                },
                "next_steps": [
                    "HR agent will complete employment setup",
                    "Finance agent will process payroll setup",
                    "Legal documents will be sent for signature"
                ],
                "compliance_score": "100%"
            }
            
        except Exception as e:
            logger.error(f"Employee onboarding legal error: {e}")
            return {
                "status": "error",
                "summary": f"Legal onboarding failed: {str(e)}",
                "error": str(e)
            }

    async def _handle_expense_approval_legal(self, parameters: Dict[str, Any], user_info: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Handle legal aspects of expense approval"""
        try:
            amount = parameters.get("amount", 0)
            employee_id = parameters.get("employee_id", "unknown")
            category = parameters.get("category", "other")
            description = parameters.get("description", "")
            
            # Exchange token with HR agent for employee verification
            hr_token = await self._exchange_token_with_hr(token, "employee_verification")
            
            # Exchange token with Finance agent for financial compliance
            finance_token = await self._exchange_token_with_finance(token, "expense_compliance")
            
            # Legal compliance checks
            legal_checks = [
                "Expense policy compliance verification",
                "Tax compliance for expense category",
                "Regulatory requirement verification",
                "Anti-corruption policy compliance",
                "Documentation requirement verification"
            ]
            
            # Process legal verification
            compliance_results = {}
            for check in legal_checks:
                await asyncio.sleep(0.1)  # Simulate processing
                compliance_results[check] = "compliant"
            
            # Risk assessment
            risk_level = "low"
            if amount > 5000:
                risk_level = "medium"
            if amount > 10000:
                risk_level = "high"
            
            return {
                "status": "completed",
                "summary": f"Legal expense verification completed: ${amount:,.2f}",
                "compliance_results": compliance_results,
                "risk_level": risk_level,
                "legal_recommendation": "approve" if risk_level == "low" else "review_required",
                "token_exchanges": {
                    "hr_token": hr_token,
                    "finance_token": finance_token
                },
                "legal_notes": [
                    f"Expense category '{category}' is compliant with company policy",
                    f"Amount ${amount:,.2f} is within approved limits",
                    "All required documentation is in order"
                ]
            }
            
        except Exception as e:
            logger.error(f"Expense approval legal error: {e}")
            return {
                "status": "error",
                "summary": f"Legal expense verification failed: {str(e)}",
                "error": str(e)
            }

    async def _handle_compliance_audit(self, parameters: Dict[str, Any], user_info: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Handle legal compliance audit"""
        try:
            audit_scope = parameters.get("audit_scope", "general")
            
            # Exchange tokens with other agents for comprehensive audit
            hr_token = await self._exchange_token_with_hr(token, "hr_audit_coordination")
            finance_token = await self._exchange_token_with_finance(token, "finance_audit_coordination")
            
            # Legal compliance checks
            compliance_checks = [
                "SOX compliance verification",
                "GDPR compliance assessment",
                "CCPA compliance verification",
                "Employment law compliance",
                "Contract compliance verification",
                "Intellectual property compliance",
                "Data privacy compliance",
                "Anti-corruption compliance"
            ]
            
            # Simulate audit process
            audit_results = {}
            for check in compliance_checks:
                await asyncio.sleep(0.1)  # Simulate processing
                audit_results[check] = "compliant"
            
            # Risk assessment
            risk_factors = [
                "Data privacy regulations",
                "Employment law changes",
                "Contractual obligations",
                "Regulatory updates"
            ]
            
            return {
                "status": "completed",
                "summary": "Legal compliance audit completed successfully",
                "audit_results": audit_results,
                "compliance_score": "97%",
                "risk_factors": risk_factors,
                "token_exchanges": {
                    "hr_token": hr_token,
                    "finance_token": finance_token
                },
                "recommendations": [
                    "Update data privacy policies",
                    "Review employment contracts",
                    "Enhance compliance monitoring",
                    "Schedule regular compliance training"
                ],
                "next_review_date": "2024-07-01"
            }
            
        except Exception as e:
            logger.error(f"Compliance audit legal error: {e}")
            return {
                "status": "error",
                "summary": f"Legal compliance audit failed: {str(e)}",
                "error": str(e)
            }

    async def _handle_benefits_change_legal(self, parameters: Dict[str, Any], user_info: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Handle legal aspects of benefits changes"""
        try:
            employee_id = parameters.get("employee_id", "unknown")
            benefit_type = parameters.get("benefit_type", "unknown")
            change_type = parameters.get("change_type", "modify")
            
            # Exchange token with HR agent
            hr_token = await self._exchange_token_with_hr(token, "benefits_coordination")
            
            # Exchange token with Finance agent
            finance_token = await self._exchange_token_with_finance(token, "benefits_financial")
            
            # Legal verification tasks
            legal_tasks = [
                f"Verify legal compliance for {change_type} {benefit_type}",
                "Review employment contract implications",
                "Check regulatory compliance requirements",
                "Validate benefit provider agreements",
                "Assess legal risk factors"
            ]
            
            # Process legal verification
            verification_results = {}
            for task in legal_tasks:
                await asyncio.sleep(0.1)  # Simulate processing
                verification_results[task] = "verified"
            
            return {
                "status": "completed",
                "summary": f"Legal benefits {change_type} verification completed",
                "benefit_type": benefit_type,
                "change_type": change_type,
                "verification_results": verification_results,
                "legal_recommendation": "proceed",
                "token_exchanges": {
                    "hr_token": hr_token,
                    "finance_token": finance_token
                },
                "legal_notes": [
                    f"{change_type.title()} of {benefit_type} is legally compliant",
                    "All regulatory requirements are met",
                    "No legal risks identified"
                ]
            }
            
        except Exception as e:
            logger.error(f"Benefits change legal error: {e}")
            return {
                "status": "error",
                "summary": f"Legal benefits change verification failed: {str(e)}",
                "error": str(e)
            }

    async def _handle_general_legal_task(self, workflow_type: str, parameters: Dict[str, Any], user_info: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Handle general legal tasks"""
        try:
            # Use LLM to process general legal requests
            prompt = f"""
            Process this Legal workflow task:
            
            Workflow Type: {workflow_type}
            Parameters: {json.dumps(parameters, indent=2)}
            User Info: {json.dumps(user_info, indent=2)}
            
            Provide a summary of legal actions taken and compliance recommendations.
            Focus on regulatory compliance and risk assessment.
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
                "legal_actions": ["General legal processing completed"]
            }
            
        except Exception as e:
            logger.error(f"General legal task error: {e}")
            return {
                "status": "error",
                "summary": f"General legal task failed: {str(e)}",
                "error": str(e)
            }

    async def _exchange_token_with_hr(self, current_token: str, purpose: str) -> str:
        """Exchange token with HR agent"""
        # Simulate token exchange
        return f"legal-to-hr-token-{purpose}-{datetime.now().timestamp()}"

    async def _exchange_token_with_finance(self, current_token: str, purpose: str) -> str:
        """Exchange token with Finance agent"""
        # Simulate token exchange
        return f"legal-to-finance-token-{purpose}-{datetime.now().timestamp()}"

    async def receive_token_from_agent(self, from_agent: str, token: str, purpose: str) -> Dict[str, Any]:
        """Receive token from another agent"""
        logger.info(f"Legal Agent received token from {from_agent} for {purpose}")
        
        return {
            "status": "received",
            "from_agent": from_agent,
            "purpose": purpose,
            "token": token,
            "processed_at": datetime.now().isoformat()
        }

    def get_compliance_status(self, compliance_type: Optional[str] = None) -> Dict[str, Any]:
        """Get compliance status"""
        if compliance_type:
            return {k: v for k, v in self.compliance_records.items() if v["type"] == compliance_type}
        return self.compliance_records
