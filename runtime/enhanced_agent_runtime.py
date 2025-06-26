#!/usr/bin/env python3

"""Enhanced Agent Runtime with database persistence and session management."""

import asyncio
import datetime
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from config import get_settings
from database import get_db, create_conversation, get_conversation
from database.models import Message, Conversation, Session, User
from database.session import get_or_create_anonymous_user
from runtime.agent_runtime import AgentRuntime as BaseAgentRuntime, AgentPlugin
from sqlalchemy import select

settings = get_settings()
logger = logging.getLogger("enhanced_agent_runtime")


class EnhancedAgentRuntime(BaseAgentRuntime):
    """Enhanced Agent Runtime with database persistence."""
    
    def __init__(self, config_path: str = None):
        super().__init__(config_path)
        self.db_conversations: Dict[str, str] = {}  # Map conversation_id to database conversation_id
    
    async def process_query_with_persistence(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """Process a query with database persistence."""
        async with get_db() as db:
            # Get or create user
            if user_id:
                stmt = select(User).where(User.id == user_id)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                if not user:
                    user = await get_or_create_anonymous_user(db)
            else:
                user = await get_or_create_anonymous_user(db)
            
            # Get or create conversation
            db_conversation = None
            if conversation_id:
                db_conversation = await get_conversation(db, conversation_id)
            
            if not db_conversation:
                db_conversation = await create_conversation(
                    db,
                    session_id=session_id,
                    user_id=user.id,
                    title=query[:50] + "..." if len(query) > 50 else query
                )
                conversation_id = db_conversation.id
            
            # Store user message
            user_message = Message(
                conversation_id=conversation_id,
                role="user",
                content=query,
                sender_id=user.id,
                message_type="text"
            )
            db.add(user_message)
            await db.commit()
            
            # Process with base runtime
            result = await super().process_query(
                query=query,
                conversation_id=conversation_id,
                verbose=verbose
            )
            
            # Store assistant response
            assistant_message = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=result.get("content", ""),
                sender_id="runtime",
                recipient_id=user.id,
                message_type="text",
                agents_used=result.get("agents_used", []),
                execution_trace=result.get("execution_trace", [])
            )
            db.add(assistant_message)
            await db.commit()
            
            # Update conversation timestamp
            db_conversation.updated_at = datetime.datetime.utcnow()
            await db.commit()
            
            # Add database IDs to result
            result["conversation_id"] = conversation_id
            result["user_message_id"] = user_message.id
            result["assistant_message_id"] = assistant_message.id
            
            return result
    
    async def stream_process_query_with_persistence(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        verbose: bool = False
    ):
        """Stream process query with database persistence."""
        async with get_db() as db:
            # Get or create user
            if user_id:
                stmt = select(User).where(User.id == user_id)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                if not user:
                    user = await get_or_create_anonymous_user(db)
            else:
                user = await get_or_create_anonymous_user(db)
            
            # Get or create conversation
            db_conversation = None
            if conversation_id:
                db_conversation = await get_conversation(db, conversation_id)
            
            if not db_conversation:
                db_conversation = await create_conversation(
                    db,
                    session_id=session_id,
                    user_id=user.id,
                    title=query[:50] + "..." if len(query) > 50 else query
                )
                conversation_id = db_conversation.id
            
            # Store user message
            user_message = Message(
                conversation_id=conversation_id,
                role="user",
                content=query,
                sender_id=user.id,
                message_type="text"
            )
            db.add(user_message)
            await db.commit()
            
            # Collect the full response for database storage
            full_response_content = ""
            agents_used = []
            
            # Stream process with base runtime
            async for chunk in super().stream_process_query(
                query=query,
                conversation_id=conversation_id,
                verbose=verbose
            ):
                # Yield chunk to client
                yield chunk
                
                # Collect response data
                if isinstance(chunk, dict):
                    if "content" in chunk:
                        full_response_content += str(chunk["content"])
                    if "agents_used" in chunk:
                        agents_used = chunk["agents_used"]
                    if chunk.get("complete", False):
                        # Store final assistant response
                        assistant_message = Message(
                            conversation_id=conversation_id,
                            role="assistant",
                            content=full_response_content,
                            sender_id="runtime",
                            recipient_id=user.id,
                            message_type="text",
                            agents_used=agents_used
                        )
                        db.add(assistant_message)
                        
                        # Update conversation timestamp
                        db_conversation.updated_at = datetime.datetime.utcnow()
                        await db.commit()
                        
                        # Add database info to final chunk
                        chunk["user_message_id"] = user_message.id
                        chunk["assistant_message_id"] = assistant_message.id
                        
                        yield chunk
    
    async def get_conversation_history_from_db(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation history from database."""
        async with get_db() as db:
            # Get conversation
            conversation = await get_conversation(db, conversation_id)
            if not conversation:
                return None
            
            # Get messages
            stmt = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            )
            result = await db.execute(stmt)
            messages = result.scalars().all()
            
            return {
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "extra_data": conversation.extra_data,
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "sender_id": msg.sender_id,
                        "recipient_id": msg.recipient_id,
                        "message_type": msg.message_type,
                        "agents_used": msg.agents_used,
                        "execution_trace": msg.execution_trace,
                        "extra_data": msg.extra_data,
                        "created_at": msg.created_at.isoformat(),
                        "updated_at": msg.updated_at.isoformat()
                    }
                    for msg in messages
                ]
            }
    
    async def list_user_conversations(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """List conversations for a user."""
        async with get_db() as db:
            stmt = (
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .order_by(Conversation.updated_at.desc())
                .limit(limit)
            )
            result = await db.execute(stmt)
            conversations = result.scalars().all()
            
            return [
                {
                    "id": conv.id,
                    "title": conv.title,
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat(),
                    "extra_data": conv.extra_data
                }
                for conv in conversations
            ]
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and its messages."""
        async with get_db() as db:
            conversation = await get_conversation(db, conversation_id)
            if not conversation:
                return False
            
            await db.delete(conversation)
            await db.commit()
            return True