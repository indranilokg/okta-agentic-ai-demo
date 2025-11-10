import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import re
import openai

from auth.okta_cross_app_access import OktaCrossAppAccessManager

logger = logging.getLogger(__name__)

class StreamwardAssistant:
    """
    Main Streamward Chat Assistant with ID-JAG Cross-App Access Integration
    
    Features:
    - Memory management with session persistence
    - Context preservation across conversations
    - RAG (Retrieval Augmented Generation) capabilities
    - OpenAI function calling for tool integration
    - **NEW**: ID-JAG cross-app access for secure MCP server communication
    
    ID-JAG Flow for MCP Access:
    - STEP 1-3: Exchange user ID token → ID-JAG token → MCP access token (in Chat Assistant)
    - STEP 4: MCP Server validates MCP access token before granting tool access
    - Result: Secure cross-app authentication without sharing credentials
    """
    
    def __init__(self):
        # Get OpenAI API key from environment
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = openai.OpenAI(api_key=openai_api_key)
        self.model = "gpt-3.5-turbo"
        
        # Session management with memory
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        # Initialize ID-JAG cross-app access manager for MCP token exchange
        try:
            self.cross_app_access_manager = OktaCrossAppAccessManager()
            logger.info("✅ Chat Assistant initialized with ID-JAG cross-app access support")
        except Exception as e:
            logger.warning(f"⚠️ Chat Assistant: ID-JAG support not available: {e}")
            self.cross_app_access_manager = None
        
        # Initialize MCP servers
        try:
            from mcp_servers.employees_mcp import EmployeesMCP
            from mcp_servers.partners_mcp import PartnersMCP
            self.employees_mcp = EmployeesMCP()
            self.partners_mcp = PartnersMCP()
            logger.info("[CHAT_INIT] MCP servers initialized: EmployeesMCP and PartnersMCP")
        except Exception as e:
            logger.warning(f"[CHAT_INIT] MCP server warning: {e}")
            self.employees_mcp = None
            self.partners_mcp = None
        
        # System prompt for the assistant
        self.system_prompt = """
You are the Streamward AI Assistant, an intelligent enterprise assistant for Streamward Corporation.

Your capabilities include:
- Answering questions about Streamward's products and services
- Helping with general business inquiries
- Providing information about company policies and procedures
- Assisting with customer support queries
- Accessing authorized documents and knowledge base through RAG (Retrieval Augmented Generation)
- Querying employee information through MCP tools (employees, departments, benefits, onboarding)
- Querying partner information through MCP tools (partners, contracts, SLA, revenue)

You have access to the full conversation history and MUST use it to maintain context. 
If someone shares their name, preferences, or any information during the conversation, 
you should remember it and reference it in your responses.

When users ask about documents, projects, or anything stored in the knowledge base, 
you can use the get_context_docs tool to retrieve relevant information. This tool 
respects user permissions and only returns documents the user is authorized to access.

When users ask about employees, departments, benefits, or HR-related topics, the system
will automatically route to employee MCP tools. When users ask about partners, contracts,
or vendor information, the system will route to partner MCP tools.

Be helpful, professional, and conversational while maintaining enterprise-grade security awareness.
"""
    
    async def process_message(self, message: str, user_info: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Process a user message with full context preservation and RAG capabilities
        """
        try:
            logger.info(f"Processing message for session {session_id}: {message[:100]}...")
            
            # Initialize session if needed
            if session_id not in self.sessions:
                self.sessions[session_id] = {
                    "conversation_history": [],
                    "created_at": datetime.now(),
                    "message_count": 0,
                    "user_info": user_info
                }
            
            self.sessions[session_id]["message_count"] += 1
            
            # SCENARIO DETECTION WITH CLEAR PRIORITIES
            # Priority order: RAG > A2A Workflow > MCP > General Chat
            
            message_lower = message.lower()
            detected_scenario = None
            
            # 1. RAG Detection - Strong indicators for document queries
            # Document/knowledge base specific keywords
            rag_keywords_strong = ["document", "documents", "file", "files", "documentation", 
                                   "knowledge base", "knowledge", "policy", "policies", "compliance", 
                                   "regulation", "standard", "procedure", "guideline"]
            
            # Query patterns that indicate looking for information in documents
            rag_query_patterns = ["search for", "find information", "look up", "tell me about the",
                                 "what are the", "what is the", "information about the", "documents about",
                                 "information about compliance", "information about security", 
                                 "information about policy", "information about regulation"]
            
            # RAG is detected if:
            # - Has document/knowledge keywords, AND
            # - Has RAG-specific query patterns (search, find, about the, what are the, etc.)
            is_rag_query = (
                any(keyword in message_lower for keyword in rag_keywords_strong) and 
                any(pattern in message_lower for pattern in rag_query_patterns)
            )
            
            # 2. A2A Workflow Detection - Action-oriented, not query-oriented
            # Only trigger for actual workflow ACTIONS (process, approve, submit), NOT queries (list, show, tell)
            workflow_action_keywords = {
                "finance": ["process payment", "approve payment", "process transaction", "approve transaction", 
                           "submit invoice", "process invoice", "approve expense", "process expense"],
                "hr": ["onboard employee", "hire employee", "process hire", "submit hire", "process onboard"],
                "legal": ["review contract", "approve contract", "verify compliance", "review compliance"]
            }
            
            # Workflow entity keywords - only match with explicit action verbs
            # These should NOT be used for queries (list, show, tell, query, info, details, etc.)
            workflow_entity_keywords = {
                "finance": ["financial", "finance", "budget"],
                "hr": ["staff", "hr", "human resources"],  # Removed: employee, benefits (too query-focused)
                "legal": ["legal", "compliance", "contract", "regulatory", "law", "attorney"]
            }
            
            detected_workflow = None
            detected_agent = None
            
            # Only detect A2A workflow if:
            # - NOT a RAG query (clear boundary)
            # - Contains action keywords (process, approve, onboard, etc.), OR
            # - Contains entity keywords + action verbs (e.g., "process financial transaction")
            if not is_rag_query:
                # Check for explicit action-oriented workflows
                for agent, action_keywords in workflow_action_keywords.items():
                    if any(keyword in message_lower for keyword in action_keywords):
                        detected_agent = agent
                        if agent == "finance":
                            detected_workflow = "financial_transaction"
                        elif agent == "hr":
                            detected_workflow = "employee_onboarding"
                        elif agent == "legal":
                            detected_workflow = "compliance_review"
                        break
                
                # If no action detected, check for entity + action verb patterns
                if not detected_workflow:
                    action_verbs = ["need to", "help me", "can you", "process", "approve", "handle", "manage"]
                    has_action_verb = any(verb in message_lower for verb in action_verbs)
                    
                    if has_action_verb:
                        for agent, entity_keywords in workflow_entity_keywords.items():
                            if any(keyword in message_lower for keyword in entity_keywords):
                                detected_agent = agent
                                if agent == "finance":
                                    detected_workflow = "financial_transaction"
                                elif agent == "hr":
                                    detected_workflow = "employee_onboarding"
                                elif agent == "legal":
                                    detected_workflow = "compliance_review"
                                break
            
            # 3. MCP Detection - Employee or Partner queries
            # ONLY trigger for QUERY-ORIENTED prompts (list, show, get, tell, what, information, details)
            # NOT for action-oriented (process, approve, onboard - those are A2A workflows)
            is_mcp_scenario = False
            mcp_server = None
            mcp_tool = None
            
            # Query verbs that indicate MCP queries (list, show, get, tell, information, etc.)
            query_verbs = ["list", "show", "get", "tell", "what", "information", "details", 
                          "query", "search", "find", "retrieve", "show me", "tell me",
                          "are the", "do we", "how many", "which", "who"]
            
            # Employee-related keywords (for MCP queries)
            employee_keywords = ["employee", "employees", "staff", "team member", "colleague", 
                               "department", "departments", "benefits", "salary", "compensation", "salary band"]
            
            # Partner-related keywords (for MCP queries)
            partner_keywords = ["partner", "partners", "vendor", "vendors", "sla", 
                              "service level", "revenue share", "partnership"]
            
            # MCP-specific query patterns (e.g., asking about specific entities by name)
            # These patterns indicate person/company info queries (employee or partner)
            mcp_info_patterns = ["information about", "info about", "tell me about", "show me"]
            
            # Check if message is about employees or partners (but not RAG or A2A workflow)
            # AND contains a query verb OR MCP info pattern
            has_query_verb = any(verb in message_lower for verb in query_verbs)
            has_info_pattern = any(pattern in message_lower for pattern in mcp_info_patterns)
            
            if not is_rag_query and not detected_workflow and (has_query_verb or has_info_pattern):
                has_employee_keywords = any(keyword in message_lower for keyword in employee_keywords)
                has_partner_keywords = any(keyword in message_lower for keyword in partner_keywords)
                
                # Route to MCP Employees if:
                # - Has employee keywords, OR
                # - Has info pattern + looks like a person query (e.g., "show me information about John Smith")
                if (has_employee_keywords or (has_info_pattern and not has_partner_keywords)) and self.employees_mcp:
                    is_mcp_scenario = True
                    mcp_server = "employees"
                    logger.debug(f"[CHAT] MCP: employee_query=True")
                elif has_partner_keywords and self.partners_mcp:
                    is_mcp_scenario = True
                    mcp_server = "partners"
                    logger.debug(f"[CHAT] MCP: partner_query=True")
            
            # Log scenario detection
            if is_rag_query:
                detected_scenario = "RAG"
                logger.debug(f"[CHAT] Scenario: RAG")
            elif detected_workflow:
                detected_scenario = "A2A"
                logger.debug(f"[CHAT] Scenario: A2A_workflow={detected_workflow}")
            elif is_mcp_scenario:
                detected_scenario = "MCP"
                logger.debug(f"[CHAT] Scenario: MCP_server={mcp_server}")
            else:
                detected_scenario = "GENERAL"
                logger.debug(f"[CHAT] Scenario: GENERAL_CHAT")
            
            # Route to MCP tools if MCP scenario detected
            if detected_scenario == "MCP" and mcp_server:
                logger.debug(f"[CHAT] Routing to MCP: {mcp_server}")
                try:
                    mcp_result = await self._handle_mcp_query(
                        message, 
                        mcp_server, 
                        user_info, 
                        session_id
                    )
                    
                    # Update conversation history
                    self.sessions[session_id]["conversation_history"].append({"role": "user", "content": message})
                    self.sessions[session_id]["conversation_history"].append({
                        "role": "assistant", 
                        "content": mcp_result.get("content", "MCP query processed")
                    })
                    
                    return mcp_result
                except Exception as e:
                    logger.error(f"[CHAT] MCP_query_failed: {str(e)}", exc_info=True)
                    # Fall through to normal chat processing
            
            # Route to A2A orchestrator ONLY if:
            # - A2A workflow detected (not RAG, not MCP)
            # - User has token for exchange
            if detected_scenario == "A2A" and detected_workflow and user_info.get("token"):
                logger.debug(f"[CHAT] Routing to orchestrator: workflow={detected_workflow}, agent={detected_agent}")
                try:
                    from orchestrator_agent.orchestrator import OrchestratorAgent
                    orchestrator = OrchestratorAgent()
                    
                    # Extract parameters from message (simplified - could use LLM for better extraction)
                    # Security: Only include email, not sub (internal ID)
                    parameters = {
                        "message": message,
                        "user_email": user_info.get("email")
                        # Removed user_sub - internal ID not needed
                    }
                    
                    logger.info(f"🚀 Executing orchestrator workflow: {detected_workflow}")
                    logger.info(f"📋 Parameters: {parameters}")
                    logger.info(f"🔐 User has token for exchange: {bool(user_info.get('token'))}")
                    
                    workflow_result = await orchestrator.execute_workflow(
                        workflow_type=detected_workflow,
                        parameters=parameters,
                        user_info=user_info
                    )
                    
                    logger.info(f"✅ Orchestrator workflow completed: {workflow_result.get('status')}")
                    
                    # Update conversation history
                    self.sessions[session_id]["conversation_history"].append({"role": "user", "content": message})
                    self.sessions[session_id]["conversation_history"].append({
                        "role": "assistant", 
                        "content": workflow_result.get("response", "Workflow completed successfully")
                    })
                    
                    return {
                        "content": workflow_result.get("response", "Workflow completed successfully"),
                        "agent_type": f"Orchestrator ({detected_agent.capitalize()} Agent)",
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat(),
                        "used_rag": False,
                        "workflow_info": {
                            "workflow_type": detected_workflow,
                            "agent": detected_agent,
                            "status": workflow_result.get("status")
                        },
                        "agent_flow": workflow_result.get("agent_flow", []),  # Agent routing flow
                        "token_exchanges": workflow_result.get("token_exchanges", []),  # Token exchange details
                        "source_user_token": workflow_result.get("source_user_token")  # Original user token
                    }
                except Exception as e:
                    logger.error(f"❌ Orchestrator workflow failed: {e}")
                    import traceback
                    logger.debug(f"Orchestrator error traceback: {traceback.format_exc()}")
                    # Fall through to normal chat processing
            
            # Prepare messages for OpenAI with system prompt and conversation history
            openai_messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            # Add conversation history from memory
            for msg in self.sessions[session_id]["conversation_history"]:
                openai_messages.append(msg)
            
            # If RAG scenario detected, try to get context from documents
            context = ""
            rag_query = ""
            rag_documents_count = 0
            rag_context_preview = ""
            if detected_scenario == "RAG":
                try:
                    from rag.context_docs_tool import get_context_docs_fn
                    from langchain_core.runnables import RunnableConfig
                    
                    # Store the query for RAG tracking
                    rag_query = message
                    
                    # Create config with user credentials
                    config = RunnableConfig(
                        configurable={
                            "_credentials": {
                                "user": user_info
                            }
                        }
                    )
                    
                    # Get context from documents
                    context = await get_context_docs_fn(message, config)
                    
                    if context and context != "No authorized documents found for this query.":
                        # Add context to the system message
                        context_message = f"\n\nRelevant information from authorized documents:\n{context}"
                        openai_messages[0]["content"] += context_message
                        logger.info(f"✅ Added RAG context: {len(context)} characters")
                        
                        # Get actual document count from the retriever
                        try:
                            from rag.context_docs_tool import document_retriever
                            # Count documents - they are separated by \n\n
                            # We need to check the actual number returned by search
                            temp_docs = await document_retriever.search_documents(message, user_info.get("email", ""))
                            rag_documents_count = len(temp_docs) if temp_docs else 0
                        except:
                            # Fallback: estimate based on separator
                            rag_documents_count = context.count("\n\n") + 1 if context else 0
                        
                        # Create preview (first 300 characters)
                        rag_context_preview = context[:300] + "..." if len(context) > 300 else context
                    
                except Exception as e:
                    logger.error(f"RAG context retrieval failed: {e}")
                    # Continue without context
            
            # Add current user message
            openai_messages.append({"role": "user", "content": message})
            
            logger.info(f"Total messages sent to OpenAI: {len(openai_messages)}")
            
            # Call OpenAI API with full conversation context
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=openai_messages,
                    max_tokens=1000,
                    temperature=0.7
                )
            )
            
            content = response.choices[0].message.content
            
            # Update conversation history in memory
            self.sessions[session_id]["conversation_history"].append({"role": "user", "content": message})
            self.sessions[session_id]["conversation_history"].append({"role": "assistant", "content": content})
            
            # Keep only last 20 messages to prevent memory overflow
            if len(self.sessions[session_id]["conversation_history"]) > 20:
                self.sessions[session_id]["conversation_history"] = self.sessions[session_id]["conversation_history"][-20:]
            
            used_rag = bool(context and context != "No authorized documents found for this query.")
            
            return {
                "content": content,
                "agent_type": "Streamward Assistant with RAG",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "used_rag": used_rag,
                "rag_info": {
                    "query": rag_query if used_rag else None,
                    "documents_count": rag_documents_count if used_rag else 0,
                    "context_preview": rag_context_preview if used_rag else None
                } if used_rag else None
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "content": f"I apologize, but I encountered an error processing your message: {str(e)}",
                "agent_type": "Error Handler",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "used_rag": False
            }
    
    async def _exchange_id_token_for_mcp_access(self, id_token: str, mcp_server: str, user_info: Dict[str, Any]) -> Optional[str]:
        """
        STEPS 1-3 of ID-JAG Flow: Exchange ID token for MCP access token
        
        Args:
            id_token: User's ID token from authentication
            mcp_server: Target MCP server ("employees" or "partners")
            user_info: User context info
            
        Returns:
            MCP access token if successful, None otherwise
        """
        try:
            if not self.cross_app_access_manager:
                logger.error("❌ MCP SDK not configured. ID-JAG exchange not available.")
                return None
            
            if not id_token:
                logger.error("[MCP] No ID token provided. Cannot exchange for MCP token.")
                return None
            
            logger.debug(f"[MCP] Exchanging ID token for MCP token ({mcp_server})")
            
            # Perform the 4-step ID-JAG exchange
            mcp_token_response = await self.cross_app_access_manager.exchange_id_to_mcp_token(id_token)
            
            if mcp_token_response:
                # Extract the actual token string from the response dict
                mcp_access_token = mcp_token_response.get("access_token")
                if mcp_access_token:
                    logger.info(f"[MCP] Token exchange SUCCESS: server={mcp_server}, expires_in={mcp_token_response.get('expires_in')}s")
                    logger.debug(f"[MCP] MCP token (first 50): {mcp_access_token[:50]}...")
                    logger.debug(f"[MCP] Full MCP token: {mcp_access_token}")
                    # Return full response with both ID-JAG token and access token for frontend display
                    return {
                        "access_token": mcp_access_token,
                        "id_jag_token": mcp_token_response.get("id_jag_token"),  # Captured from exchange
                        "expires_in": mcp_token_response.get("expires_in"),
                        "scope": mcp_token_response.get("scope")
                    }
                else:
                    logger.error(f"[MCP] No access token in exchange response")
                    return None
            else:
                logger.error(f"[MCP] Token exchange FAILED for server={mcp_server}")
                return None
                
        except Exception as e:
            logger.error(f"[MCP] Token exchange error: {str(e)}", exc_info=True)
            return None
    
    async def _handle_mcp_query(self, message: str, mcp_server: str, user_info: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Handle MCP query by using OpenAI function calling to determine and execute the right tool.
        
        Flow:
        1. Exchange ID token for MCP access token (ID-JAG)
        2. Determine which MCP tool to call using OpenAI function calling
        3. Call MCP tool with MCP access token for authorization
        4. MCP server validates token before executing tool
        """
        try:
            # STEP 1-3: Exchange ID token for MCP access token
            # ID token should be provided by the frontend in user_info
            id_token = user_info.get("id_token")
            if not id_token:
                logger.error("[MCP] No ID token in user_info. Cannot perform ID-JAG exchange.")
            
            mcp_token_info = await self._exchange_id_token_for_mcp_access(id_token, mcp_server, user_info)
            
            # Extract token and store token info for frontend display
            mcp_access_token = None
            mcp_tokens_info = {}
            if mcp_token_info:
                if isinstance(mcp_token_info, dict):
                    mcp_access_token = mcp_token_info.get("access_token")
                    # Capture tokens and metadata for display
                    mcp_tokens_info = {
                        "id_jag_token": mcp_token_info.get("id_jag_token"),
                        "mcp_access_token": mcp_access_token,
                        "expires_in": mcp_token_info.get("expires_in"),
                        "scope": mcp_token_info.get("scope")
                    }
                    logger.debug(f"[MCP] Captured tokens: id_jag={bool(mcp_tokens_info.get('id_jag_token'))}, access={bool(mcp_tokens_info.get('mcp_access_token'))}, expires_in={mcp_tokens_info.get('expires_in')}s, scope={mcp_tokens_info.get('scope')}")
                else:
                    # Backward compatibility: if it's just a string token
                    mcp_access_token = mcp_token_info
            
            # Add MCP token to user_info for tool execution
            if mcp_access_token:
                user_info["mcp_token"] = mcp_access_token
                user_info["mcp_tokens_info"] = mcp_tokens_info
                logger.debug(f"[MCP] Token added to user_info for {mcp_server}")
            else:
                logger.warning(f"[MCP] No MCP token available. MCP tools will reject access requests.")
            
            # Get the appropriate MCP server
            if mcp_server == "employees":
                mcp = self.employees_mcp
            elif mcp_server == "partners":
                mcp = self.partners_mcp
            else:
                return {
                    "content": "Unknown MCP server",
                    "agent_type": "MCP",
                    "error": "unknown_server"
                }
            
            if not mcp:
                return {
                    "content": "MCP server not available",
                    "agent_type": "MCP",
                    "error": "server_not_available"
                }
            
            # Get available tools from MCP server
            available_tools = mcp.list_tools()
            
            # Convert MCP tools to OpenAI function format
            openai_functions = []
            for tool in available_tools:
                openai_functions.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["parameters"]
                    }
                })
            
            # Prepare messages for OpenAI with function calling
            conversation_history = self.sessions.get(session_id, {}).get("conversation_history", [])
            openai_messages = [
                {"role": "system", "content": f"You are a helpful assistant that uses MCP tools to answer questions about {mcp_server}. Always use the appropriate tool to answer user questions."}
            ]
            
            # Add conversation history (last 5 messages for context)
            for msg in conversation_history[-5:]:
                openai_messages.append(msg)
            
            # Add current message
            openai_messages.append({"role": "user", "content": message})
            
            # Call OpenAI with function calling
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model="gpt-4",  # Use GPT-4 for better function calling
                    messages=openai_messages,
                    tools=openai_functions if openai_functions else None,
                    tool_choice="auto",
                    max_tokens=1000,
                    temperature=0.3
                )
            )
            
            message_response = response.choices[0].message
            
            # Check if OpenAI wants to call a tool
            if message_response.tool_calls:
                tool_calls = message_response.tool_calls
                tool_results = []
                
                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    logger.debug(f"[MCP] Calling tool: {tool_name}")
                    
                    # Call the MCP tool
                    tool_result = await mcp.call_tool(tool_name, tool_args, user_info)
                    
                    # Check for errors
                    if "error" in tool_result:
                        tool_results.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": tool_name,
                            "content": json.dumps({
                                "error": tool_result["error"],
                                "message": tool_result.get("message", "Tool execution failed")
                            })
                        })
                    else:
                        tool_results.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": tool_name,
                            "content": json.dumps(tool_result, indent=2)
                        })
                
                # Add tool results to messages and get final response
                openai_messages.append(message_response)
                openai_messages.extend(tool_results)
                
                # Get final response from OpenAI
                final_response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(
                        model="gpt-4",
                        messages=openai_messages,
                        max_tokens=1000,
                        temperature=0.3
                    )
                )
                
                content = final_response.choices[0].message.content
                
                logger.debug(f"[MCP] Response built: tools_called={[tc.function.name for tc in tool_calls]}")
                
                return {
                    "content": content,
                    "agent_type": f"MCP ({mcp_server.capitalize()})",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "used_rag": False,
                    "mcp_info": {
                        "server": mcp_server,
                        "tools_called": [tc.function.name for tc in tool_calls],
                        **mcp_tokens_info  # Include ID-JAG and access tokens for frontend display
                    }
                }
            else:
                # No tool calls, return direct response
                content = message_response.content
                
                return {
                    "content": content,
                    "agent_type": f"MCP ({mcp_server.capitalize()})",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "used_rag": False,
                    "mcp_info": {
                        "server": mcp_server,
                        "tools_called": [],
                        **mcp_tokens_info  # Include ID-JAG and access tokens for frontend display
                    }
                }
                
        except Exception as e:
            logger.error(f"[MCP] Query_failed: {str(e)}", exc_info=True)
            return {
                "content": f"I encountered an error processing your {mcp_server} query. Please try again.",
                "agent_type": f"MCP ({mcp_server.capitalize()})",
                "error": str(e)
            }
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a session"""
        return self.sessions.get(session_id)
    
    def clear_session(self, session_id: str) -> bool:
        """Clear a session's memory"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def get_all_sessions(self) -> Dict[str, Any]:
        """Get information about all active sessions"""
        return {
            "active_sessions": len(self.sessions),
            "sessions": {
                sid: {
                    "message_count": data["message_count"],
                    "created_at": data["created_at"].isoformat(),
                    "conversation_length": len(data["conversation_history"])
                }
                for sid, data in self.sessions.items()
            }
        }