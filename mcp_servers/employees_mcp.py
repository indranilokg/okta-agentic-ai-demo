import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import os

from auth.okta_auth import OktaAuth
from auth.okta_cross_app_access import OktaCrossAppAccessManager

logger = logging.getLogger(__name__)

class EmployeesMCP:
    """
    MCP Server for Employee Lifecycle System (Okta-secured with ID-JAG)
    
    Features:
    - Handles internal employee data, access control, and lifecycle events
    - Validates MCP access tokens via ID-JAG before granting tool access (STEP 4)
    - Provides audit trail with token claims (subject, scope, expiration)
    - Requires valid mcp_token in user_info for all tool calls
    
    Token Flow:
    1. Chat Assistant exchanges ID token for ID-JAG token
    2. Chat Assistant exchanges ID-JAG for MCP access token
    3. Chat Assistant passes mcp_token in user_info to MCP tools
    4. MCP Server validates token before executing any tool
    """
    
    def __init__(self):
        self.okta_auth = OktaAuth()
        # Initialize cross-app access manager with fallback if ID-JAG not configured
        try:
            self.cross_app_access_manager = OktaCrossAppAccessManager()
            logger.info(" EmployeesMCP initialized with ID-JAG token validation")
        except Exception as e:
            logger.warning(f" EmployeesMCP: ID-JAG not available ({type(e).__name__}), running in limited mode")
            self.cross_app_access_manager = None
        
        self.employees_data = self._initialize_mock_data()
        self.tools = self._define_tools()
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define available MCP tools for employee management"""
        return [
            {
                "name": "list_employees",
                "description": "List all active employees with their basic information (department, title, manager). Requires HR, managers, or admin permissions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status_filter": {
                            "type": "string",
                            "enum": ["Active", "Inactive", "All"],
                            "description": "Filter employees by status. Default: Active",
                            "default": "Active"
                        }
                    }
                }
            },
            {
                "name": "get_employee_info",
                "description": "Get detailed information about a specific employee by name or employee ID. Requires HR, managers, or admin permissions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "employee_identifier": {
                            "type": "string",
                            "description": "Employee name (e.g., 'John Smith') or employee ID (e.g., 'EMP001')"
                        }
                    },
                    "required": ["employee_identifier"]
                }
            },
            {
                "name": "get_department_info",
                "description": "Get overview information about all departments including head, employee count, budget, and location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "department_name": {
                            "type": "string",
                            "description": "Optional: Specific department name. If not provided, returns all departments.",
                            "enum": ["Engineering", "Finance", "HR", "Legal", None]
                        }
                    }
                }
            },
            {
                "name": "get_benefits_info",
                "description": "Get information about available employee benefits and enrollment statistics.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_salary_info",
                "description": "Get salary band distribution information. Requires HR or admin permissions.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_onboarding_info",
                "description": "Get information about the employee onboarding process and steps.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
        
    def _initialize_mock_data(self) -> Dict[str, Any]:
        """Initialize mock employee data with rich sample data for demonstration"""
        return {
            "employees": {
                # Engineering Department
                "emp-001": {
                    "id": "emp-001",
                    "employee_id": "EMP001",
                    "name": "Jane Doe",
                    "email": "jane.doe@streamward.com",
                    "department": "Engineering",
                    "title": "VP of Engineering",
                    "manager": None,
                    "hire_date": "2019-06-01",
                    "status": "Active",
                    "location": "San Francisco, CA",
                    "phone": "+1-555-0101",
                    "salary_band": "L7",
                    "benefits": ["Health Insurance", "401k", "Stock Options", "Executive Bonus"],
                    "access_level": "Admin",
                    "last_login": "2025-11-09T14:30:00Z",
                    "reports_count": 8,
                    "team": "Engineering Leadership"
                },
                "emp-002": {
                    "id": "emp-002",
                    "employee_id": "EMP002",
                    "name": "John Smith",
                    "email": "john.smith@streamward.com",
                    "department": "Engineering",
                    "title": "Senior Software Engineer",
                    "manager": "Jane Doe",
                    "hire_date": "2022-03-15",
                    "status": "Active",
                    "location": "San Francisco, CA",
                    "phone": "+1-555-0102",
                    "salary_band": "L5",
                    "benefits": ["Health Insurance", "401k", "Stock Options", "Gym Membership"],
                    "access_level": "Standard",
                    "last_login": "2025-11-09T09:30:00Z",
                    "reports_count": 0,
                    "team": "Backend Platform"
                },
                "emp-003": {
                    "id": "emp-003",
                    "employee_id": "EMP003",
                    "name": "Alice Kumar",
                    "email": "alice.kumar@streamward.com",
                    "department": "Engineering",
                    "title": "Software Engineer (Backend)",
                    "manager": "John Smith",
                    "hire_date": "2023-07-20",
                    "status": "Active",
                    "location": "San Francisco, CA",
                    "phone": "+1-555-0103",
                    "salary_band": "L4",
                    "benefits": ["Health Insurance", "401k", "Stock Options"],
                    "access_level": "Standard",
                    "last_login": "2025-11-09T10:15:00Z",
                    "reports_count": 0,
                    "team": "Backend Platform"
                },
                "emp-004": {
                    "id": "emp-004",
                    "employee_id": "EMP004",
                    "name": "Marcus Thompson",
                    "email": "marcus.thompson@streamward.com",
                    "department": "Engineering",
                    "title": "DevOps Engineer",
                    "manager": "Jane Doe",
                    "hire_date": "2021-11-01",
                    "status": "Active",
                    "location": "Seattle, WA",
                    "phone": "+1-555-0104",
                    "salary_band": "L5",
                    "benefits": ["Health Insurance", "401k", "Stock Options", "Remote Work"],
                    "access_level": "Admin",
                    "last_login": "2025-11-09T08:45:00Z",
                    "reports_count": 2,
                    "team": "Infrastructure"
                },
                # Finance Department
                "emp-005": {
                    "id": "emp-005",
                    "employee_id": "EMP005",
                    "name": "Mike Wilson",
                    "email": "mike.wilson@streamward.com",
                    "department": "Finance",
                    "title": "CFO",
                    "manager": None,
                    "hire_date": "2020-01-15",
                    "status": "Active",
                    "location": "New York, NY",
                    "phone": "+1-555-0105",
                    "salary_band": "L7",
                    "benefits": ["Health Insurance", "401k", "Stock Options", "Executive Bonus", "Company Car"],
                    "access_level": "Admin",
                    "last_login": "2025-11-09T15:00:00Z",
                    "reports_count": 5,
                    "team": "Finance Leadership"
                },
                "emp-006": {
                    "id": "emp-006",
                    "employee_id": "EMP006",
                    "name": "Sarah Johnson",
                    "email": "sarah.johnson@streamward.com",
                    "department": "Finance",
                    "title": "Senior Financial Analyst",
                    "manager": "Mike Wilson",
                    "hire_date": "2021-08-20",
                    "status": "Active",
                    "location": "New York, NY",
                    "phone": "+1-555-0106",
                    "salary_band": "L5",
                    "benefits": ["Health Insurance", "401k", "Stock Options", "Tuition Reimbursement"],
                    "access_level": "Standard",
                    "last_login": "2025-11-09T09:00:00Z",
                    "reports_count": 0,
                    "team": "Financial Planning"
                },
                "emp-007": {
                    "id": "emp-007",
                    "employee_id": "EMP007",
                    "name": "Priya Patel",
                    "email": "priya.patel@streamward.com",
                    "department": "Finance",
                    "title": "Controller",
                    "manager": "Mike Wilson",
                    "hire_date": "2019-03-10",
                    "status": "Active",
                    "location": "New York, NY",
                    "phone": "+1-555-0107",
                    "salary_band": "L6",
                    "benefits": ["Health Insurance", "401k", "Stock Options", "Executive Bonus"],
                    "access_level": "Admin",
                    "last_login": "2025-11-09T11:30:00Z",
                    "reports_count": 3,
                    "team": "Accounting"
                },
                # HR Department
                "emp-008": {
                    "id": "emp-008",
                    "employee_id": "EMP008",
                    "name": "Lisa Brown",
                    "email": "lisa.brown@streamward.com",
                    "department": "HR",
                    "title": "Chief People Officer",
                    "manager": None,
                    "hire_date": "2018-09-05",
                    "status": "Active",
                    "location": "Austin, TX",
                    "phone": "+1-555-0108",
                    "salary_band": "L7",
                    "benefits": ["Health Insurance", "401k", "Stock Options", "Executive Bonus"],
                    "access_level": "Admin",
                    "last_login": "2025-11-09T13:45:00Z",
                    "reports_count": 4,
                    "team": "HR Leadership"
                },
                "emp-009": {
                    "id": "emp-009",
                    "employee_id": "EMP009",
                    "name": "David Chen",
                    "email": "david.chen@streamward.com",
                    "department": "HR",
                    "title": "HR Business Partner",
                    "manager": "Lisa Brown",
                    "hire_date": "2020-11-10",
                    "status": "Active",
                    "location": "Austin, TX",
                    "phone": "+1-555-0109",
                    "salary_band": "L5",
                    "benefits": ["Health Insurance", "401k", "Stock Options", "Flexible PTO"],
                    "access_level": "Elevated",
                    "last_login": "2025-11-09T10:20:00Z",
                    "reports_count": 0,
                    "team": "Talent Management"
                },
                "emp-010": {
                    "id": "emp-010",
                    "employee_id": "EMP010",
                    "name": "Jessica Martinez",
                    "email": "jessica.martinez@streamward.com",
                    "department": "HR",
                    "title": "Recruiting Manager",
                    "manager": "Lisa Brown",
                    "hire_date": "2022-02-14",
                    "status": "Active",
                    "location": "Austin, TX",
                    "phone": "+1-555-0110",
                    "salary_band": "L5",
                    "benefits": ["Health Insurance", "401k", "Stock Options"],
                    "access_level": "Elevated",
                    "last_login": "2025-11-09T09:45:00Z",
                    "reports_count": 2,
                    "team": "Talent Acquisition"
                },
                # Legal Department
                "emp-011": {
                    "id": "emp-011",
                    "employee_id": "EMP011",
                    "name": "Robert Taylor",
                    "email": "robert.taylor@streamward.com",
                    "department": "Legal",
                    "title": "General Counsel",
                    "manager": None,
                    "hire_date": "2017-05-20",
                    "status": "Active",
                    "location": "Chicago, IL",
                    "phone": "+1-555-0111",
                    "salary_band": "L7",
                    "benefits": ["Health Insurance", "401k", "Stock Options", "Executive Bonus", "Legal Services"],
                    "access_level": "Admin",
                    "last_login": "2025-11-09T14:00:00Z",
                    "reports_count": 3,
                    "team": "Legal Leadership"
                },
                "emp-012": {
                    "id": "emp-012",
                    "employee_id": "EMP012",
                    "name": "Emily Davis",
                    "email": "emily.davis@streamward.com",
                    "department": "Legal",
                    "title": "Senior Legal Counsel",
                    "manager": "Robert Taylor",
                    "hire_date": "2023-01-05",
                    "status": "Active",
                    "location": "Chicago, IL",
                    "phone": "+1-555-0112",
                    "salary_band": "L6",
                    "benefits": ["Health Insurance", "401k", "Stock Options", "Legal Insurance"],
                    "access_level": "Elevated",
                    "last_login": "2025-11-09T12:30:00Z",
                    "reports_count": 0,
                    "team": "Corporate Law"
                },
                # Product & Marketing
                "emp-013": {
                    "id": "emp-013",
                    "employee_id": "EMP013",
                    "name": "Rachel Green",
                    "email": "rachel.green@streamward.com",
                    "department": "Product",
                    "title": "Head of Product",
                    "manager": None,
                    "hire_date": "2020-09-01",
                    "status": "Active",
                    "location": "San Francisco, CA",
                    "phone": "+1-555-0113",
                    "salary_band": "L6",
                    "benefits": ["Health Insurance", "401k", "Stock Options", "Executive Bonus"],
                    "access_level": "Elevated",
                    "last_login": "2025-11-09T13:15:00Z",
                    "reports_count": 4,
                    "team": "Product Management"
                },
                "emp-014": {
                    "id": "emp-014",
                    "employee_id": "EMP014",
                    "name": "Kevin Lopez",
                    "email": "kevin.lopez@streamward.com",
                    "department": "Marketing",
                    "title": "Marketing Manager",
                    "manager": None,
                    "hire_date": "2021-05-15",
                    "status": "Active",
                    "location": "New York, NY",
                    "phone": "+1-555-0114",
                    "salary_band": "L5",
                    "benefits": ["Health Insurance", "401k", "Stock Options"],
                    "access_level": "Standard",
                    "last_login": "2025-11-09T10:00:00Z",
                    "reports_count": 3,
                    "team": "Digital Marketing"
                },
                "emp-015": {
                    "id": "emp-015",
                    "employee_id": "EMP015",
                    "name": "Sophia Rodriguez",
                    "email": "sophia.rodriguez@streamward.com",
                    "department": "Sales",
                    "title": "VP of Sales",
                    "manager": None,
                    "hire_date": "2019-08-10",
                    "status": "Active",
                    "location": "New York, NY",
                    "phone": "+1-555-0115",
                    "salary_band": "L7",
                    "benefits": ["Health Insurance", "401k", "Stock Options", "Executive Bonus", "Car Allowance"],
                    "access_level": "Elevated",
                    "last_login": "2025-11-09T15:30:00Z",
                    "reports_count": 6,
                    "team": "Sales Leadership"
                }
            },
            "departments": {
                "Engineering": {
                    "name": "Engineering",
                    "head": "Jane Doe",
                    "employee_count": 45,
                    "budget": 5000000,
                    "budget_used": 4200000,
                    "location": "San Francisco, CA",
                    "description": "Software Development, Infrastructure, DevOps",
                    "teams": 5,
                    "hiring_plan": 8,
                    "avg_tenure_years": 3.2
                },
                "Finance": {
                    "name": "Finance",
                    "head": "Mike Wilson",
                    "employee_count": 12,
                    "budget": 800000,
                    "budget_used": 750000,
                    "location": "New York, NY",
                    "description": "Accounting, Financial Planning, Treasury",
                    "teams": 3,
                    "hiring_plan": 2,
                    "avg_tenure_years": 4.1
                },
                "HR": {
                    "name": "Human Resources",
                    "head": "Lisa Brown",
                    "employee_count": 8,
                    "budget": 400000,
                    "budget_used": 380000,
                    "location": "Austin, TX",
                    "description": "Talent Acquisition, Employee Relations, Compensation & Benefits",
                    "teams": 3,
                    "hiring_plan": 3,
                    "avg_tenure_years": 2.8
                },
                "Legal": {
                    "name": "Legal",
                    "head": "Robert Taylor",
                    "employee_count": 5,
                    "budget": 300000,
                    "budget_used": 290000,
                    "location": "Chicago, IL",
                    "description": "Corporate Law, Compliance, Contracts",
                    "teams": 2,
                    "hiring_plan": 1,
                    "avg_tenure_years": 5.3
                },
                "Product": {
                    "name": "Product",
                    "head": "Rachel Green",
                    "employee_count": 12,
                    "budget": 900000,
                    "budget_used": 850000,
                    "location": "San Francisco, CA",
                    "description": "Product Management, Product Strategy, UX Research",
                    "teams": 2,
                    "hiring_plan": 3,
                    "avg_tenure_years": 2.5
                },
                "Marketing": {
                    "name": "Marketing",
                    "head": "Kevin Lopez",
                    "employee_count": 15,
                    "budget": 1200000,
                    "budget_used": 1050000,
                    "location": "New York, NY",
                    "description": "Digital Marketing, Content, Brand, Demand Gen",
                    "teams": 4,
                    "hiring_plan": 2,
                    "avg_tenure_years": 2.1
                },
                "Sales": {
                    "name": "Sales",
                    "head": "Sophia Rodriguez",
                    "employee_count": 28,
                    "budget": 3500000,
                    "budget_used": 3200000,
                    "location": "New York, NY",
                    "description": "Enterprise Sales, Mid-Market, Sales Engineering",
                    "teams": 3,
                    "hiring_plan": 6,
                    "avg_tenure_years": 3.4
                }
            }
        }

    async def query(self, message: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process employee-related queries
        """
        try:
            message_lower = message.lower()
            
            # Route to appropriate handler
            if "list" in message_lower or "show" in message_lower:
                return await self._handle_list_employees(message, user_info)
            elif "info" in message_lower or "details" in message_lower:
                return await self._handle_employee_info(message, user_info)
            elif "department" in message_lower:
                return await self._handle_department_info(message, user_info)
            elif "benefits" in message_lower:
                return await self._handle_benefits_info(message, user_info)
            elif "salary" in message_lower or "compensation" in message_lower:
                return await self._handle_salary_info(message, user_info)
            elif "onboard" in message_lower or "new employee" in message_lower:
                return await self._handle_onboarding_info(message, user_info)
            else:
                return await self._handle_general_query(message, user_info)
                
        except Exception as e:
            logger.error(f"Error processing employee query: {e}")
            return {
                "response": "I encountered an error processing your employee query. Please try again.",
                "metadata": {"error": str(e)}
            }

    async def _handle_list_employees(self, message: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle employee listing requests"""
        employees = self.employees_data["employees"]
        
        # Check if user has permission to view employee list
        if not self._has_permission(user_info, "view_employee_list"):
            return {
                "response": "You don't have permission to view the employee list. Please contact HR for access.",
                "metadata": {"error": "insufficient_permissions"}
            }
        
        response = "**Current Employees:**\n\n"
        for emp_id, employee in employees.items():
            if employee['status'] == 'Active':
                response += f"• **{employee['name']}** ({employee['employee_id']})\n"
                response += f"  - Department: {employee['department']}\n"
                response += f"  - Title: {employee['title']}\n"
                response += f"  - Manager: {employee['manager']}\n\n"
        
        return {
            "response": response,
            "metadata": {
                "total_employees": len(employees),
                "active_employees": len([e for e in employees.values() if e['status'] == 'Active']),
                "query_type": "list_employees"
            }
        }

    async def _handle_employee_info(self, message: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle specific employee information requests"""
        # Extract employee name or ID from message
        employee_identifier = self._extract_employee_identifier(message)
        
        if not employee_identifier:
            return {
                "response": "I need to know which employee you're asking about. Please specify the employee name or ID.",
                "metadata": {"query_type": "employee_info", "error": "no_employee_specified"}
            }
        
        # Find employee
        employee = self._find_employee_by_identifier(employee_identifier)
        
        if not employee:
            return {
                "response": f"I couldn't find an employee matching '{employee_identifier}'. Please check the name or ID and try again.",
                "metadata": {"query_type": "employee_info", "searched_identifier": employee_identifier}
            }
        
        # Check permissions for detailed info
        if not self._has_permission(user_info, "view_employee_details"):
            return {
                "response": f"Employee {employee['name']} found, but you don't have permission to view detailed information.",
                "metadata": {"employee_id": employee['id'], "error": "insufficient_permissions"}
            }
        
        response = f"**{employee['name']}** Employee Information:\n\n"
        response += f"• **Employee ID**: {employee['employee_id']}\n"
        response += f"• **Email**: {employee['email']}\n"
        response += f"• **Department**: {employee['department']}\n"
        response += f"• **Title**: {employee['title']}\n"
        response += f"• **Manager**: {employee['manager']}\n"
        response += f"• **Hire Date**: {employee['hire_date']}\n"
        response += f"• **Status**: {employee['status']}\n"
        response += f"• **Location**: {employee['location']}\n"
        response += f"• **Phone**: {employee['phone']}\n"
        response += f"• **Salary Band**: {employee['salary_band']}\n"
        response += f"• **Benefits**: {', '.join(employee['benefits'])}\n"
        response += f"• **Access Level**: {employee['access_level']}\n"
        response += f"• **Last Login**: {employee['last_login']}\n"
        
        return {
            "response": response,
            "metadata": {
                "employee_id": employee['id'],
                "query_type": "employee_info"
            }
        }

    async def _handle_department_info(self, message: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle department information requests"""
        departments = self.employees_data["departments"]
        
        response = "**Department Overview:**\n\n"
        for dept_name, dept_info in departments.items():
            response += f"• **{dept_name}**\n"
            response += f"  - Head: {dept_info['head']}\n"
            response += f"  - Employees: {dept_info['employee_count']}\n"
            response += f"  - Budget: ${dept_info['budget']:,}\n"
            response += f"  - Location: {dept_info['location']}\n\n"
        
        return {
            "response": response,
            "metadata": {
                "total_departments": len(departments),
                "query_type": "department_info"
            }
        }

    async def _handle_benefits_info(self, message: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle benefits information requests"""
        employees = self.employees_data["employees"]
        
        # Aggregate benefits data
        all_benefits = set()
        for employee in employees.values():
            all_benefits.update(employee['benefits'])
        
        response = "**Available Benefits:**\n\n"
        for benefit in sorted(all_benefits):
            count = sum(1 for emp in employees.values() if benefit in emp['benefits'])
            response += f"• **{benefit}**: {count} employees\n"
        
        response += "\n**Benefits Summary:**\n"
        response += f"• Total Unique Benefits: {len(all_benefits)}\n"
        response += f"• Most Common: {max(all_benefits, key=lambda b: sum(1 for emp in employees.values() if b in emp['benefits']))}\n"
        
        return {
            "response": response,
            "metadata": {
                "total_benefits": len(all_benefits),
                "benefits_list": list(all_benefits),
                "query_type": "benefits_info"
            }
        }

    async def _handle_salary_info(self, message: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle salary/compensation information requests"""
        # Check permissions for salary information
        if not self._has_permission(user_info, "view_salary_info"):
            return {
                "response": "You don't have permission to view salary information. Please contact HR for access.",
                "metadata": {"error": "insufficient_permissions"}
            }
        
        employees = self.employees_data["employees"]
        
        # Group by salary band
        salary_bands = {}
        for employee in employees.values():
            band = employee['salary_band']
            if band not in salary_bands:
                salary_bands[band] = []
            salary_bands[band].append(employee['name'])
        
        response = "**Salary Band Distribution:**\n\n"
        for band, names in salary_bands.items():
            response += f"• **{band}**: {', '.join(names)}\n"
        
        return {
            "response": response,
            "metadata": {
                "salary_bands": salary_bands,
                "query_type": "salary_info"
            }
        }

    async def _handle_onboarding_info(self, message: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle onboarding information requests"""
        response = "**Employee Onboarding Process:**\n\n"
        response += "1. **Pre-boarding** (1 week before start date)\n"
        response += "   - Send welcome email with company information\n"
        response += "   - Set up IT accounts and access\n"
        response += "   - Schedule orientation session\n\n"
        response += "2. **First Day**\n"
        response += "   - Complete HR paperwork\n"
        response += "   - IT setup and equipment assignment\n"
        response += "   - Department introduction\n\n"
        response += "3. **First Week**\n"
        response += "   - Training sessions\n"
        response += "   - Buddy assignment\n"
        response += "   - Goal setting meeting\n\n"
        response += "4. **First Month**\n"
        response += "   - Regular check-ins\n"
        response += "   - Performance review setup\n"
        response += "   - Benefits enrollment\n\n"
        response += "Would you like me to initiate the onboarding process for a new employee?"
        
        return {
            "response": response,
            "metadata": {"query_type": "onboarding_info"}
        }

    async def _handle_general_query(self, message: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general employee queries"""
        response = "I can help you with employee information including:\n\n"
        response += "• **Employee Listings** - Show current employees\n"
        response += "• **Employee Details** - Get specific employee information\n"
        response += "• **Department Information** - View department overview\n"
        response += "• **Benefits Information** - Check available benefits\n"
        response += "• **Onboarding Process** - Learn about new employee onboarding\n\n"
        response += "What would you like to know about our employees?"
        
        return {
            "response": response,
            "metadata": {"query_type": "general_help"}
        }

    def _extract_employee_identifier(self, message: str) -> Optional[str]:
        """Extract employee name or ID from message"""
        message_lower = message.lower()
        
        # Check for employee IDs
        import re
        emp_id_match = re.search(r'emp\d{3}', message_lower)
        if emp_id_match:
            return emp_id_match.group().upper()
        
        # Check for known employee names
        employee_names = ["john smith", "sarah johnson", "david chen", "emily davis"]
        for name in employee_names:
            if name in message_lower:
                return name.title()
        
        # Check for partial matches
        if "john" in message_lower:
            return "John Smith"
        elif "sarah" in message_lower:
            return "Sarah Johnson"
        elif "david" in message_lower:
            return "David Chen"
        elif "emily" in message_lower:
            return "Emily Davis"
        
        return None

    def _find_employee_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Find employee by name or ID"""
        employees = self.employees_data["employees"]
        
        # Check by employee ID first
        for employee in employees.values():
            if employee['employee_id'].lower() == identifier.lower():
                return employee
        
        # Check by name
        for employee in employees.values():
            if identifier.lower() in employee['name'].lower():
                return employee
        
        return None

    def _has_permission(self, user_info: Dict[str, Any], permission: str) -> bool:
        """Check if user has specific permission based on OAuth scope"""
        # Check OAuth scope from MCP token claims
        token_claims = user_info.get("mcp_token_claims", {})
        scope = token_claims.get("scope", "")
        
        # Scope-based permission mapping
        # mcp:read = read-only access to employee data
        # mcp:write = write/modify access to employee data
        permission_scope_map = {
            "view_employee_list": ["mcp:read", "mcp:write"],
            "view_employee_details": ["mcp:read", "mcp:write"],
            "view_salary_info": ["mcp:read", "mcp:write"],
            "edit_employee": ["mcp:write"],
            "delete_employee": ["mcp:write"]
        }
        
        required_scopes = permission_scope_map.get(permission, [])
        
        # Check if user has the required scope
        has_permission = any(req_scope in scope for req_scope in required_scopes)
        
        if has_permission:
            logger.info(f" Permission '{permission}' granted (scope: {scope})")
        else:
            logger.warning(f" Permission '{permission}' denied (scope: {scope})")
        
        return has_permission

    async def get_employee_by_id(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Get employee by ID"""
        return self.employees_data["employees"].get(employee_id)

    async def update_employee(self, employee_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update employee information"""
        if employee_id not in self.employees_data["employees"]:
            raise ValueError(f"Employee {employee_id} not found")
        
        employee = self.employees_data["employees"][employee_id]
        employee.update(updates)
        employee["updated_at"] = datetime.now().isoformat()
        
        return employee
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available MCP tools"""
        return self.tools
    
    async def _validate_mcp_token(self, user_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validate the MCP access token from user_info before granting tool access.
        
        Implements STEP 4 of ID-JAG flow: Token verification
        
        Args:
            user_info: Dict containing 'mcp_token' (the access token from Chat Assistant)
            
        Returns:
            Token claims if valid, None if invalid or missing
        """
        try:
            mcp_token = user_info.get("mcp_token")
            
            # If ID-JAG is not available, allow access with demo permissions for testing
            if not self.cross_app_access_manager:
                logger.info("[MCP_EMPLOYEES] ID-JAG not available, allowing access in demo mode")
                return {
                    "valid": True,
                    "sub": user_info.get("sub", "demo-user"),
                    "scope": "mcp:read mcp:write",  # Full permissions for demo
                    "aud": "api://streamward-chat"
                }
            
            if not mcp_token:
                logger.warning(" No MCP token provided in user_info. Access denied.")
                return None
            
            logger.debug("[MCP_EMPLOYEES] Validating access token")
            
            # Verify the token using the cross-app access manager
            token_claims = await self.cross_app_access_manager.verify_mcp_token(mcp_token)
            
            if token_claims and token_claims.get("valid"):
                logger.info(f"[MCP_EMPLOYEES] Token validated: subject={token_claims.get('sub')}, scope={token_claims.get('scope')}")
                return token_claims
            else:
                logger.error("[MCP_EMPLOYEES] Token validation failed. Access denied.")
                return None
                
        except Exception as e:
            logger.error(f"[MCP_EMPLOYEES] Token validation error: {str(e)}", exc_info=True)
            return None
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any], user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool by name with arguments.
        
        REQUIRES valid MCP token for access control.
        """
        try:
            # STEP 4: Validate MCP token before granting access
            token_claims = await self._validate_mcp_token(user_info)
            
            if not token_claims:
                return {
                    "error": "unauthorized",
                    "message": "Invalid or missing MCP token. Please authenticate via ID-JAG token exchange."
                }
            
            # Add token claims to user_info for audit trail
            user_info["mcp_token_claims"] = token_claims
            user_info["mcp_subject"] = token_claims.get("sub")
            user_info["mcp_scope"] = token_claims.get("scope")
            
            logger.debug(f"[MCP_EMPLOYEES] Granting tool access: tool={tool_name}, sub={token_claims.get('sub')}, scope={token_claims.get('scope')}")
            
            if tool_name == "list_employees":
                status_filter = arguments.get("status_filter", "Active")
                return await self._tool_list_employees(status_filter, user_info)
            elif tool_name == "get_employee_info":
                employee_identifier = arguments.get("employee_identifier")
                if not employee_identifier:
                    return {"error": "employee_identifier is required"}
                return await self._tool_get_employee_info(employee_identifier, user_info)
            elif tool_name == "get_department_info":
                department_name = arguments.get("department_name")
                return await self._tool_get_department_info(department_name, user_info)
            elif tool_name == "get_benefits_info":
                return await self._tool_get_benefits_info(user_info)
            elif tool_name == "get_salary_info":
                return await self._tool_get_salary_info(user_info)
            elif tool_name == "get_onboarding_info":
                return await self._tool_get_onboarding_info(user_info)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {"error": str(e)}
    
    async def _tool_list_employees(self, status_filter: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Tool implementation for list_employees"""
        if not self._has_permission(user_info, "view_employee_list"):
            return {
                "error": "insufficient_permissions",
                "message": "You don't have permission to view the employee list. Please contact HR for access."
            }
        
        employees = self.employees_data["employees"]
        filtered_employees = []
        
        for emp_id, employee in employees.items():
            if status_filter == "All" or employee['status'] == status_filter:
                filtered_employees.append({
                    "employee_id": employee['employee_id'],
                    "name": employee['name'],
                    "department": employee['department'],
                    "title": employee['title'],
                    "manager": employee['manager'],
                    "status": employee['status']
                })
        
        return {
            "employees": filtered_employees,
            "total_count": len(filtered_employees),
            "status_filter": status_filter
        }
    
    async def _tool_get_employee_info(self, employee_identifier: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Tool implementation for get_employee_info"""
        if not self._has_permission(user_info, "view_employee_details"):
            return {
                "error": "insufficient_permissions",
                "message": "You don't have permission to view detailed employee information."
            }
        
        employee = self._find_employee_by_identifier(employee_identifier)
        if not employee:
            return {
                "error": "employee_not_found",
                "message": f"Employee '{employee_identifier}' not found."
            }
        
        return {
            "employee": {
                "id": employee['id'],
                "employee_id": employee['employee_id'],
                "name": employee['name'],
                "email": employee['email'],
                "department": employee['department'],
                "title": employee['title'],
                "manager": employee['manager'],
                "hire_date": employee['hire_date'],
                "status": employee['status'],
                "location": employee['location'],
                "phone": employee['phone'],
                "salary_band": employee['salary_band'],
                "benefits": employee['benefits'],
                "access_level": employee['access_level'],
                "last_login": employee['last_login']
            }
        }
    
    async def _tool_get_department_info(self, department_name: Optional[str], user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Tool implementation for get_department_info"""
        departments = self.employees_data["departments"]
        
        if department_name:
            if department_name in departments:
                return {
                    "department": {
                        "name": department_name,
                        **departments[department_name]
                    }
                }
            else:
                return {
                    "error": "department_not_found",
                    "message": f"Department '{department_name}' not found."
                }
        else:
            return {
                "departments": [
                    {"name": name, **info} 
                    for name, info in departments.items()
                ],
                "total_count": len(departments)
            }
    
    async def _tool_get_benefits_info(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Tool implementation for get_benefits_info"""
        employees = self.employees_data["employees"]
        
        all_benefits = set()
        benefit_enrollments = {}
        
        for employee in employees.values():
            for benefit in employee['benefits']:
                all_benefits.add(benefit)
                if benefit not in benefit_enrollments:
                    benefit_enrollments[benefit] = 0
                benefit_enrollments[benefit] += 1
        
        return {
            "benefits": [
                {
                    "name": benefit,
                    "enrollment_count": benefit_enrollments[benefit]
                }
                for benefit in sorted(all_benefits)
            ],
            "total_unique_benefits": len(all_benefits),
            "total_employees": len(employees)
        }
    
    async def _tool_get_salary_info(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Tool implementation for get_salary_info"""
        if not self._has_permission(user_info, "view_salary_info"):
            return {
                "error": "insufficient_permissions",
                "message": "You don't have permission to view salary information. Please contact HR for access."
            }
        
        employees = self.employees_data["employees"]
        salary_bands = {}
        
        for employee in employees.values():
            band = employee['salary_band']
            if band not in salary_bands:
                salary_bands[band] = []
            salary_bands[band].append(employee['name'])
        
        return {
            "salary_bands": {
                band: {
                    "employees": names,
                    "count": len(names)
                }
                for band, names in salary_bands.items()
            }
        }
    
    async def _tool_get_onboarding_info(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Tool implementation for get_onboarding_info"""
        return {
            "onboarding_process": {
                "pre_boarding": {
                    "timeline": "1 week before start date",
                    "steps": [
                        "Send welcome email with company information",
                        "Set up IT accounts and access",
                        "Schedule orientation session"
                    ]
                },
                "first_day": {
                    "steps": [
                        "Complete HR paperwork",
                        "IT setup and equipment assignment",
                        "Department introduction"
                    ]
                },
                "first_week": {
                    "steps": [
                        "Training sessions",
                        "Buddy assignment",
                        "Goal setting meeting"
                    ]
                },
                "first_month": {
                    "steps": [
                        "Regular check-ins",
                        "Performance review setup",
                        "Benefits enrollment"
                    ]
                }
            }
        }
