"""
College SQLModel for College List AI

Database model for college/university cache with vector support.
Note: Vector operations still handled by Supabase client (pgvector).
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class CollegeMetadataSchema(SQLModel):
    """
    Schema for college metadata stored as JSON.
    
    This mirrors the domain CollegeMetadata model for serialization.
    """
    
    acceptance_rate: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    need_blind_countries: Optional[List[str]] = None
    need_aware_countries: Optional[List[str]] = None
    application_deadline: Optional[str] = None
    financial_aid_available: bool = True
    avg_sat: Optional[int] = Field(default=None, ge=400, le=1600)
    avg_gpa: Optional[float] = Field(default=None, ge=0.0, le=4.0)


class CollegeBase(SQLModel):
    """Base schema for College model."""
    
    name: str = Field(
        ...,
        max_length=255,
        unique=True,
        index=True,
        description="University name"
    )
    content: Optional[str] = Field(
        default=None,
        description="JSON serialized metadata and description"
    )


class College(CollegeBase, table=True):
    """
    College cache database table model.
    
    Table name matches existing Supabase table 'colleges_cache'.
    Note: 'embedding' vector field is handled by Supabase RPC, not SQLModel.
    """
    
    __tablename__ = "colleges_cache"
    
    id: Optional[UUID] = Field(
        default=None,
        primary_key=True,
        description="Unique college identifier"
    )
    
    created_at: Optional[datetime] = Field(
        default=None,
        description="Record creation timestamp"
    )
    
    class Config:
        from_attributes = True


class CollegeCreate(CollegeBase):
    """Schema for creating a new college cache entry."""
    pass


class CollegeRead(CollegeBase):
    """Schema for reading college with all fields."""
    
    id: UUID
    created_at: datetime
