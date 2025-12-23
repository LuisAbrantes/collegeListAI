"""
Profile Routes

CRUD endpoints for user profiles (nationality, GPA, major).
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from app.domain.models import UserProfile, UserProfileCreate, UserProfileUpdate
from app.domain.services import UserProfileService
from app.infrastructure.exceptions import NotFoundError, DuplicateError


router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class ProfileCreateRequest(BaseModel):
    """Request to create a new profile."""
    nationality: str = Field(..., min_length=2, max_length=100)
    gpa: float = Field(..., ge=0.0, le=4.0)
    major: str = Field(..., min_length=2, max_length=100)


class ProfileUpdateRequest(BaseModel):
    """Request to update an existing profile."""
    nationality: Optional[str] = Field(None, min_length=2, max_length=100)
    gpa: Optional[float] = Field(None, ge=0.0, le=4.0)
    major: Optional[str] = Field(None, min_length=2, max_length=100)


class ProfileResponse(BaseModel):
    """Profile response model."""
    id: str
    user_id: str
    nationality: str
    gpa: float
    major: str
    created_at: str
    updated_at: str


# ============================================================================
# Dependency Injection
# ============================================================================

def get_profile_service() -> UserProfileService:
    """Get profile service instance."""
    return UserProfileService()


async def get_current_user_id(
    authorization: Optional[str] = Header(None)
) -> UUID:
    """
    Extract user ID from authorization header.
    
    In production, this would validate a Supabase JWT token.
    For now, we expect the user_id to be passed directly.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    # In production: validate JWT and extract user_id from claims
    # For development: expect Bearer <user_id>
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization scheme")
        return UUID(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization token")


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/profiles/me", response_model=ProfileResponse)
async def get_current_profile(
    user_id: UUID = Depends(get_current_user_id),
    service: UserProfileService = Depends(get_profile_service)
):
    """Get the current user's profile."""
    try:
        profile = await service.get_profile(user_id)
        return ProfileResponse(
            id=str(profile.id),
            user_id=str(profile.user_id),
            nationality=profile.nationality,
            gpa=profile.gpa,
            major=profile.major,
            created_at=profile.created_at.isoformat(),
            updated_at=profile.updated_at.isoformat(),
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/profiles", response_model=ProfileResponse, status_code=201)
async def create_profile(
    request: ProfileCreateRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: UserProfileService = Depends(get_profile_service)
):
    """Create a new profile for the current user."""
    try:
        data = UserProfileCreate(
            nationality=request.nationality,
            gpa=request.gpa,
            major=request.major,
        )
        profile = await service.create_profile(user_id, data)
        return ProfileResponse(
            id=str(profile.id),
            user_id=str(profile.user_id),
            nationality=profile.nationality,
            gpa=profile.gpa,
            major=profile.major,
            created_at=profile.created_at.isoformat(),
            updated_at=profile.updated_at.isoformat(),
        )
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.patch("/profiles/me", response_model=ProfileResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: UserProfileService = Depends(get_profile_service)
):
    """Update the current user's profile."""
    try:
        data = UserProfileUpdate(
            nationality=request.nationality,
            gpa=request.gpa,
            major=request.major,
        )
        profile = await service.update_profile(user_id, data)
        return ProfileResponse(
            id=str(profile.id),
            user_id=str(profile.user_id),
            nationality=profile.nationality,
            gpa=profile.gpa,
            major=profile.major,
            created_at=profile.created_at.isoformat(),
            updated_at=profile.updated_at.isoformat(),
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/profiles/me", status_code=204)
async def delete_profile(
    user_id: UUID = Depends(get_current_user_id),
    service: UserProfileService = Depends(get_profile_service)
):
    """Delete the current user's profile."""
    try:
        await service.delete_profile(user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
