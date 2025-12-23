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


class CitizenshipStatus(str, Enum):
    """Student citizenship/residency status for financial aid determination."""
    US_CITIZEN = "US_CITIZEN"
    PERMANENT_RESIDENT = "PERMANENT_RESIDENT"
    INTERNATIONAL = "INTERNATIONAL"
    DACA = "DACA"


class HouseholdIncomeTier(str, Enum):
    """Income tier for financial aid estimation."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class CampusVibe(str, Enum):
    """Preferred campus environment type."""
    URBAN = "URBAN"
    SUBURBAN = "SUBURBAN"
    RURAL = "RURAL"


class PostGradGoal(str, Enum):
    """Post-graduation career focus."""
    JOB_PLACEMENT = "JOB_PLACEMENT"
    GRADUATE_SCHOOL = "GRADUATE_SCHOOL"
    ENTREPRENEURSHIP = "ENTREPRENEURSHIP"
    UNDECIDED = "UNDECIDED"


class UserProfileCreate(BaseModel):
    """Schema for creating a new user profile."""
    # Core identification
    citizenship_status: CitizenshipStatus = Field(..., description="Student citizenship/residency status")
    nationality: Optional[str] = Field(None, min_length=2, max_length=100, description="Country of citizenship (optional context)")
    
    # Academic metrics
    gpa: float = Field(..., ge=0.0, le=4.0, description="GPA on 4.0 scale")
    major: str = Field(..., min_length=2, max_length=100, description="Intended major/field of study")
    sat_score: Optional[int] = Field(None, ge=400, le=1600, description="SAT score")
    act_score: Optional[int] = Field(None, ge=1, le=36, description="ACT score")
    
    # US-specific fields
    state_of_residence: Optional[str] = Field(None, max_length=50, description="State for in-state tuition (US residents only)")
    
    # Financial info
    household_income_tier: Optional[HouseholdIncomeTier] = Field(None, description="Income tier for aid estimation")
    
    # International-specific
    english_proficiency_score: Optional[int] = Field(None, ge=0, le=120, description="TOEFL/IELTS score (internationals)")
    
    # Fit factors
    campus_vibe: Optional[CampusVibe] = Field(None, description="Preferred campus environment")
    is_student_athlete: bool = Field(False, description="Pursuing athletic recruitment")
    has_legacy_status: bool = Field(False, description="Has family alumni connections")
    legacy_universities: Optional[List[str]] = Field(None, description="Universities with legacy status")
    post_grad_goal: Optional[PostGradGoal] = Field(None, description="Post-graduation career focus")

    @field_validator("major")
    @classmethod
    def validate_major_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Major cannot be empty or whitespace only")
        return v.strip()
    
    @field_validator("nationality")
    @classmethod
    def validate_nationality_if_provided(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Nationality cannot be empty if provided")
        return v.strip() if v else v


class UserProfileUpdate(BaseModel):
    """Schema for updating an existing user profile. All fields optional."""
    # Core identification
    citizenship_status: Optional[CitizenshipStatus] = None
    nationality: Optional[str] = Field(None, min_length=2, max_length=100)
    
    # Academic metrics
    gpa: Optional[float] = Field(None, ge=0.0, le=4.0)
    major: Optional[str] = Field(None, min_length=2, max_length=100)
    sat_score: Optional[int] = Field(None, ge=400, le=1600)
    act_score: Optional[int] = Field(None, ge=1, le=36)
    
    # US-specific fields
    state_of_residence: Optional[str] = Field(None, max_length=50)
    
    # Financial info
    household_income_tier: Optional[HouseholdIncomeTier] = None
    
    # International-specific
    english_proficiency_score: Optional[int] = Field(None, ge=0, le=120)
    
    # Fit factors
    campus_vibe: Optional[CampusVibe] = None
    is_student_athlete: Optional[bool] = None
    has_legacy_status: Optional[bool] = None
    legacy_universities: Optional[List[str]] = None
    post_grad_goal: Optional[PostGradGoal] = None

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
    
    # Core identification
    citizenship_status: Optional[CitizenshipStatus] = None
    nationality: Optional[str] = None
    
    # Academic metrics
    gpa: float
    major: str
    sat_score: Optional[int] = None
    act_score: Optional[int] = None
    
    # US-specific fields
    state_of_residence: Optional[str] = None
    
    # Financial info
    household_income_tier: Optional[HouseholdIncomeTier] = None
    
    # International-specific
    english_proficiency_score: Optional[int] = None
    
    # Fit factors
    campus_vibe: Optional[CampusVibe] = None
    is_student_athlete: bool = False
    has_legacy_status: bool = False
    legacy_universities: Optional[List[str]] = None
    post_grad_goal: Optional[PostGradGoal] = None
    
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
