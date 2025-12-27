"""
Base Model for SQLModel ORM

Provides common fields and behavior for all database models.
Follows Single Responsibility Principle - only defines base schema.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class TimestampMixin(SQLModel):
    """
    Mixin providing timestamp fields for models.
    
    Follows Interface Segregation - separates timestamp concern.
    """
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        description="Record creation timestamp (UTC)"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
        description="Last update timestamp (UTC)"
    )


class UUIDMixin(SQLModel):
    """
    Mixin providing UUID primary key.
    
    Follows Single Responsibility - only handles ID generation.
    """
    
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        description="Unique identifier (UUID v4)"
    )


class BaseModel(UUIDMixin, TimestampMixin):
    """
    Base model combining UUID and timestamp mixins.
    
    All database models should inherit from this class.
    Provides: id, created_at, updated_at
    """
    
    class Config:
        """Pydantic/SQLModel configuration."""
        from_attributes = True
        validate_assignment = True
