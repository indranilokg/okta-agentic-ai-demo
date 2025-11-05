"""
Okta Scope Constants

This module centralizes all OAuth scope definitions used in token exchanges.
Scopes are organized by authorization server (HR, Finance, Legal).

Each authorization server has its own set of scopes. When performing token exchanges,
use the scopes that belong to the TARGET authorization server.

Example:
    # When exchanging TO HR server, use HR scopes
    await okta_auth.exchange_token(
        token=user_token,
        target_audience="hr-agent-audience",
        scope=OKTA_SCOPES.HR.EMPLOYEES_READ
    )
    
    # When exchanging TO Finance server, use Finance scopes
    await okta_auth.exchange_token(
        token=user_token,
        target_audience="finance-agent-audience",
        scope=OKTA_SCOPES.FINANCE.TRANSACTIONS_READ
    )
"""

from typing import Dict, List


class HRScopes:
    """HR Authorization Server Scopes"""
    # Employee management
    EMPLOYEES_READ = "hr:employees:read"
    EMPLOYEES_WRITE = "hr:employees:write"
    
    # Benefits
    BENEFITS_READ = "hr:benefits:read"
    BENEFITS_WRITE = "hr:benefits:write"
    
    # Onboarding
    ONBOARDING_MANAGE = "hr:onboarding:manage"
    
    # Common combinations
    EMPLOYEES_READ_BENEFITS_READ = f"{EMPLOYEES_READ} {BENEFITS_READ}"
    EMPLOYEES_FULL_ACCESS = f"{EMPLOYEES_READ} {EMPLOYEES_WRITE} {BENEFITS_READ} {BENEFITS_WRITE}"
    
    @classmethod
    def get_all_scopes(cls) -> List[str]:
        """Get all available HR scopes"""
        return [
            cls.EMPLOYEES_READ,
            cls.EMPLOYEES_WRITE,
            cls.BENEFITS_READ,
            cls.BENEFITS_WRITE,
            cls.ONBOARDING_MANAGE,
        ]
    
    @classmethod
    def get_read_only_scopes(cls) -> str:
        """Get read-only scope combination"""
        return cls.EMPLOYEES_READ_BENEFITS_READ


class FinanceScopes:
    """Finance Authorization Server Scopes"""
    # Transactions
    TRANSACTIONS_READ = "finance:transactions:read"
    TRANSACTIONS_WRITE = "finance:transactions:write"
    
    # Budget
    BUDGET_READ = "finance:budget:read"
    BUDGET_WRITE = "finance:budget:write"
    
    # Approvals
    APPROVAL_MANAGE = "finance:approval:manage"
    
    # Common combinations
    TRANSACTIONS_READ_APPROVAL = f"{TRANSACTIONS_READ} {APPROVAL_MANAGE}"
    TRANSACTIONS_FULL_ACCESS = f"{TRANSACTIONS_READ} {TRANSACTIONS_WRITE} {APPROVAL_MANAGE}"
    
    @classmethod
    def get_all_scopes(cls) -> List[str]:
        """Get all available Finance scopes"""
        return [
            cls.TRANSACTIONS_READ,
            cls.TRANSACTIONS_WRITE,
            cls.BUDGET_READ,
            cls.BUDGET_WRITE,
            cls.APPROVAL_MANAGE,
        ]
    
    @classmethod
    def get_read_only_scopes(cls) -> str:
        """Get read-only scope combination"""
        return cls.TRANSACTIONS_READ


class LegalScopes:
    """Legal Authorization Server Scopes"""
    # Compliance
    COMPLIANCE_READ = "legal:compliance:read"
    COMPLIANCE_VERIFY = "legal:compliance:verify"
    
    # Contracts
    CONTRACTS_READ = "legal:contracts:read"
    CONTRACTS_REVIEW = "legal:contracts:review"
    
    # Audit
    AUDIT_EXECUTE = "legal:audit:execute"
    
    # Common combinations
    COMPLIANCE_READ_VERIFY = f"{COMPLIANCE_READ} {COMPLIANCE_VERIFY}"
    COMPLIANCE_FULL_ACCESS = f"{COMPLIANCE_READ} {COMPLIANCE_VERIFY} {CONTRACTS_READ} {CONTRACTS_REVIEW}"
    
    @classmethod
    def get_all_scopes(cls) -> List[str]:
        """Get all available Legal scopes"""
        return [
            cls.COMPLIANCE_READ,
            cls.COMPLIANCE_VERIFY,
            cls.CONTRACTS_READ,
            cls.CONTRACTS_REVIEW,
            cls.AUDIT_EXECUTE,
        ]
    
    @classmethod
    def get_read_only_scopes(cls) -> str:
        """Get read-only scope combination"""
        return cls.COMPLIANCE_READ


class OKTA_SCOPES:
    """
    Centralized Okta scope definitions.
    
    Usage:
        # HR scopes
        OKTA_SCOPES.HR.EMPLOYEES_READ
        OKTA_SCOPES.HR.EMPLOYEES_READ_BENEFITS_READ
        
        # Finance scopes
        OKTA_SCOPES.FINANCE.TRANSACTIONS_READ
        OKTA_SCOPES.FINANCE.TRANSACTIONS_READ_APPROVAL
        
        # Legal scopes
        OKTA_SCOPES.LEGAL.COMPLIANCE_READ
        OKTA_SCOPES.LEGAL.COMPLIANCE_READ_VERIFY
    """
    HR = HRScopes
    FINANCE = FinanceScopes
    LEGAL = LegalScopes
    
    @classmethod
    def get_scope_by_server(cls, server: str) -> Dict[str, List[str]]:
        """
        Get all scopes for a specific authorization server.
        
        Args:
            server: One of "hr", "finance", "legal"
            
        Returns:
            Dictionary mapping scope names to scope values
        """
        server_map = {
            "hr": cls.HR,
            "finance": cls.FINANCE,
            "legal": cls.LEGAL,
        }
        
        scope_class = server_map.get(server.lower())
        if not scope_class:
            raise ValueError(f"Unknown server: {server}. Must be one of: hr, finance, legal")
        
        # Return all class attributes that are strings (scope values)
        return {
            attr: getattr(scope_class, attr)
            for attr in dir(scope_class)
            if not attr.startswith("_") and isinstance(getattr(scope_class, attr), str)
        }


# Convenience functions for common scope combinations
def get_default_hr_scopes() -> str:
    """Get default HR scopes for common operations"""
    return OKTA_SCOPES.HR.EMPLOYEES_READ_BENEFITS_READ


def get_default_finance_scopes() -> str:
    """Get default Finance scopes for common operations"""
    return OKTA_SCOPES.FINANCE.TRANSACTIONS_READ_APPROVAL


def get_default_legal_scopes() -> str:
    """Get default Legal scopes for common operations"""
    return OKTA_SCOPES.LEGAL.COMPLIANCE_READ_VERIFY


def get_cross_agent_scope(source_agent: str, target_agent: str) -> str:
    """
    Get appropriate scope for cross-agent token exchange.
    
    Args:
        source_agent: Source agent name ("hr", "finance", "legal")
        target_agent: Target agent name ("hr", "finance", "legal")
        
    Returns:
        Scope string for the target agent server
    """
    if target_agent.lower() == "hr":
        return OKTA_SCOPES.HR.EMPLOYEES_READ
    elif target_agent.lower() == "finance":
        return OKTA_SCOPES.FINANCE.TRANSACTIONS_READ
    elif target_agent.lower() == "legal":
        return OKTA_SCOPES.LEGAL.COMPLIANCE_READ
    else:
        raise ValueError(f"Unknown target agent: {target_agent}")

