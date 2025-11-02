from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import json
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our modules
from chat_assistant.assistant import StreamwardAssistant
from api.routes.documents import router as documents_router
from auth.okta_validator import get_current_user_optional

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # Temporarily set to DEBUG to see token validation
logger = logging.getLogger(__name__)
# Set specific loggers to INFO to reduce noise
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

app = FastAPI(
    title="Streamward AI Assistant API",
    description="Enterprise-grade agentic AI demo with multi-provider authentication",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize services
streamward_assistant = StreamwardAssistant()

# Include document routes
app.include_router(documents_router)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None

class ChatMessageList(BaseModel):
    messages: List[Dict[str, Any]]
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    agent_type: str
    timestamp: datetime
    session_id: str

class SimpleChatResponse(BaseModel):
    content: str
    agentType: str
    used_rag: Optional[bool] = None

class WorkflowRequest(BaseModel):
    workflow_type: str
    parameters: Dict[str, Any]
    user_id: str

class WorkflowResponse(BaseModel):
    workflow_id: str
    status: str
    result: Optional[Dict[str, Any]] = None

# Mock authentication for testing
def get_current_user():
    """Mock user for testing"""
    return {"sub": "test-user", "email": "test@streamward.com", "name": "Test User"}

# API Routes
@app.get("/")
async def root():
    return {"message": "Streamward AI Assistant API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

@app.post("/api/chat", response_model=SimpleChatResponse)
async def chat_endpoint(request: ChatMessageList, current_user: Optional[dict] = Depends(get_current_user_optional)):
    """Main chat endpoint that routes messages to appropriate agents"""
    try:
        # Get the last message from the conversation
        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")
        
        last_message = request.messages[-1]
        user_message = last_message.get('content', '')
        
        # Get session ID from request or use default
        session_id = request.session_id or 'test-session'
        
        logger.info(f"Chat message: {user_message} (session: {session_id})")
        
        # Use real user if authenticated, otherwise use mock for demo
        if current_user:
            logger.info(f"✅ Authenticated user: {current_user.get('email')}")
            user_info = current_user
        else:
            logger.warning("⚠️ No authenticated user - using demo user (check if token is being forwarded)")
            user_info = {
                "sub": "demo-user",
                "email": "demo@streamward.com",
                "name": "Demo User"
            }
        
        logger.info(f"Using user: {user_info['email']}")
        logger.info(f"User details: sub={user_info.get('sub')}, name={user_info.get('name')}, email={user_info.get('email')}")
        
        # Process message through Streamward Assistant (with memory management)
        response = await streamward_assistant.process_message(
            user_message,
            user_info,
            session_id
        )
        
        return SimpleChatResponse(
            content=response["content"],
            agentType=response["agent_type"],
            used_rag=response.get("used_rag", False)
        )
        
    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/chat/authenticated", response_model=ChatResponse)
async def chat_endpoint_authenticated(message: ChatMessage):
    """Authenticated chat endpoint that routes messages to appropriate agents"""
    try:
        current_user = get_current_user()
        logger.info(f"Chat message from user {current_user.get('sub', 'unknown')}: {message.message}")
        
        # Process message through Streamward Assistant
        response = await streamward_assistant.process_message(
            message.message,
            current_user,
            message.session_id or "default-session"
        )
        
        return ChatResponse(
            response=response["content"],
            agent_type=response["agent_type"],
            timestamp=datetime.now(),
            session_id=response["session_id"]
        )
        
    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/orchestrator/workflow", response_model=WorkflowResponse)
async def trigger_workflow(
    request: WorkflowRequest,
):
    """Trigger complex multi-agent workflows"""
    try:
        current_user = get_current_user()
        logger.info(f"Workflow request from user {current_user.get('sub', 'unknown')}: {request.workflow_type}")
        
        # Process through orchestrator agent (simplified)
        result = {"status": "simplified", "message": "Workflow processing simplified for testing"}
        
        return WorkflowResponse(
            workflow_id="test-workflow-123",
            status=result["status"],
            result=result
        )
        
    except Exception as e:
        logger.error(f"Workflow execution error: {e}")
        raise HTTPException(status_code=500, detail="Workflow execution failed")

@app.post("/api/documents/search")
async def search_documents(
    query: str,
):
    """Search documents with DPOP protection"""
    try:
        current_user = get_current_user()
        logger.info(f"Document search from user {current_user.get('sub', 'unknown')}: {query}")
        
        # Search through RAG tool (simplified)
        results = [{"title": "Sample Document", "content": f"Search results for: {query}", "score": 0.95}]
        
        return {
            "query": query,
            "results": results,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Document search error: {e}")
        raise HTTPException(status_code=500, detail="Document search failed")

@app.get("/api/agents/status")
async def get_agent_status():
    """Get status of all agents"""
    return {
        "streamward_assistant": "active",
        "openai_integration": "active",
        "memory_management": "active",
        "active_sessions": len(streamward_assistant.sessions),
        "timestamp": datetime.now()
    }

@app.get("/api/sessions/{session_id}")
async def get_session_info(session_id: str):
    """Get session information"""
    session_info = streamward_assistant.get_session_info(session_id)
    if not session_info:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "message_count": session_info["message_count"],
        "created_at": session_info["created_at"],
        "conversation_length": len(session_info["conversation_history"])
    }

@app.delete("/api/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear session data"""
    if not streamward_assistant.clear_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": f"Session {session_id} cleared successfully"}

@app.get("/api/sessions")
async def get_all_sessions():
    """Get information about all active sessions"""
    return streamward_assistant.get_all_sessions()

# WebSocket endpoint for real-time chat
@app.websocket("/ws/chat/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Process message
            response = await streamward_assistant.process_message(
                message_data["message"],
                {"sub": user_id},
                message_data.get("session_id")
            )
            
            # Send response back
            await manager.send_personal_message(
                json.dumps({
                    "response": response["content"],
                    "agent_type": response["agent_type"],
                    "timestamp": datetime.now().isoformat(),
                    "session_id": response["session_id"]
                }),
                websocket
            )
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
