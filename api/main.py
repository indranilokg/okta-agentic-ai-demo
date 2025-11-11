from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
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
# 
# Logging Strategy:
# - Root logger: INFO level (reduces noise while keeping important logs visible)
# - Suppress noisy third-party libraries (OpenAI, httpx, etc.) to WARNING
# - Keep token exchange and agent logs at INFO for clear visibility
# - This ensures token exchange flow is clearly visible without OpenAI DEBUG clutter
#
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# Suppress noisy third-party library logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)  # Suppress OpenAI DEBUG logs (e.g., "DEBUG:openai._base_client")
logging.getLogger("openai._base_client").setLevel(logging.WARNING)
logging.getLogger("langchain_openai").setLevel(logging.WARNING)  # Suppress LangChain OpenAI DEBUG logs
logging.getLogger("okta_ai_sdk").setLevel(logging.WARNING)  # Suppress Okta AI SDK verbose output (emojis in verification steps)
logging.getLogger("okta_ai_sdk.cross_app_access").setLevel(logging.WARNING)

# Keep important loggers at DEBUG level for full token visibility and flow details
# DEBUG logs will show full tokens (first 50 chars + full token for sensitive data)
logging.getLogger("auth.okta_auth").setLevel(logging.DEBUG)  # Token exchange with full tokens
logging.getLogger("auth.okta_validator").setLevel(logging.DEBUG)  # Token validation with full tokens
logging.getLogger("auth.okta_cross_app_access").setLevel(logging.DEBUG)  # ID-JAG exchange with full tokens
logging.getLogger("orchestrator_agent").setLevel(logging.DEBUG)  # Orchestrator workflow logs
logging.getLogger("a2a_agents").setLevel(logging.DEBUG)  # Agent processing logs
logging.getLogger("chat_assistant").setLevel(logging.DEBUG)  # Chat assistant with full MCP tokens
logging.getLogger("api.main").setLevel(logging.DEBUG)  # API endpoint logs
logging.getLogger("mcp_servers").setLevel(logging.DEBUG)  # MCP server logs

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
    id_token: Optional[str] = None  # For ID-JAG token exchange
    access_token: Optional[str] = None  # For resource access

class ChatMessageList(BaseModel):
    messages: List[Dict[str, Any]]
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    agent_type: str
    timestamp: datetime
    session_id: str

class RAGInfo(BaseModel):
    query: Optional[str] = None
    documents_count: Optional[int] = 0
    context_preview: Optional[str] = None

class AgentFlowStep(BaseModel):
    agent: str
    step: int
    timestamp: str
    token_exchange: Dict[str, Any]

class TokenExchangeInfo(BaseModel):
    from_: str = Field(alias="from")
    to: str
    audience: str
    scope: str
    token: str

    class Config:
        populate_by_name = True

class SimpleChatResponse(BaseModel):
    content: str
    agentType: str
    used_rag: Optional[bool] = None
    rag_info: Optional[RAGInfo] = None
    workflow_info: Optional[Dict[str, Any]] = None
    agent_flow: Optional[List[Dict[str, Any]]] = None
    token_exchanges: Optional[List[Dict[str, Any]]] = None
    source_user_token: Optional[str] = None  # Original user token that initiated the workflow
    mcp_info: Optional[Dict[str, Any]] = None  # MCP server info and tools called

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

@app.get("/api/config/okta")
async def get_okta_config():
    """Return Okta configuration needed for frontend custom server OAuth flow (A2A)"""
    return {
        "mainServerId": os.getenv("OKTA_MAIN_SERVER_ID", "default"),
        "oktaDomain": os.getenv("OKTA_DOMAIN"),
        "audience": os.getenv("OKTA_MAIN_AUDIENCE", "api://streamward-chat")
    }

@app.post("/api/chat", response_model=SimpleChatResponse)
async def chat_endpoint(request: ChatMessageList, http_request: Request, current_user: Optional[dict] = Depends(get_current_user_optional)):
    """Main chat endpoint that routes messages to appropriate agents"""
    try:
        # Get the last message from the conversation
        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")
        
        last_message = request.messages[-1]
        user_message = last_message.get('content', '')
        
        # Get session ID from request or use default
        session_id = request.session_id or 'test-session'
        
        logger.debug(f"[API] Chat: msg={user_message[:50]}..., session={session_id}")
        
        # Extract tokens from headers
        # Support both header formats and body parameters for flexibility
        custom_id_token = http_request.headers.get('X-ID-Token') or last_message.get('id_token')
        custom_access_token = http_request.headers.get('X-Custom-Access-Token') or http_request.headers.get('X-Access-Token') or last_message.get('access_token')
        
        # Log token availability from each source
        logger.info(f"[API] Token sources - X-ID-Token: {bool(http_request.headers.get('X-ID-Token'))}, X-Custom-Access-Token: {bool(http_request.headers.get('X-Custom-Access-Token'))}, X-Access-Token: {bool(http_request.headers.get('X-Access-Token'))}")
        logger.debug(f"[API] Tokens: has_id_token={bool(custom_id_token)}, has_access_token={bool(custom_access_token)}")
        
        # Log full tokens at DEBUG level for troubleshooting
        if custom_id_token:
            logger.debug(f"[API] ID Token (first 50): {custom_id_token[:50]}...")
            logger.debug(f"[API] Full ID Token: {custom_id_token}")
        if custom_access_token:
            logger.debug(f"[API] Access Token (first 50): {custom_access_token[:50]}...")
            logger.debug(f"[API] Full Access Token: {custom_access_token}")
        
        # Build user_info - prioritize in this order:
        # 1. User from Authorization header (if provided)
        # 2. User from custom access token (validate and extract user info)
        # 3. Demo user (fallback)
        user_info = None
        
        if current_user:
            # User authenticated via Authorization header
            logger.debug(f"[API] User: authenticated via header={current_user.get('email')}")
            user_info = current_user.copy()
        elif custom_access_token:
            # Validate custom access token and extract user info
            try:
                from auth.okta_validator import token_validator
                validated_user = await token_validator.validate_token(custom_access_token)
                if validated_user:
                    logger.debug(f"[API] User: validated from token={validated_user.get('email')}")
                    user_info = validated_user
                else:
                    logger.warning("[API] Custom access token validation failed")
            except Exception as e:
                logger.warning(f"[API] Token validation error: {str(e)}")
        elif custom_id_token:
            # Also validate ID token to extract user info for RAG access
            try:
                from auth.okta_validator import token_validator
                validated_user = await token_validator.validate_token(custom_id_token)
                if validated_user:
                    logger.debug(f"[API] User: validated from ID token={validated_user.get('email')}")
                    user_info = validated_user
                else:
                    logger.warning("[API] ID token validation failed")
            except Exception as e:
                logger.warning(f"[API] ID token validation error: {str(e)}")
        
        if not user_info:
            # Fallback to demo user
            logger.debug("[API] Using demo user")
            user_info = {
                "sub": "demo-user",
                "email": "demo@streamward.com",
                "name": "Demo User"
            }
        
        # Add tokens to user_info
        if custom_id_token:
            user_info["id_token"] = custom_id_token
        
        # For A2A workflows: requires valid access token
        if custom_access_token:
            user_info["token"] = custom_access_token
        
        logger.info(f"[API] User_session: email={user_info['email']}, has_id_token={bool(custom_id_token)}, has_access_token={bool(custom_access_token)}")
        logger.debug(f"[API] User_info keys: {list(user_info.keys())}")
        
        # Process message through Streamward Assistant (with memory management)
        response = await streamward_assistant.process_message(
            user_message,
            user_info,
            session_id
        )
        
        response_data = SimpleChatResponse(
            content=response["content"],
            agentType=response["agent_type"],
            used_rag=response.get("used_rag", False),
            rag_info=RAGInfo(**response.get("rag_info", {})) if response.get("rag_info") else None,
            workflow_info=response.get("workflow_info"),
            agent_flow=response.get("agent_flow"),
            token_exchanges=response.get("token_exchanges"),
            source_user_token=response.get("source_user_token"),
            mcp_info=response.get("mcp_info")
        )
        
        # Log response details
        logger.debug(f"[API] Response: agent_type={response['agent_type']}, has_agent_flow={bool(response_data.agent_flow)}, has_token_exchanges={bool(response_data.token_exchanges)}, has_mcp_info={bool(response_data.mcp_info)}, used_rag={response_data.used_rag}")
        
        return response_data
        
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
