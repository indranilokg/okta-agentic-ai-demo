import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from auth.auth0_auth import Auth0Auth

logger = logging.getLogger(__name__)

class PartnersMCP:
    """
    MCP Server for Partner Management System (Auth0-secured)
    Handles external partner data, contracts, and integrations
    """
    
    def __init__(self):
        # Try to initialize Auth0, but don't fail if not configured
        try:
            self.auth0 = Auth0Auth()
        except ValueError:
            logger.warning("Auth0 not configured - PartnersMCP will operate in demo mode only")
            self.auth0 = None
        
        self.partners_data = self._initialize_mock_data()
        self.tools = self._define_tools()
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define available MCP tools for partner management"""
        return [
            {
                "name": "list_partners",
                "description": "List all partners with their type, SLA level, contract status, and contact information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status_filter": {
                            "type": "string",
                            "enum": ["Active", "Pending", "Inactive", "All"],
                            "description": "Filter partners by contract status. Default: All",
                            "default": "All"
                        }
                    }
                }
            },
            {
                "name": "get_partner_info",
                "description": "Get detailed information about a specific partner by name.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "partner_name": {
                            "type": "string",
                            "description": "Partner name (e.g., 'TechCorp Solutions', 'FinanceFlow Inc', 'LegalEase Partners')"
                        }
                    },
                    "required": ["partner_name"]
                }
            },
            {
                "name": "get_contract_info",
                "description": "Get information about active contracts with partners including value, period, and terms.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "contract_id": {
                            "type": "string",
                            "description": "Optional: Specific contract ID. If not provided, returns all contracts."
                        }
                    }
                }
            },
            {
                "name": "get_sla_info",
                "description": "Get SLA (Service Level Agreement) information grouped by SLA level with definitions.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_revenue_info",
                "description": "Get partner revenue share information and financial statistics.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
        
    def _initialize_mock_data(self) -> Dict[str, Any]:
        """Initialize mock partner data"""
        return {
            "partners": {
                "partner-001": {
                    "id": "partner-001",
                    "name": "TechCorp Solutions",
                    "type": "Technology Partner",
                    "sla_level": "Premium",
                    "contract_status": "Active",
                    "contact_email": "partnerships@techcorp.com",
                    "integration_tokens": ["api-token-001", "webhook-token-001"],
                    "last_activity": "2024-01-15T10:30:00Z",
                    "services": ["API Integration", "Data Analytics", "Cloud Services"],
                    "revenue_share": 15.5,
                    "contract_start": "2023-06-01",
                    "contract_end": "2025-05-31"
                },
                "partner-002": {
                    "id": "partner-002",
                    "name": "FinanceFlow Inc",
                    "type": "Financial Services",
                    "sla_level": "Standard",
                    "contract_status": "Active",
                    "contact_email": "business@financeflow.com",
                    "integration_tokens": ["api-token-002"],
                    "last_activity": "2024-01-14T15:45:00Z",
                    "services": ["Payment Processing", "Financial Analytics"],
                    "revenue_share": 8.2,
                    "contract_start": "2023-09-15",
                    "contract_end": "2024-09-14"
                },
                "partner-003": {
                    "id": "partner-003",
                    "name": "LegalEase Partners",
                    "type": "Legal Services",
                    "sla_level": "Premium",
                    "contract_status": "Pending",
                    "contact_email": "legal@legalease.com",
                    "integration_tokens": [],
                    "last_activity": None,
                    "services": ["Contract Review", "Compliance Consulting"],
                    "revenue_share": 12.0,
                    "contract_start": "2024-02-01",
                    "contract_end": "2026-01-31"
                }
            },
            "contracts": {
                "contract-001": {
                    "id": "contract-001",
                    "partner_id": "partner-001",
                    "type": "Technology Integration",
                    "status": "Active",
                    "value": 500000,
                    "start_date": "2023-06-01",
                    "end_date": "2025-05-31",
                    "terms": ["SLA: 99.9% uptime", "24/7 support", "Monthly reporting"]
                },
                "contract-002": {
                    "id": "contract-002",
                    "partner_id": "partner-002",
                    "type": "Financial Services",
                    "status": "Active",
                    "value": 250000,
                    "start_date": "2023-09-15",
                    "end_date": "2024-09-14",
                    "terms": ["SLA: 99.5% uptime", "Business hours support", "Quarterly reporting"]
                }
            }
        }

    async def query(self, message: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process partner-related queries
        """
        try:
            message_lower = message.lower()
            
            # Route to appropriate handler
            if "list" in message_lower or "show" in message_lower:
                return await self._handle_list_partners(message, user_info)
            elif "info" in message_lower or "details" in message_lower:
                return await self._handle_partner_info(message, user_info)
            elif "contract" in message_lower:
                return await self._handle_contract_info(message, user_info)
            elif "sla" in message_lower:
                return await self._handle_sla_info(message, user_info)
            elif "revenue" in message_lower or "financial" in message_lower:
                return await self._handle_revenue_info(message, user_info)
            else:
                return await self._handle_general_query(message, user_info)
                
        except Exception as e:
            logger.error(f"Error processing partner query: {e}")
            return {
                "response": "I encountered an error processing your partner query. Please try again.",
                "metadata": {"error": str(e)}
            }

    async def _handle_list_partners(self, message: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle partner listing requests"""
        partners = self.partners_data["partners"]
        
        response = "Here are our current partners:\n\n"
        for partner_id, partner in partners.items():
            response += f"• **{partner['name']}** ({partner['type']})\n"
            response += f"  - SLA Level: {partner['sla_level']}\n"
            response += f"  - Status: {partner['contract_status']}\n"
            response += f"  - Contact: {partner['contact_email']}\n\n"
        
        return {
            "response": response,
            "metadata": {
                "total_partners": len(partners),
                "active_partners": len([p for p in partners.values() if p['contract_status'] == 'Active']),
                "query_type": "list_partners"
            }
        }

    async def _handle_partner_info(self, message: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle specific partner information requests"""
        # Extract partner name or ID from message
        partner_name = self._extract_partner_name(message)
        
        if not partner_name:
            return {
                "response": "I need to know which partner you're asking about. Please specify the partner name.",
                "metadata": {"query_type": "partner_info", "error": "no_partner_specified"}
            }
        
        # Find partner
        partner = self._find_partner_by_name(partner_name)
        
        if not partner:
            return {
                "response": f"I couldn't find a partner matching '{partner_name}'. Please check the partner name and try again.",
                "metadata": {"query_type": "partner_info", "searched_name": partner_name}
            }
        
        response = f"**{partner['name']}** Partner Information:\n\n"
        response += f"• **Type**: {partner['type']}\n"
        response += f"• **SLA Level**: {partner['sla_level']}\n"
        response += f"• **Contract Status**: {partner['contract_status']}\n"
        response += f"• **Contact Email**: {partner['contact_email']}\n"
        response += f"• **Services**: {', '.join(partner['services'])}\n"
        response += f"• **Revenue Share**: {partner['revenue_share']}%\n"
        response += f"• **Contract Period**: {partner['contract_start']} to {partner['contract_end']}\n"
        response += f"• **Last Activity**: {partner['last_activity'] or 'No recent activity'}\n"
        
        return {
            "response": response,
            "metadata": {
                "partner_id": partner['id'],
                "query_type": "partner_info"
            }
        }

    async def _handle_contract_info(self, message: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle contract information requests"""
        contracts = self.partners_data["contracts"]
        
        response = "**Active Contracts Overview:**\n\n"
        for contract_id, contract in contracts.items():
            partner = self.partners_data["partners"][contract["partner_id"]]
            response += f"• **{contract['id']}** - {partner['name']}\n"
            response += f"  - Type: {contract['type']}\n"
            response += f"  - Value: ${contract['value']:,}\n"
            response += f"  - Period: {contract['start_date']} to {contract['end_date']}\n"
            response += f"  - Status: {contract['status']}\n\n"
        
        return {
            "response": response,
            "metadata": {
                "total_contracts": len(contracts),
                "query_type": "contract_info"
            }
        }

    async def _handle_sla_info(self, message: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle SLA information requests"""
        partners = self.partners_data["partners"]
        
        # Group by SLA level
        sla_levels = {}
        for partner in partners.values():
            level = partner['sla_level']
            if level not in sla_levels:
                sla_levels[level] = []
            sla_levels[level].append(partner['name'])
        
        response = "**Partner SLA Levels:**\n\n"
        for level, partner_names in sla_levels.items():
            response += f"• **{level} SLA**: {', '.join(partner_names)}\n"
        
        response += "\n**SLA Definitions:**\n"
        response += "• **Premium**: 99.9% uptime, 24/7 support, <1hr response time\n"
        response += "• **Standard**: 99.5% uptime, business hours support, <4hr response time\n"
        response += "• **Basic**: 99.0% uptime, business hours support, <8hr response time\n"
        
        return {
            "response": response,
            "metadata": {
                "sla_levels": sla_levels,
                "query_type": "sla_info"
            }
        }

    async def _handle_revenue_info(self, message: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle revenue and financial information requests"""
        partners = self.partners_data["partners"]
        
        total_revenue_share = sum(partner['revenue_share'] for partner in partners.values())
        avg_revenue_share = total_revenue_share / len(partners)
        
        response = "**Partner Revenue Information:**\n\n"
        for partner in partners.values():
            response += f"• **{partner['name']}**: {partner['revenue_share']}% revenue share\n"
        
        response += f"\n**Summary:**\n"
        response += f"• Total Partners: {len(partners)}\n"
        response += f"• Average Revenue Share: {avg_revenue_share:.1f}%\n"
        response += f"• Total Revenue Share: {total_revenue_share:.1f}%\n"
        
        return {
            "response": response,
            "metadata": {
                "total_partners": len(partners),
                "total_revenue_share": total_revenue_share,
                "avg_revenue_share": avg_revenue_share,
                "query_type": "revenue_info"
            }
        }

    async def _handle_general_query(self, message: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general partner queries"""
        response = "I can help you with partner information including:\n\n"
        response += "• **Partner Listings** - Show all current partners\n"
        response += "• **Partner Details** - Get specific partner information\n"
        response += "• **Contract Information** - View active contracts\n"
        response += "• **SLA Levels** - Check service level agreements\n"
        response += "• **Revenue Data** - Partner financial information\n\n"
        response += "What would you like to know about our partners?"
        
        return {
            "response": response,
            "metadata": {"query_type": "general_help"}
        }

    def _extract_partner_name(self, message: str) -> Optional[str]:
        """Extract partner name from message"""
        message_lower = message.lower()
        
        # Check for known partner names
        partner_names = ["techcorp", "financeflow", "legalease"]
        for name in partner_names:
            if name in message_lower:
                return name.title()
        
        # Check for partial matches
        if "tech" in message_lower:
            return "TechCorp"
        elif "finance" in message_lower:
            return "FinanceFlow"
        elif "legal" in message_lower:
            return "LegalEase"
        
        return None

    def _find_partner_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find partner by name"""
        partners = self.partners_data["partners"]
        
        for partner in partners.values():
            if name.lower() in partner['name'].lower():
                return partner
        
        return None

    async def get_partner_by_id(self, partner_id: str) -> Optional[Dict[str, Any]]:
        """Get partner by ID"""
        return self.partners_data["partners"].get(partner_id)

    async def update_partner(self, partner_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update partner information"""
        if partner_id not in self.partners_data["partners"]:
            raise ValueError(f"Partner {partner_id} not found")
        
        partner = self.partners_data["partners"][partner_id]
        partner.update(updates)
        partner["updated_at"] = datetime.now().isoformat()
        
        return partner
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available MCP tools"""
        return self.tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any], user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool by name with arguments"""
        try:
            if tool_name == "list_partners":
                status_filter = arguments.get("status_filter", "All")
                return await self._tool_list_partners(status_filter, user_info)
            elif tool_name == "get_partner_info":
                partner_name = arguments.get("partner_name")
                if not partner_name:
                    return {"error": "partner_name is required"}
                return await self._tool_get_partner_info(partner_name, user_info)
            elif tool_name == "get_contract_info":
                contract_id = arguments.get("contract_id")
                return await self._tool_get_contract_info(contract_id, user_info)
            elif tool_name == "get_sla_info":
                return await self._tool_get_sla_info(user_info)
            elif tool_name == "get_revenue_info":
                return await self._tool_get_revenue_info(user_info)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {"error": str(e)}
    
    async def _tool_list_partners(self, status_filter: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Tool implementation for list_partners"""
        partners = self.partners_data["partners"]
        filtered_partners = []
        
        for partner_id, partner in partners.items():
            if status_filter == "All" or partner['contract_status'] == status_filter:
                filtered_partners.append({
                    "id": partner['id'],
                    "name": partner['name'],
                    "type": partner['type'],
                    "sla_level": partner['sla_level'],
                    "contract_status": partner['contract_status'],
                    "contact_email": partner['contact_email']
                })
        
        return {
            "partners": filtered_partners,
            "total_count": len(filtered_partners),
            "status_filter": status_filter
        }
    
    async def _tool_get_partner_info(self, partner_name: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Tool implementation for get_partner_info"""
        partner = self._find_partner_by_name(partner_name)
        if not partner:
            return {
                "error": "partner_not_found",
                "message": f"Partner '{partner_name}' not found."
            }
        
        return {
            "partner": {
                "id": partner['id'],
                "name": partner['name'],
                "type": partner['type'],
                "sla_level": partner['sla_level'],
                "contract_status": partner['contract_status'],
                "contact_email": partner['contact_email'],
                "services": partner['services'],
                "revenue_share": partner['revenue_share'],
                "contract_start": partner['contract_start'],
                "contract_end": partner['contract_end'],
                "last_activity": partner['last_activity']
            }
        }
    
    async def _tool_get_contract_info(self, contract_id: Optional[str], user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Tool implementation for get_contract_info"""
        contracts = self.partners_data["contracts"]
        
        if contract_id:
            if contract_id in contracts:
                contract = contracts[contract_id]
                partner = self.partners_data["partners"][contract["partner_id"]]
                return {
                    "contract": {
                        **contract,
                        "partner_name": partner['name']
                    }
                }
            else:
                return {
                    "error": "contract_not_found",
                    "message": f"Contract '{contract_id}' not found."
                }
        else:
            contract_list = []
            for contract_id, contract in contracts.items():
                partner = self.partners_data["partners"][contract["partner_id"]]
                contract_list.append({
                    **contract,
                    "partner_name": partner['name']
                })
            
            return {
                "contracts": contract_list,
                "total_count": len(contract_list)
            }
    
    async def _tool_get_sla_info(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Tool implementation for get_sla_info"""
        partners = self.partners_data["partners"]
        
        sla_levels = {}
        for partner in partners.values():
            level = partner['sla_level']
            if level not in sla_levels:
                sla_levels[level] = []
            sla_levels[level].append(partner['name'])
        
        return {
            "sla_levels": {
                level: {
                    "partners": partner_names,
                    "count": len(partner_names)
                }
                for level, partner_names in sla_levels.items()
            },
            "sla_definitions": {
                "Premium": {
                    "uptime": "99.9%",
                    "support": "24/7 support",
                    "response_time": "<1hr response time"
                },
                "Standard": {
                    "uptime": "99.5%",
                    "support": "Business hours support",
                    "response_time": "<4hr response time"
                },
                "Basic": {
                    "uptime": "99.0%",
                    "support": "Business hours support",
                    "response_time": "<8hr response time"
                }
            }
        }
    
    async def _tool_get_revenue_info(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Tool implementation for get_revenue_info"""
        partners = self.partners_data["partners"]
        
        total_revenue_share = sum(partner['revenue_share'] for partner in partners.values())
        avg_revenue_share = total_revenue_share / len(partners) if partners else 0
        
        revenue_data = [
            {
                "partner_name": partner['name'],
                "revenue_share": partner['revenue_share']
            }
            for partner in partners.values()
        ]
        
        return {
            "revenue_data": revenue_data,
            "summary": {
                "total_partners": len(partners),
                "average_revenue_share": round(avg_revenue_share, 1),
                "total_revenue_share": round(total_revenue_share, 1)
            }
        }
