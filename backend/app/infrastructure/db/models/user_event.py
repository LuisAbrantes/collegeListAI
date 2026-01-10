"""
User Event Model for Analytics

Tracks user behavior for data flywheel optimization.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class UserEventType(str, Enum):
    """Types of user events to track."""
    SEARCH_EXECUTED = "search_executed"
    RECOMMENDATION_VIEWED = "recommendation_viewed"
    RECOMMENDATION_ADDED = "recommendation_added"
    RECOMMENDATION_REJECTED = "recommendation_rejected"
    COLLEGE_INFO_EXPANDED = "college_info_expanded"
    LIST_EXPORTED = "list_exported"


class UserEvent(SQLModel, table=True):
    """User behavior event for analytics."""
    
    __tablename__ = "user_events"
    
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True
    )
    
    user_id: UUID = Field(
        ...,
        foreign_key="profiles.id",
        index=True,
        description="User who triggered this event"
    )
    
    event_type: str = Field(
        ...,
        max_length=50,
        sa_column=Column(String(50), nullable=False),
        description="Type of event"
    )
    
    college_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="College associated with event (if applicable)"
    )
    
    event_data: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSONB, default={}),
        description="Additional event data (query, position, time_spent_ms, etc.)"
    )
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this event occurred"
    )


class UserEventCreate(SQLModel):
    """Schema for creating a user event."""
    user_id: UUID
    event_type: UserEventType
    college_name: Optional[str] = None
    event_data: Optional[dict] = None
