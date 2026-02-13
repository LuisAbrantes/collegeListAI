"""
Profile Routes

CRUD endpoints for user profiles (nationality, GPA, major, citizenship, etc.).
Uses SQLAlchemy UserProfileRepository via FastAPI dependency injection.
"""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.domain.models import (
    CitizenshipStatus,
    HouseholdIncomeTier,
    CampusVibe,
    PostGradGoal,
    UserProfileCreate,
    UserProfileUpdate,
)
from app.infrastructure.exceptions import NotFoundError, DuplicateError
from app.api.dependencies import get_current_user_id as _get_current_user_str
from app.infrastructure.db.dependencies import UserProfileRepoDep


router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class ProfileCreateRequest(BaseModel):
    """Request to create a new profile."""
    # Core identification
    citizenship_status: CitizenshipStatus = Field(
        ..., description="Student citizenship/residency status"
    )
    nationality: Optional[str] = Field(
        None, min_length=2, max_length=100, description="Country of citizenship"
    )

    # Academic metrics
    gpa: float = Field(..., ge=0.0, le=4.0, description="GPA on 4.0 scale")
    major: str = Field(
        ..., min_length=2, max_length=100, description="Intended major"
    )
    sat_score: Optional[int] = Field(None, ge=400, le=1600)
    act_score: Optional[int] = Field(None, ge=1, le=36)

    # US-specific
    state_of_residence: Optional[str] = Field(None, max_length=50)

    # Financial
    household_income_tier: Optional[HouseholdIncomeTier] = None

    # International-specific
    english_proficiency_score: Optional[int] = Field(None, ge=0, le=120)

    # Fit factors
    campus_vibe: Optional[CampusVibe] = None
    is_student_athlete: bool = False
    has_legacy_status: bool = False
    legacy_universities: Optional[List[str]] = None
    post_grad_goal: Optional[PostGradGoal] = None


class ProfileUpdateRequest(BaseModel):
    """Request to update an existing profile (all fields optional)."""
    citizenship_status: Optional[CitizenshipStatus] = None
    nationality: Optional[str] = Field(None, min_length=2, max_length=100)
    gpa: Optional[float] = Field(None, ge=0.0, le=4.0)
    major: Optional[str] = Field(None, min_length=2, max_length=100)
    sat_score: Optional[int] = Field(None, ge=400, le=1600)
    act_score: Optional[int] = Field(None, ge=1, le=36)
    state_of_residence: Optional[str] = Field(None, max_length=50)
    household_income_tier: Optional[HouseholdIncomeTier] = None
    english_proficiency_score: Optional[int] = Field(None, ge=0, le=120)
    campus_vibe: Optional[CampusVibe] = None
    is_student_athlete: Optional[bool] = None
    has_legacy_status: Optional[bool] = None
    legacy_universities: Optional[List[str]] = None
    post_grad_goal: Optional[PostGradGoal] = None


class ProfileResponse(BaseModel):
    """Profile response model."""
    id: str
    user_id: str

    # Core identification
    citizenship_status: Optional[str] = None
    nationality: Optional[str] = None

    # Academic metrics
    gpa: float
    major: str
    sat_score: Optional[int] = None
    act_score: Optional[int] = None

    # US-specific
    state_of_residence: Optional[str] = None

    # Financial
    household_income_tier: Optional[str] = None

    # International-specific
    english_proficiency_score: Optional[int] = None

    # Fit factors
    campus_vibe: Optional[str] = None
    is_student_athlete: bool = False
    has_legacy_status: bool = False
    legacy_universities: Optional[List[str]] = None
    post_grad_goal: Optional[str] = None

    # Timestamps
    created_at: str
    updated_at: str


# ============================================================================
# Dependency Injection
# ============================================================================

async def get_current_user_id(
    user_id_str: str = Depends(_get_current_user_str),
) -> UUID:
    """Convert verified JWT user_id (str) to UUID for downstream repos."""
    return UUID(user_id_str)


# ============================================================================
# Helper
# ============================================================================

def _profile_to_response(profile) -> ProfileResponse:
    """Convert a UserProfile ORM object to a ProfileResponse."""
    return ProfileResponse(
        id=str(profile.id),
        user_id=str(profile.user_id),
        citizenship_status=profile.citizenship_status.value if profile.citizenship_status else None,
        nationality=profile.nationality,
        gpa=profile.gpa,
        major=profile.major,
        sat_score=profile.sat_score,
        act_score=profile.act_score,
        state_of_residence=profile.state_of_residence,
        household_income_tier=profile.household_income_tier.value if profile.household_income_tier else None,
        english_proficiency_score=profile.english_proficiency_score,
        campus_vibe=profile.campus_vibe.value if profile.campus_vibe else None,
        is_student_athlete=profile.is_student_athlete,
        has_legacy_status=profile.has_legacy_status,
        legacy_universities=profile.legacy_universities,
        post_grad_goal=profile.post_grad_goal.value if profile.post_grad_goal else None,
        created_at=profile.created_at.isoformat() if profile.created_at else "",
        updated_at=profile.updated_at.isoformat() if profile.updated_at else "",
    )


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/profiles/me", response_model=ProfileResponse)
async def get_current_profile(
    user_id: UUID = Depends(get_current_user_id),
    repo: UserProfileRepoDep = None,
):
    """Get the current user's profile."""
    profile = await repo.get_by_user_id(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"No profile found for user {user_id}")
    return _profile_to_response(profile)


@router.post("/profiles", response_model=ProfileResponse, status_code=201)
async def create_profile(
    request: ProfileCreateRequest,
    user_id: UUID = Depends(get_current_user_id),
    repo: UserProfileRepoDep = None,
):
    """Create a new profile for the current user."""
    # Check for existing profile
    existing = await repo.get_by_user_id(user_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Profile already exists for user {user_id}")

    from app.infrastructure.db.models.user_profile import UserProfileCreate as DBProfileCreate

    data = DBProfileCreate(**request.model_dump())
    profile = await repo.create_for_user(user_id, data)
    return _profile_to_response(profile)


@router.patch("/profiles/me", response_model=ProfileResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    user_id: UUID = Depends(get_current_user_id),
    repo: UserProfileRepoDep = None,
):
    """Update the current user's profile."""
    from app.infrastructure.db.models.user_profile import UserProfileUpdate as DBProfileUpdate

    data = DBProfileUpdate(**request.model_dump(exclude_unset=True))
    profile = await repo.update_by_user_id(user_id, data)
    if not profile:
        raise HTTPException(status_code=404, detail=f"No profile found for user {user_id}")
    return _profile_to_response(profile)


@router.delete("/profiles/me", status_code=204)
async def delete_profile(
    user_id: UUID = Depends(get_current_user_id),
    repo: UserProfileRepoDep = None,
):
    """Delete the current user's profile."""
    deleted = await repo.delete_by_user_id(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No profile found for user {user_id}")
