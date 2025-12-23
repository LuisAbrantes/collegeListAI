"""
Domain Models for College List AI

Pure Python/Pydantic models with no framework dependencies.
These models define the core business entities and validation rules.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import uuid


class CollegeLabel(str, Enum):
    """College classification based on admission probability."""
    REACH = "Reach"
    TARGET = "Target"
    SAFETY = "Safety"


class UserProfileCreate(BaseModel):
    """Schema for creating a new user profile."""
    nationality: str = Field(..., min_length=2, max_length=100, description="Student's citizenship/nationality")
    gpa: float = Field(..., ge=0.0, le=4.0, description="GPA on 4.0 scale")
    major: str = Field(..., min_length=2, max_length=100, description="Intended major/field of study")

    @field_validator("nationality", "major")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip()


class UserProfileUpdate(BaseModel):
    """Schema for updating an existing user profile. All fields optional."""
    nationality: Optional[str] = Field(None, min_length=2, max_length=100)
    gpa: Optional[float] = Field(None, ge=0.0, le=4.0)
    major: Optional[str] = Field(None, min_length=2, max_length=100)

    @field_validator("nationality", "major")
    @classmethod
    def validate_not_empty_if_provided(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip() if v else v


class UserProfile(BaseModel):
    """Complete user profile entity from database."""
    id: uuid.UUID
    user_id: uuid.UUID
    nationality: str
    gpa: float
    major: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CollegeMetadata(BaseModel):
    """Extended metadata for a college."""
    acceptance_rate: Optional[float] = Field(None, ge=0.0, le=100.0)
    need_blind_countries: Optional[List[str]] = None
    need_aware_countries: Optional[List[str]] = None
    application_deadline: Optional[str] = None
    financial_aid_available: bool = True
    avg_sat: Optional[int] = Field(None, ge=400, le=1600)
    avg_gpa: Optional[float] = Field(None, ge=0.0, le=4.0)


class College(BaseModel):
    """College entity from cache."""
    id: uuid.UUID
    name: str
    metadata: Optional[CollegeMetadata] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CollegeSearchResult(BaseModel):
    """Result from vector similarity search."""
    id: uuid.UUID
    name: str
    metadata: Optional[CollegeMetadata] = None
    similarity: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity score")


class CollegeRecommendation(BaseModel):
    """AI-generated college recommendation."""
    id: str
    name: str
    label: CollegeLabel
    match_score: int = Field(..., ge=0, le=100)
    reasoning: str
    financial_aid_summary: str
    official_links: List[str] = Field(default_factory=list)


class UserExclusion(BaseModel):
    """User's blacklisted college."""
    id: uuid.UUID
    user_id: uuid.UUID
    college_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class EmbeddingRequest(BaseModel):
    """Request to generate text embedding."""
    text: str = Field(..., min_length=1, max_length=10000)
    task_type: str = Field(default="retrieval_document", pattern="^(retrieval_document|retrieval_query)$")


class EmbeddingResponse(BaseModel):
    """Response containing generated embedding."""
    embedding: List[float]
    dimension: int
    model: str = "text-embedding-004"
