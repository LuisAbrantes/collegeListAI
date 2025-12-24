"""
College SQLModel for College List AI

Database model for college/university cache with structured stats.
Enhanced for Smart Sourcing RAG Pipeline with staleness detection.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON, String, Float, Integer
from sqlmodel import Field, SQLModel


class CollegeBase(SQLModel):
    """Base schema for College model with structured stats."""
    
    name: str = Field(
        ...,
        max_length=255,
        sa_column=Column(String(255), unique=True, index=True),
        description="University name"
    )
    
    # Structured stats for scoring (no longer just JSON blob)
    acceptance_rate: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="Acceptance rate as decimal (0.0-1.0)"
    )
    median_gpa: Optional[float] = Field(
        default=None,
        ge=0.0, le=4.0,
        description="Median GPA of admitted students"
    )
    sat_25th: Optional[int] = Field(
        default=None,
        ge=400, le=1600,
        description="25th percentile SAT score"
    )
    sat_75th: Optional[int] = Field(
        default=None,
        ge=400, le=1600,
        description="75th percentile SAT score"
    )
    
    # Financial aid info
    need_blind_international: bool = Field(
        default=False,
        description="Whether need-blind for international students"
    )
    meets_full_need: bool = Field(
        default=False,
        description="Whether meets 100% demonstrated need"
    )
    
    # Program strength
    major_strength: Optional[int] = Field(
        default=None,
        ge=1, le=10,
        description="Program strength score 1-10 for student's major"
    )
    
    # Campus info
    campus_setting: Optional[str] = Field(
        default=None,
        max_length=50,
        description="URBAN, SUBURBAN, RURAL"
    )
    
    # Data provenance
    data_source: Optional[str] = Field(
        default="gemini",
        max_length=100,
        description="Source: gemini, manual, common_data_set"
    )
    
    # Legacy JSON field for additional metadata
    content: Optional[str] = Field(
        default=None,
        description="JSON serialized additional metadata"
    )


class College(CollegeBase, table=True):
    """
    College cache database table model.
    
    Table name matches existing Supabase table 'colleges_cache'.
    Enhanced with structured fields for RAG pipeline.
    """
    
    __tablename__ = "colleges_cache"
    
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Unique college identifier"
    )
    
    # Note: created_at is managed by Supabase, not SQLModel
    # We only track updated_at for staleness detection
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp for staleness detection"
    )
    
    class Config:
        from_attributes = True


class CollegeCreate(CollegeBase):
    """Schema for creating a new college cache entry."""
    pass


class CollegeRead(CollegeBase):
    """Schema for reading college with all fields."""
    
    id: UUID
    updated_at: Optional[datetime]

