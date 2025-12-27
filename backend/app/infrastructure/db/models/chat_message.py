"""
ChatMessage SQLModel for College List AI

Database model for chat messages.
Follows SOLID principles:
- Single Responsibility: Only defines ChatMessage schema
- Open/Closed: Extensible via inheritance
"""

from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Column, Text, String, JSON, ForeignKey
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from app.infrastructure.db.models.chat_thread import ChatThread


class ChatMessage(SQLModel, table=True):
    """
    ChatMessage database table model.
    
    Stores individual messages within chat threads.
    """
    
    __tablename__ = "chat_messages"
    
    # Primary key
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        description="Unique message identifier"
    )
    
    # Foreign key to chat_threads
    thread_id: UUID = Field(
        ...,
        sa_column=Column(
            "thread_id",
            ForeignKey("chat_threads.id", ondelete="CASCADE"),
            nullable=False,
            index=True
        ),
        description="Reference to parent thread"
    )
    
    # Message content
    role: str = Field(
        ...,
        max_length=20,
        sa_column=Column(String(20), nullable=False),
        description="Message role: 'user' or 'assistant'"
    )
    
    content: str = Field(
        ...,
        sa_column=Column(Text, nullable=False),
        description="Message content"
    )
    
    # Optional grounding sources
    sources: Optional[List[dict]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Grounding sources for assistant messages"
    )
    
    # Timestamp (naive UTC for Supabase TIMESTAMP WITHOUT TIME ZONE compatibility)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        description="Message timestamp"
    )
    
    # Relationships
    thread: Optional["ChatThread"] = Relationship(back_populates="messages")
    
    class Config:
        from_attributes = True
