"""
Chat Domain Models for College List AI

Pure Python/Pydantic models for chat entities.
Follows Single Responsibility Principle - only defines chat schemas.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MessageRole(str, Enum):
    """Role of the message sender."""
    USER = "user"
    ASSISTANT = "assistant"


class ChatThreadCreate(BaseModel):
    """Schema for creating a new chat thread."""
    user_id: UUID
    title: Optional[str] = Field(None, max_length=255)


class ChatThreadUpdate(BaseModel):
    """Schema for updating a chat thread."""
    title: Optional[str] = Field(None, max_length=255)


class ChatThread(BaseModel):
    """Complete chat thread entity."""
    id: UUID
    user_id: UUID
    title: Optional[str] = None
    langgraph_thread_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMessageCreate(BaseModel):
    """Schema for creating a new chat message."""
    thread_id: UUID
    role: MessageRole
    content: str = Field(..., min_length=1)
    sources: Optional[List[dict]] = None


class ChatMessage(BaseModel):
    """Complete chat message entity."""
    id: UUID
    thread_id: UUID
    role: MessageRole
    content: str
    sources: Optional[List[dict]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatThreadWithMessages(ChatThread):
    """Chat thread with its messages included."""
    messages: List[ChatMessage] = Field(default_factory=list)
