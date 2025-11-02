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
            
            # Check if this is a document-related query
            document_keywords = ["document", "documents", "file", "files", "project", "projects", 
                               "knowledge", "base", "search", "find", "look up", "reference"]
            
            is_document_query = any(keyword in message.lower() for keyword in document_keywords)
            
            # Prepare messages for OpenAI with system prompt and conversation history
            openai_messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            # Add conversation history from memory
            for msg in self.sessions[session_id]["conversation_history"]:
                openai_messages.append(msg)
            
            # If it's a document query, try to get context from RAG
            context = ""
            if is_document_query:
                try:
                    from rag.context_docs_tool import get_context_docs_fn
                    from langchain_core.runnables import RunnableConfig
                    
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
            
            return {
                "content": content,
                "agent_type": "Streamward Assistant with RAG",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "used_rag": bool(context and context != "No authorized documents found for this query.")
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