"""
UserProfile SQLModel for College List AI

Database model for student profiles with all academic and preference fields.
Follows SOLID principles:
- Single Responsibility: Only defines UserProfile schema
- Open/Closed: Extensible via inheritance, closed for modification
- Liskov Substitution: Can be used anywhere base SQLModel is expected
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Column, JSON
from pydantic import ConfigDict
from sqlmodel import Field, SQLModel

from app.domain.models import (
    CitizenshipStatus,
    HouseholdIncomeTier,
    CampusVibe,
    PostGradGoal,
)


class UserProfileBase(SQLModel):
    """
    Base schema for UserProfile (shared between create/update/read).
    
    Follows DRY principle - common fields in one place.
    """
    
    # Core identification
    citizenship_status: Optional[CitizenshipStatus] = Field(
        default=None,
        description="Student citizenship/residency status"
    )
    nationality: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="Country of citizenship"
    )
    
    # User identity (UI only - NOT sent to AI)
    name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="User's name (UI display only, never sent to AI)"
    )
    
    # Academic metrics
    gpa: float = Field(
        ...,
        ge=0.0,
        le=4.0,
        description="GPA on 4.0 scale"
    )
    major: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Intended major/field of study"
    )
    sat_score: Optional[int] = Field(
        default=None,
        ge=400,
        le=1600,
        description="SAT score"
    )
    act_score: Optional[int] = Field(
        default=None,
        ge=1,
        le=36,
        description="ACT score"
    )
    
    # US-specific fields
    state_of_residence: Optional[str] = Field(
        default=None,
        max_length=50,
        description="State for in-state tuition (US residents only)"
    )
    
    # Financial info
    household_income_tier: Optional[HouseholdIncomeTier] = Field(
        default=None,
        description="Income tier for aid estimation"
    )
    
    # International-specific
    english_proficiency_score: Optional[int] = Field(
        default=None,
        ge=0,
        le=120,
        description="TOEFL/IELTS score (internationals)"
    )
    
    # Fit factors
    campus_vibe: Optional[CampusVibe] = Field(
        default=None,
        description="Preferred campus environment"
    )
    is_student_athlete: bool = Field(
        default=False,
        description="Pursuing athletic recruitment"
    )
    has_legacy_status: bool = Field(
        default=False,
        description="Has family alumni connections"
    )
    legacy_universities: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Universities with legacy status"
    )
    post_grad_goal: Optional[PostGradGoal] = Field(
        default=None,
        description="Post-graduation career focus"
    )


class UserProfile(UserProfileBase, table=True):
    """
    UserProfile database table model.
    
    Table name matches existing Supabase table 'profiles'.
    """
    
    __tablename__ = "profiles"
    
    # Primary key
    id: Optional[UUID] = Field(
        default=None,
        primary_key=True,
        description="Unique profile identifier"
    )
    
    # Foreign key to auth.users
    user_id: UUID = Field(
        ...,
        unique=True,
        index=True,
        description="Reference to authenticated user"
    )
    
    # Timestamps
    created_at: Optional[datetime] = Field(
        default=None,
        description="Record creation timestamp"
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Last update timestamp"
    )
    
    model_config = ConfigDict(from_attributes=True)


class UserProfileCreate(UserProfileBase):
    """Schema for creating a new user profile."""
    pass


class UserProfileUpdate(SQLModel):
    """
    Schema for updating user profile (all fields optional).
    
    Follows Open/Closed - allows partial updates without modifying base.
    """
    
    citizenship_status: Optional[CitizenshipStatus] = None
    nationality: Optional[str] = Field(default=None, min_length=2, max_length=100)
    name: Optional[str] = Field(default=None, max_length=100)
    gpa: Optional[float] = Field(default=None, ge=0.0, le=4.0)
    major: Optional[str] = Field(default=None, min_length=2, max_length=100)
    sat_score: Optional[int] = Field(default=None, ge=400, le=1600)
    act_score: Optional[int] = Field(default=None, ge=1, le=36)
    state_of_residence: Optional[str] = Field(default=None, max_length=50)
    household_income_tier: Optional[HouseholdIncomeTier] = None
    english_proficiency_score: Optional[int] = Field(default=None, ge=0, le=120)
    campus_vibe: Optional[CampusVibe] = None
    is_student_athlete: Optional[bool] = None
    has_legacy_status: Optional[bool] = None
    legacy_universities: Optional[List[str]] = None
    post_grad_goal: Optional[PostGradGoal] = None


class UserProfileRead(UserProfileBase):
    """Schema for reading user profile with all fields."""
    
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
