"""
ChatThread SQLModel for College List AI

Database model for chat threads.
Follows SOLID principles:
- Single Responsibility: Only defines ChatThread schema
- Open/Closed: Extensible via inheritance
"""

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Column, String, Index
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from app.infrastructure.db.models.chat_message import ChatMessage


class ChatThread(SQLModel, table=True):
    """
    ChatThread database table model.
    
    Stores conversation threads for users.
    """
    
    __tablename__ = "chat_threads"
    
    # Primary key
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        description="Unique thread identifier"
    )
    
    # Foreign key to auth.users
    user_id: UUID = Field(
        ...,
        index=True,
        nullable=False,
        description="Reference to authenticated user"
    )
    
    # Thread metadata
    title: Optional[str] = Field(
        default=None,
        max_length=255,
        sa_column=Column(String(255)),
        description="Auto-generated from first message"
    )
    
    # LangGraph integration
    langgraph_thread_id: Optional[str] = Field(
        default=None,
        max_length=100,
        sa_column=Column(String(100)),
        description="LangGraph thread ID for checkpoints"
    )
    
    # Timestamps (naive UTC for Supabase TIMESTAMP WITHOUT TIME ZONE compatibility)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        description="Thread creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        description="Last message timestamp"
    )
    
    # Relationships
    messages: list["ChatMessage"] = Relationship(
        back_populates="thread",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    
    class Config:
        from_attributes = True
