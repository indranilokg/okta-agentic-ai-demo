import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from auth.okta_auth import OktaAuth

logger = logging.getLogger(__name__)

class EmployeesMCP:
    """
    MCP Server for Employee Lifecycle System (Okta-secured)
    Handles internal employee data, access control, and lifecycle events
    """
    
    def __init__(self):
        self.okta_auth = OktaAuth()
        self.employees_data = self._initialize_mock_data()
        
    def _initialize_mock_data(self) -> Dict[str, Any]:
        """Initialize mock employee data"""
        return {
            "employees": {
                "emp-001": {
                    "id": "emp-001",
                    "employee_id": "EMP001",
                    "name": "John Smith",
                    "email": "john.smith@streamward.com",
                    "department": "Engineering",
                    "title": "Senior Software Engineer",
                    "manager": "Jane Doe",
                    "hire_date": "2022-03-15",
                    "status": "Active",
                    "location": "San Francisco, CA",
                    "phone": "+1-555-0101",
                    "salary_band": "L5",
                    "benefits": ["Health Insurance", "401k", "Stock Options"],
                    "access_level": "Standard",
                    "last_login": "2024-01-15T09:30:00Z"
                },
                "emp-002": {
                    "id": "emp-002",
                    "employee_id": "EMP002",
                    "name": "Sarah Johnson",
                    "email": "sarah.johnson@streamward.com",
                    "department": "Finance",
                    "title": "Financial Analyst",
                    "manager": "Mike Wilson",
                    "hire_date": "2021-08-20",
                    "status": "Active",
                    "location": "New York, NY",
                    "phone": "+1-555-0102",
                    "salary_band": "L4",
                    "benefits": ["Health Insurance", "401k", "Dental"],
                    "access_level": "Standard",
                    "last_login": "2024-01-15T08:45:00Z"
                },
                "emp-003": {
                    "id": "emp-003",
                    "employee_id": "EMP003",
                    "name": "David Chen",
                    "email": "david.chen@streamward.com",
                    "department": "HR",
                    "title": "HR Business Partner",
                    "manager": "Lisa Brown",
                    "hire_date": "2020-11-10",
                    "status": "Active",
                    "location": "Austin, TX",
                    "phone": "+1-555-0103",
                    "salary_band": "L5",
                    "benefits": ["Health Insurance", "401k", "Stock Options", "Flexible PTO"],
                    "access_level": "Elevated",
                    "last_login": "2024-01-15T10:15:00Z"
                },
                "emp-004": {
                    "id": "emp-004",
                    "employee_id": "EMP004",
                    "name": "Emily Davis",
                    "email": "emily.davis@streamward.com",
                    "department": "Legal",
                    "title": "Legal Counsel",
                    "manager": "Robert Taylor",
                    "hire_date": "2023-01-05",
                    "status": "Active",
                    "location": "Chicago, IL",
                    "phone": "+1-555-0104",
                    "salary_band": "L6",
                    "benefits": ["Health Insurance", "401k", "Stock Options", "Legal Insurance"],
                    "access_level": "Elevated",
                    "last_login": "2024-01-15T11:00:00Z"
                }
            },
            "departments": {
                "Engineering": {
                    "name": "Engineering",
                    "head": "Jane Doe",
                    "employee_count": 45,
                    "budget": 5000000,
                    "location": "San Francisco, CA"
                },
                "Finance": {
                    "name": "Finance",
                    "head": "Mike Wilson",
                    "employee_count": 12,
                    "budget": 800000,
                    "location": "New York, NY"
                },
                "HR": {
                    "name": "Human Resources",
                    "head": "Lisa Brown",
                    "employee_count": 8,
                    "budget": 400000,
                    "location": "Austin, TX"
                },
                "Legal": {
                    "name": "Legal",
                    "head": "Robert Taylor",
                    "employee_count": 5,
                    "budget": 300000,
                    "location": "Chicago, IL"
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
        """Check if user has specific permission"""
        # Mock permission checking based on user groups/roles
        user_groups = user_info.get("groups", [])
        
        permission_map = {
            "view_employee_list": ["hr", "managers", "admin"],
            "view_employee_details": ["hr", "managers", "admin"],
            "view_salary_info": ["hr", "admin"]
        }
        
        required_groups = permission_map.get(permission, [])
        return any(group in user_groups for group in required_groups)

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
