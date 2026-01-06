"""
College SQLModels for College List AI

Database models for normalized college data:
- College: Fixed institutional data (one row per university)
- CollegeMajorStats: Major-specific RAG data (one row per college+major combination)

This implements proper 3NF normalization for the RAG pipeline.
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Column, String, UniqueConstraint, ForeignKey
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from typing import List


# ============== Base Schemas ==============

class CollegeBase(SQLModel):
    """Base schema for College institutional data."""
    
    name: str = Field(
        ...,
        max_length=255,
        description="University name (unique identifier)"
    )
    
    ipeds_id: Optional[int] = Field(
        default=None,
        index=True,
        description="IPEDS Unit ID from College Scorecard (unique across US institutions)"
    )
    
    campus_setting: Optional[str] = Field(
        default=None,
        max_length=50,
        description="URBAN, SUBURBAN, RURAL"
    )
    
    # Tuition fields
    tuition_in_state: Optional[float] = Field(
        default=None,
        description="Annual in-state tuition in USD"
    )
    
    tuition_out_of_state: Optional[float] = Field(
        default=None,
        description="Annual out-of-state tuition in USD"
    )
    
    tuition_international: Optional[float] = Field(
        default=None,
        description="Annual international student tuition in USD"
    )
    
    # Financial aid policies
    need_blind_domestic: bool = Field(
        default=True,
        description="Whether need-blind for domestic students"
    )
    
    need_blind_international: bool = Field(
        default=False,
        description="Whether need-blind for international students"
    )
    
    meets_full_need: bool = Field(
        default=False,
        description="Whether meets 100% demonstrated need"
    )
    
    # Location
    state: Optional[str] = Field(
        default=None,
        max_length=50,
        description="US state where main campus is located"
    )
    
    city: Optional[str] = Field(
        default=None,
        max_length=100,
        description="City where main campus is located"
    )
    
    # Admission statistics (from College Scorecard)
    acceptance_rate: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="Overall acceptance rate as decimal"
    )
    
    sat_25th: Optional[int] = Field(
        default=None,
        ge=400, le=1600,
        description="25th percentile SAT score (combined)"
    )
    
    sat_75th: Optional[int] = Field(
        default=None,
        ge=400, le=1600,
        description="75th percentile SAT score (combined)"
    )
    
    act_25th: Optional[int] = Field(
        default=None,
        ge=1, le=36,
        description="25th percentile ACT score"
    )
    
    act_75th: Optional[int] = Field(
        default=None,
        ge=1, le=36,
        description="75th percentile ACT score"
    )
    
    student_size: Optional[int] = Field(
        default=None,
        description="Total undergraduate enrollment"
    )
    
    # Metadata
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp for freshness checking"
    )



class CollegeMajorStatsBase(SQLModel):
    """Base schema for major-specific statistics."""
    
    major_name: str = Field(
        ...,
        max_length=100,
        index=True,
        description="Major name (e.g., 'Computer Science', 'Physics')"
    )
    
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
    
    major_strength: Optional[int] = Field(
        default=None,
        ge=1, le=10,
        description="Program strength score 1-10 for this major"
    )
    
    data_source: Optional[str] = Field(
        default="gemini",
        max_length=100,
        description="Source: gemini, ollama_simulated, manual, common_data_set"
    )


# ============== Database Table Models ==============

class College(CollegeBase, table=True):
    """
    College institutional data table.
    
    Contains fixed data about the university that doesn't change per major.
    One row per university, with name as unique identifier.
    """
    
    __tablename__ = "colleges"
    __table_args__ = (
        UniqueConstraint('name', name='colleges_name_unique'),
    )
    
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Unique college identifier"
    )
    
    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="When this college was first added"
    )
    
    # Relationship to major stats
    major_stats: List["CollegeMajorStats"] = Relationship(back_populates="college")
    
    class Config:
        from_attributes = True


class CollegeMajorStats(CollegeMajorStatsBase, table=True):
    """
    Major-specific statistics table for RAG pipeline.
    
    Contains admission statistics and program strength for a specific major.
    Each (college_id, major_name) combination is unique.
    """
    
    __tablename__ = "college_major_stats"
    __table_args__ = (
        UniqueConstraint('college_id', 'major_name', name='college_major_stats_unique'),
    )
    
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Unique stats record identifier"
    )
    
    college_id: UUID = Field(
        ...,
        foreign_key="colleges.id",
        index=True,
        description="Foreign key to colleges table"
    )
    
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp for staleness detection"
    )
    
    # Relationship to parent college
    college: Optional[College] = Relationship(back_populates="major_stats")
    
    class Config:
        from_attributes = True


# ============== Create/Update Schemas ==============

class CollegeCreate(CollegeBase):
    """Schema for creating a new college."""
    pass


class CollegeRead(CollegeBase):
    """Schema for reading college with ID."""
    id: UUID
    created_at: Optional[datetime]


class CollegeMajorStatsCreate(CollegeMajorStatsBase):
    """Schema for creating new major stats."""
    college_id: UUID


class CollegeMajorStatsRead(CollegeMajorStatsBase):
    """Schema for reading major stats with all fields."""
    id: UUID
    college_id: UUID
    updated_at: Optional[datetime]


# ============== Joined Response Model ==============

class CollegeWithMajorStats(SQLModel):
    """
    Combined view for API responses.
    
    Used when querying colleges with their specific major stats joined.
    """
    # College fields
    id: UUID
    name: str
    campus_setting: Optional[str] = None
    need_blind_international: bool = False
    meets_full_need: bool = False
    
    # Major stats fields
    major_name: str
    acceptance_rate: Optional[float] = None
    median_gpa: Optional[float] = None
    sat_25th: Optional[int] = None
    sat_75th: Optional[int] = None
    major_strength: Optional[int] = None
    data_source: Optional[str] = None
    updated_at: Optional[datetime] = None
