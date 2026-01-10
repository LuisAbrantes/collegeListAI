"""
Application Outcome Model

Tracks real admission results to validate and improve predictions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class OutcomeStatus(str, Enum):
    """Possible admission outcomes."""
    APPLIED = "applied"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WAITLISTED = "waitlisted"
    DEFERRED = "deferred"
    ENROLLED = "enrolled"


class ApplicationOutcomeBase(SQLModel):
    """Base schema for application outcomes."""
    
    college_name: str = Field(
        ...,
        max_length=255,
        description="Name of the college"
    )
    
    predicted_label: Optional[str] = Field(
        default=None,
        max_length=50,
        description="AI prediction at time of recommendation (Reach/Target/Safety)"
    )
    
    outcome_status: OutcomeStatus = Field(
        ...,
        description="Actual admission outcome"
    )
    
    cycle_year: int = Field(
        ...,
        ge=2020,
        le=2035,  # Extended to avoid hardcoded limit issue
        description="Admission cycle year"
    )
    
    submitted_at: Optional[datetime] = Field(
        default=None,
        description="When application was submitted"
    )


class ApplicationOutcome(ApplicationOutcomeBase, table=True):
    """Real admission outcome for ML training."""
    
    __tablename__ = "application_outcomes"
    
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True
    )
    
    user_id: UUID = Field(
        ...,
        foreign_key="profiles.id",
        index=True,
        description="User who reported this outcome"
    )
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this record was created"
    )
    
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this record was last updated"
    )


class ApplicationOutcomeCreate(ApplicationOutcomeBase):
    """Schema for creating an outcome."""
    user_id: UUID


class ApplicationOutcomeUpdate(SQLModel):
    """Schema for updating an outcome."""
    outcome_status: Optional[OutcomeStatus] = None
    submitted_at: Optional[datetime] = None
