"""
Chat Routes for College List AI

API endpoints for chat thread and message management.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.database import get_session
from app.infrastructure.db.chat_service import ChatService
from app.domain.chat import MessageRole
from app.api.dependencies import get_current_user_id as _get_current_user_str


router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class ThreadResponse(BaseModel):
    """Response model for a chat thread."""
    id: UUID
    user_id: UUID
    title: Optional[str] = None
    langgraph_thread_id: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """Response model for a chat message."""
    id: UUID
    thread_id: UUID
    role: str
    content: str
    sources: Optional[List[dict]] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class ThreadListResponse(BaseModel):
    """Response model for list of threads."""
    threads: List[ThreadResponse]
    total: int


class MessageListResponse(BaseModel):
    """Response model for list of messages."""
    messages: List[MessageResponse]
    thread_id: UUID


class CreateThreadRequest(BaseModel):
    """Request to create a new thread."""
    title: Optional[str] = Field(None, max_length=255)


class CreateMessageRequest(BaseModel):
    """Request to add a message to a thread."""
    content: str = Field(..., min_length=1)
    role: str = Field(default="user", pattern="^(user|assistant)$")
    sources: Optional[List[dict]] = None


# ============================================================================
# Dependency Injection
# ============================================================================

async def get_current_user_id(
    user_id_str: str = Depends(_get_current_user_str),
) -> UUID:
    """Convert verified JWT user_id (str) to UUID for downstream repos."""
    return UUID(user_id_str)


def get_chat_service(session: AsyncSession = Depends(get_session)) -> ChatService:
    """Get ChatService instance."""
    return ChatService(session)


# ============================================================================
# Thread Endpoints
# ============================================================================

@router.get("/chats", response_model=ThreadListResponse)
async def list_threads(
    limit: int = 10,
    offset: int = 0,
    user_id: UUID = Depends(get_current_user_id),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    List all chat threads for the current user.
    
    Returns threads ordered by most recently updated.
    """
    threads = await chat_service.get_user_threads(
        user_id=user_id,
        limit=limit,
        offset=offset
    )
    
    return ThreadListResponse(
        threads=[
            ThreadResponse(
                id=t.id,
                user_id=t.user_id,
                title=t.title,
                langgraph_thread_id=t.langgraph_thread_id,
                created_at=t.created_at.isoformat(),
                updated_at=t.updated_at.isoformat()
            )
            for t in threads
        ],
        total=len(threads)
    )


@router.post("/chats", response_model=ThreadResponse, status_code=201)
async def create_thread(
    request: CreateThreadRequest = None,
    user_id: UUID = Depends(get_current_user_id),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Create a new chat thread.
    
    Enforces 5-thread limit per user. If exceeded, oldest thread is deleted.
    """
    title = request.title if request else None
    
    thread = await chat_service.create_thread(
        user_id=user_id,
        title=title
    )
    
    return ThreadResponse(
        id=thread.id,
        user_id=thread.user_id,
        title=thread.title,
        langgraph_thread_id=thread.langgraph_thread_id,
        created_at=thread.created_at.isoformat(),
        updated_at=thread.updated_at.isoformat()
    )


@router.get("/chats/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get a specific chat thread."""
    thread = await chat_service.get_thread(thread_id)
    
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    if thread.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return ThreadResponse(
        id=thread.id,
        user_id=thread.user_id,
        title=thread.title,
        langgraph_thread_id=thread.langgraph_thread_id,
        created_at=thread.created_at.isoformat(),
        updated_at=thread.updated_at.isoformat()
    )


@router.delete("/chats/{thread_id}", status_code=204)
async def delete_thread(
    thread_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Delete a chat thread and all its messages."""
    # Verify ownership first
    thread = await chat_service.get_thread(thread_id)
    
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    if thread.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await chat_service.delete_thread(thread_id)


# ============================================================================
# Message Endpoints
# ============================================================================

@router.get("/chats/{thread_id}/messages", response_model=MessageListResponse)
async def get_messages(
    thread_id: UUID,
    limit: int = 100,
    offset: int = 0,
    user_id: UUID = Depends(get_current_user_id),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Get all messages in a chat thread.
    
    Returns messages ordered by creation time (oldest first).
    """
    # Verify ownership first
    thread = await chat_service.get_thread(thread_id)
    
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    if thread.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    messages = await chat_service.get_thread_messages(
        thread_id=thread_id,
        limit=limit,
        offset=offset
    )
    
    return MessageListResponse(
        messages=[
            MessageResponse(
                id=m.id,
                thread_id=m.thread_id,
                role=m.role,
                content=m.content,
                sources=m.sources,
                created_at=m.created_at.isoformat()
            )
            for m in messages
        ],
        thread_id=thread_id
    )


@router.post("/chats/{thread_id}/messages", response_model=MessageResponse, status_code=201)
async def add_message(
    thread_id: UUID,
    request: CreateMessageRequest,
    user_id: UUID = Depends(get_current_user_id),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Add a message to a chat thread.
    
    If this is the first user message, thread title is auto-generated.
    """
    # Verify ownership first
    thread = await chat_service.get_thread(thread_id)
    
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    if thread.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    role = MessageRole.USER if request.role == "user" else MessageRole.ASSISTANT
    
    message = await chat_service.add_message(
        thread_id=thread_id,
        role=role,
        content=request.content,
        sources=request.sources
    )
    
    return MessageResponse(
        id=message.id,
        thread_id=message.thread_id,
        role=message.role,
        content=message.content,
        sources=message.sources,
        created_at=message.created_at.isoformat()
    )
