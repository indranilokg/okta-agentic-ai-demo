import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import re
import openai

logger = logging.getLogger(__name__)

class StreamwardAssistant:
    """
    Main Streamward Chat Assistant with memory management, context preservation, and RAG capabilities
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
        
        # System prompt for the assistant
        self.system_prompt = """
You are the Streamward AI Assistant, an intelligent enterprise assistant for Streamward Corporation.

Your capabilities include:
- Answering questions about Streamward's products and services
- Helping with general business inquiries
- Providing information about company policies and procedures
- Assisting with customer support queries
- Accessing authorized documents and knowledge base through RAG (Retrieval Augmented Generation)

You have access to the full conversation history and MUST use it to maintain context. 
If someone shares their name, preferences, or any information during the conversation, 
you should remember it and reference it in your responses.

When users ask about documents, projects, or anything stored in the knowledge base, 
you can use the get_context_docs tool to retrieve relevant information. This tool 
respects user permissions and only returns documents the user is authorized to access.

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
            rag_keywords_strong = ["document", "documents", "file", "files", "search", "find", 
                                   "look up", "reference", "what are", "what is", "tell me about",
                                   "show me", "information about", "knowledge base", "knowledge"]
            rag_keywords_weak = ["project", "projects", "policy", "policies", "compliance", "regulation"]
            
            # RAG is detected if:
            # - Strong RAG keywords present, OR
            # - Weak RAG keywords + query patterns (what/how/when/where)
            is_rag_query = (
                any(keyword in message_lower for keyword in rag_keywords_strong) or
                (any(keyword in message_lower for keyword in rag_keywords_weak) and 
                 any(pattern in message_lower for pattern in ["what", "how", "when", "where", "tell me", "show me"]))
            )
            
            # 2. A2A Workflow Detection - Action-oriented, not query-oriented
            # Only trigger for actual workflow actions, not document queries
            workflow_action_keywords = {
                "finance": ["process", "approve", "transaction", "payment", "invoice", "expense"],
                "hr": ["onboard", "onboarding", "hire", "hiring", "process employee"],
                "legal": ["review compliance", "verify compliance", "approve contract"]
            }
            
            # Workflow keywords that should NOT trigger if RAG is detected
            workflow_entity_keywords = {
                "finance": ["financial", "finance", "budget"],
                "hr": ["employee", "hr", "human resources", "staff", "benefits"],
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
            
            # 3. MCP Detection (for future)
            # Placeholder for MCP scenario detection
            is_mcp_scenario = False  # Will be implemented later
            
            # Log scenario detection
            if is_rag_query:
                detected_scenario = "RAG"
                logger.info(f"📚 Scenario detected: RAG (document query)")
            elif detected_workflow:
                detected_scenario = "A2A"
                logger.info(f"🔄 Scenario detected: A2A Workflow ({detected_workflow})")
            elif is_mcp_scenario:
                detected_scenario = "MCP"
                logger.info(f"🔌 Scenario detected: MCP (Model Context Protocol)")
            else:
                detected_scenario = "GENERAL"
                logger.info(f"💬 Scenario detected: General Chat")
            
            # Route to A2A orchestrator ONLY if:
            # - A2A workflow detected (not RAG)
            # - User has token for exchange
            if detected_scenario == "A2A" and detected_workflow and user_info.get("token"):
                logger.info(f"🎯 Workflow detected: {detected_workflow} for agent: {detected_agent}")
                logger.info(f"🔄 Routing to orchestrator with token exchange enabled")
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