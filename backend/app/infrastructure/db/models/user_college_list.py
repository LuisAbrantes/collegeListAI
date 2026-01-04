"""
User College List and Exclusions Models

SQLModels for:
- UserCollegeListItem: Saved colleges in user's list
- UserExclusion: Schools to never suggest again
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class UserCollegeListItemBase(SQLModel):
    """Base schema for college list items."""
    
    college_name: str = Field(
        ...,
        max_length=255,
        description="Name of the college"
    )
    
    label: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Category: reach, target, or safety"
    )
    
    notes: Optional[str] = Field(
        default=None,
        description="User's notes about this school"
    )


class UserCollegeListItem(UserCollegeListItemBase, table=True):
    """User's saved college list item."""
    
    __tablename__ = "user_college_list"
    
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True
    )
    
    user_id: UUID = Field(
        ...,
        foreign_key="profiles.id",
        index=True,
        description="User who saved this college"
    )
    
    added_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this college was added"
    )


class UserCollegeListItemCreate(UserCollegeListItemBase):
    """Schema for creating a college list item."""
    pass


class UserCollegeListItemUpdate(SQLModel):
    """Schema for updating a college list item."""
    label: Optional[str] = None
    notes: Optional[str] = None


# =============================================================================
# Exclusions
# =============================================================================

class UserExclusionBase(SQLModel):
    """Base schema for exclusions."""
    
    college_name: str = Field(
        ...,
        max_length=255,
        description="Name of the excluded college"
    )
    
    reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional reason for exclusion"
    )


class UserExclusion(UserExclusionBase, table=True):
    """School that user never wants to see in recommendations."""
    
    __tablename__ = "user_exclusions"
    
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True
    )
    
    user_id: UUID = Field(
        ...,
        foreign_key="profiles.id",
        index=True,
        description="User who excluded this college"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this exclusion was created"
    )


class UserExclusionCreate(UserExclusionBase):
    """Schema for creating an exclusion."""
    pass
