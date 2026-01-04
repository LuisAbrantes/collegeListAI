"""
College List API Routes

Endpoints for managing user's college list and exclusions.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel

from app.infrastructure.db.database import get_session
from app.infrastructure.db.repositories.user_college_list_repository import (
    UserCollegeListRepository,
    UserExclusionRepository,
)
from app.infrastructure.db.models.user_college_list import (
    UserCollegeListItemCreate,
    UserCollegeListItemUpdate,
    UserExclusionCreate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["college-list"])


# =============================================================================
# Auth Dependency
# =============================================================================

async def get_current_user_id(
    authorization: Optional[str] = Header(None)
) -> UUID:
    """
    Extract user ID from authorization header.
    
    In production, validates Supabase JWT token.
    For development, expects Bearer <user_id>.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization scheme")
        return UUID(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization token")


# =============================================================================
# Request/Response Schemas
# =============================================================================

class AddToListRequest(BaseModel):
    college_name: str
    label: Optional[str] = None  # reach, target, safety
    notes: Optional[str] = None


class UpdateListItemRequest(BaseModel):
    label: Optional[str] = None
    notes: Optional[str] = None


class CollegeListItemResponse(BaseModel):
    id: UUID
    college_name: str
    label: Optional[str]
    notes: Optional[str]
    added_at: str


class ExcludeRequest(BaseModel):
    college_name: str
    reason: Optional[str] = None


class ExclusionResponse(BaseModel):
    id: UUID
    college_name: str
    reason: Optional[str]
    created_at: str


# =============================================================================
# College List Endpoints
# =============================================================================

@router.get("/college-list", response_model=List[CollegeListItemResponse])
async def get_college_list(
    user_id: UUID = Depends(get_current_user_id),
    session = Depends(get_session),
):
    """Get user's saved college list."""
    repo = UserCollegeListRepository(session)
    items = await repo.get_all(user_id)
    
    return [
        CollegeListItemResponse(
            id=item.id,
            college_name=item.college_name,
            label=item.label,
            notes=item.notes,
            added_at=item.added_at.isoformat(),
        )
        for item in items
    ]


@router.post("/college-list", response_model=CollegeListItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_college_list(
    request: AddToListRequest,
    user_id: UUID = Depends(get_current_user_id),
    session = Depends(get_session),
):
    """Add a college to user's list."""
    repo = UserCollegeListRepository(session)
    
    item = await repo.add(
        user_id=user_id,
        data=UserCollegeListItemCreate(
            college_name=request.college_name,
            label=request.label,
            notes=request.notes,
        )
    )
    await session.commit()
    
    logger.info(f"User {user_id} added {request.college_name} to list")
    
    return CollegeListItemResponse(
        id=item.id,
        college_name=item.college_name,
        label=item.label,
        notes=item.notes,
        added_at=item.added_at.isoformat(),
    )


@router.patch("/college-list/{college_name}", response_model=CollegeListItemResponse)
async def update_college_list_item(
    college_name: str,
    request: UpdateListItemRequest,
    user_id: UUID = Depends(get_current_user_id),
    session = Depends(get_session),
):
    """Update a college list item (label, notes)."""
    repo = UserCollegeListRepository(session)
    
    item = await repo.update(
        user_id=user_id,
        college_name=college_name,
        data=UserCollegeListItemUpdate(
            label=request.label,
            notes=request.notes,
        )
    )
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"'{college_name}' not found in your list"
        )
    
    await session.commit()
    
    return CollegeListItemResponse(
        id=item.id,
        college_name=item.college_name,
        label=item.label,
        notes=item.notes,
        added_at=item.added_at.isoformat(),
    )


@router.delete("/college-list/{college_name}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_college_list(
    college_name: str,
    user_id: UUID = Depends(get_current_user_id),
    session = Depends(get_session),
):
    """Remove a college from user's list."""
    repo = UserCollegeListRepository(session)
    removed = await repo.remove(user_id, college_name)
    
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"'{college_name}' not found in your list"
        )
    
    await session.commit()
    logger.info(f"User {user_id} removed {college_name} from list")


# =============================================================================
# Exclusion Endpoints
# =============================================================================

@router.get("/exclusions", response_model=List[ExclusionResponse])
async def get_exclusions(
    user_id: UUID = Depends(get_current_user_id),
    session = Depends(get_session),
):
    """Get user's excluded colleges."""
    repo = UserExclusionRepository(session)
    exclusions = await repo.get_all(user_id)
    
    return [
        ExclusionResponse(
            id=exc.id,
            college_name=exc.college_name,
            reason=exc.reason,
            created_at=exc.created_at.isoformat(),
        )
        for exc in exclusions
    ]


@router.post("/exclusions", response_model=ExclusionResponse, status_code=status.HTTP_201_CREATED)
async def exclude_college(
    request: ExcludeRequest,
    user_id: UUID = Depends(get_current_user_id),
    session = Depends(get_session),
):
    """Exclude a college from future recommendations."""
    repo = UserExclusionRepository(session)
    
    exclusion = await repo.add(
        user_id=user_id,
        data=UserExclusionCreate(
            college_name=request.college_name,
            reason=request.reason,
        )
    )
    await session.commit()
    
    logger.info(f"User {user_id} excluded {request.college_name}")
    
    return ExclusionResponse(
        id=exclusion.id,
        college_name=exclusion.college_name,
        reason=exclusion.reason,
        created_at=exclusion.created_at.isoformat(),
    )


@router.delete("/exclusions/{college_name}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_exclusion(
    college_name: str,
    user_id: UUID = Depends(get_current_user_id),
    session = Depends(get_session),
):
    """Remove an exclusion (un-exclude a college)."""
    repo = UserExclusionRepository(session)
    removed = await repo.remove(user_id, college_name)
    
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"'{college_name}' is not in your exclusions"
        )
    
    await session.commit()
    logger.info(f"User {user_id} un-excluded {college_name}")
