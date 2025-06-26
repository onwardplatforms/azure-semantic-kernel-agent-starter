"""Session management utilities."""

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Session as SessionModel, User, Conversation


async def create_session(
    db: AsyncSession,
    user_id: Optional[str] = None,
    expires_in_hours: int = 24 * 7,  # Default 7 days
    extra_data: Optional[dict] = None
) -> SessionModel:
    """Create a new session."""
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
    
    session = SessionModel(
        user_id=user_id,
        session_token=session_token,
        expires_at=expires_at,
        extra_data=extra_data or {}
    )
    
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    return session


async def get_session(db: AsyncSession, session_token: str) -> Optional[SessionModel]:
    """Get a session by token."""
    stmt = select(SessionModel).where(SessionModel.session_token == session_token)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    # Check if session is expired
    if session and session.expires_at and session.expires_at < datetime.utcnow():
        await delete_session(db, session_token)
        return None
    
    return session


async def delete_session(db: AsyncSession, session_token: str) -> bool:
    """Delete a session by token."""
    stmt = select(SessionModel).where(SessionModel.session_token == session_token)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if session:
        await db.delete(session)
        await db.commit()
        return True
    
    return False


async def get_or_create_anonymous_user(db: AsyncSession) -> User:
    """Get or create an anonymous user for sessionless interactions."""
    # Look for existing anonymous user
    stmt = select(User).where(User.username == "anonymous")
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            username="anonymous",
            email=None
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    return user


async def create_conversation(
    db: AsyncSession,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    title: Optional[str] = None,
    extra_data: Optional[dict] = None
) -> Conversation:
    """Create a new conversation."""
    conversation = Conversation(
        session_id=session_id,
        user_id=user_id,
        title=title,
        extra_data=extra_data or {}
    )
    
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    
    return conversation


async def get_conversation(db: AsyncSession, conversation_id: str) -> Optional[Conversation]:
    """Get a conversation by ID."""
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()