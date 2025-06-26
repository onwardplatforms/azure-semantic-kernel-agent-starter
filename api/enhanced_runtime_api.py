#!/usr/bin/env python3

"""Enhanced Runtime API with database persistence and session management."""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Header, Cookie, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import get_settings
from database import get_db, init_db
from database.session import create_session, get_session
from runtime.enhanced_agent_runtime import EnhancedAgentRuntime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("enhanced_runtime_api")

settings = get_settings()

app = FastAPI(
    title="Enhanced Agent Runtime API",
    description="Agent Runtime API with database persistence and session management",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class QueryRequest(BaseModel):
    """Enhanced query request with session support."""
    query: str
    conversation_id: Optional[str] = None
    session_token: Optional[str] = None
    user_id: Optional[str] = None
    verbose: bool = False
    stream: bool = True

class SessionCreateRequest(BaseModel):
    """Session creation request."""
    user_id: Optional[str] = None
    expires_in_hours: int = Field(default=24 * 7, ge=1, le=24 * 30)  # 1 hour to 30 days
    extra_data: Optional[Dict[str, Any]] = None

class ConversationRequest(BaseModel):
    """Conversation creation request."""
    title: Optional[str] = None
    session_token: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None

class ConversationResponse(BaseModel):
    """Conversation response."""
    id: str
    title: Optional[str]
    created_at: str
    updated_at: str
    extra_data: Optional[Dict[str, Any]]
    messages: Optional[List[Dict[str, Any]]] = None

class SessionResponse(BaseModel):
    """Session response."""
    id: str
    session_token: str
    expires_at: Optional[str]
    created_at: str
    extra_data: Optional[Dict[str, Any]]

# Singleton runtime instance
_runtime_instance: Optional[EnhancedAgentRuntime] = None

async def get_runtime() -> EnhancedAgentRuntime:
    """Get or create the Enhanced Agent Runtime instance."""
    global _runtime_instance
    if _runtime_instance is None:
        _runtime_instance = EnhancedAgentRuntime()
        # Short delay to allow kernel initialization
        await asyncio.sleep(1)
    return _runtime_instance

async def get_session_from_token(session_token: Optional[str] = Header(None, alias="X-Session-Token")) -> Optional[str]:
    """Get session from token header."""
    if not session_token:
        return None
    
    async with get_db() as db:
        session = await get_session(db, session_token)
        return session.id if session else None

async def get_user_from_session(session_token: Optional[str] = Header(None, alias="X-Session-Token")) -> Optional[str]:
    """Get user ID from session token."""
    if not session_token:
        return None
    
    async with get_db() as db:
        session = await get_session(db, session_token)
        return session.user_id if session else None

@app.on_event("startup")
async def startup_event():
    """Initialize database and runtime on startup."""
    await init_db()
    logger.info("Enhanced Runtime API started successfully")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Enhanced Agent Runtime API",
        "version": "2.0.0",
        "description": "Agent Runtime API with database persistence and session management",
        "endpoints": [
            {"path": "/api/query", "method": "POST", "description": "Process a user query with persistence"},
            {"path": "/api/sessions", "method": "POST", "description": "Create a new session"},
            {"path": "/api/conversations", "method": "POST", "description": "Create a new conversation"},
            {"path": "/api/conversations/{conversation_id}", "method": "GET", "description": "Get conversation history"},
            {"path": "/api/conversations", "method": "GET", "description": "List user conversations"},
            {"path": "/api/agents", "method": "GET", "description": "List available agents"},
            {"path": "/health", "method": "GET", "description": "Health check"}
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        async with get_db() as db:
            pass
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "version": "2.0.0"
        }
    except Exception as e:
        logger.exception("Health check failed")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.post("/api/sessions", response_model=SessionResponse)
async def create_session_endpoint(request: SessionCreateRequest):
    """Create a new session."""
    try:
        async with get_db() as db:
            session = await create_session(
                db,
                user_id=request.user_id,
                expires_in_hours=request.expires_in_hours,
                extra_data=request.extra_data
            )
            
            return SessionResponse(
                id=session.id,
                session_token=session.session_token,
                expires_at=session.expires_at.isoformat() if session.expires_at else None,
                created_at=session.created_at.isoformat(),
                extra_data=session.extra_data
            )
    except Exception as e:
        logger.exception(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/conversations", response_model=ConversationResponse)
async def create_conversation_endpoint(
    request: ConversationRequest,
    session_id: Optional[str] = Depends(get_session_from_token),
    user_id: Optional[str] = Depends(get_user_from_session)
):
    """Create a new conversation."""
    try:
        from database.session import create_conversation, get_or_create_anonymous_user
        
        async with get_db() as db:
            # Get or create user
            if not user_id:
                user = await get_or_create_anonymous_user(db)
                user_id = user.id
            
            conversation = await create_conversation(
                db,
                session_id=session_id,
                user_id=user_id,
                title=request.title,
                extra_data=request.extra_data
            )
            
            return ConversationResponse(
                id=conversation.id,
                title=conversation.title,
                created_at=conversation.created_at.isoformat(),
                updated_at=conversation.updated_at.isoformat(),
                extra_data=conversation.extra_data
            )
    except Exception as e:
        logger.exception(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
async def process_query(
    request: QueryRequest,
    runtime: EnhancedAgentRuntime = Depends(get_runtime),
    session_id: Optional[str] = Depends(get_session_from_token),
    user_id: Optional[str] = Depends(get_user_from_session)
):
    """Process a query with database persistence."""
    try:
        # Use session token from request if provided
        if request.session_token:
            async with get_db() as db:
                session = await get_session(db, request.session_token)
                if session:
                    session_id = session.id
                    user_id = session.user_id
        
        # Use user_id from request if provided
        if request.user_id:
            user_id = request.user_id
        
        if request.stream:
            return StreamingResponse(
                stream_query_response(request, runtime, session_id, user_id),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        else:
            result = await runtime.process_query_with_persistence(
                query=request.query,
                conversation_id=request.conversation_id,
                session_id=session_id,
                user_id=user_id,
                verbose=request.verbose
            )
            return result
    except Exception as e:
        logger.exception(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def stream_query_response(
    request: QueryRequest,
    runtime: EnhancedAgentRuntime,
    session_id: Optional[str],
    user_id: Optional[str]
):
    """Stream query response with persistence."""
    try:
        yield f"data: {json.dumps({'status': 'processing', 'query': request.query})}\n\n"
        
        async for chunk in runtime.stream_process_query_with_persistence(
            query=request.query,
            conversation_id=request.conversation_id,
            session_id=session_id,
            user_id=user_id,
            verbose=request.verbose
        ):
            if isinstance(chunk, dict):
                yield f"data: {json.dumps(chunk)}\n\n"
            else:
                yield f"data: {json.dumps({'content': str(chunk)})}\n\n"
        
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.exception(f"Error in streaming response: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

@app.get("/api/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    runtime: EnhancedAgentRuntime = Depends(get_runtime)
):
    """Get conversation history."""
    try:
        conversation = await runtime.get_conversation_history_from_db(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return ConversationResponse(
            id=conversation["id"],
            title=conversation["title"],
            created_at=conversation["created_at"],
            updated_at=conversation["updated_at"],
            extra_data=conversation["extra_data"],
            messages=conversation["messages"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations")
async def list_conversations(
    limit: int = 50,
    user_id: Optional[str] = Depends(get_user_from_session),
    runtime: EnhancedAgentRuntime = Depends(get_runtime)
):
    """List user conversations."""
    try:
        if not user_id:
            return {"conversations": []}
        
        conversations = await runtime.list_user_conversations(user_id, limit)
        return {"conversations": conversations}
    except Exception as e:
        logger.exception(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    runtime: EnhancedAgentRuntime = Depends(get_runtime)
):
    """Delete a conversation."""
    try:
        success = await runtime.delete_conversation(conversation_id)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"success": True, "message": "Conversation deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents")
async def list_agents(runtime: EnhancedAgentRuntime = Depends(get_runtime)):
    """List all available agents."""
    try:
        agents = runtime.get_all_agents()
        result = []
        
        for agent_id, agent in agents.items():
            result.append({
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.capabilities,
                "conversation_starters": agent.conversation_starters,
                "endpoint": agent.endpoint
            })
        
        return {"agents": result}
    except Exception as e:
        logger.exception(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host=settings.api_host, port=settings.api_port, log_level="info")