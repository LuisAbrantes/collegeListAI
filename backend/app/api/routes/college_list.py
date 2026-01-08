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
    """Add a college to user's list with auto-calculated label."""
    try:
        from app.infrastructure.db.repositories.college_repository import CollegeRepository
        
        repo = UserCollegeListRepository(session)
        
        # Auto-calculate label based on acceptance rate if not provided
        calculated_label = request.label
        
        if not calculated_label:
            try:
                college_repo = CollegeRepository(session)
                acceptance_rate = None
                
                # Get college data
                college = await college_repo.get_by_name(request.college_name)
                if not college:
                    colleges = await college_repo.search_by_name(request.college_name, limit=1)
                    if colleges:
                        college = colleges[0]
                
                # Try to get acceptance rate from local data
                if college and hasattr(college, 'acceptance_rate') and college.acceptance_rate:
                    acceptance_rate = college.acceptance_rate
                
                # If no local data, fetch from College Scorecard
                if not acceptance_rate:
                    try:
                        from app.infrastructure.services.college_scorecard_service import CollegeScorecardService
                        scorecard = CollegeScorecardService()
                        scorecard_data = await scorecard.search_by_name(request.college_name)
                        if scorecard_data and scorecard_data.acceptance_rate:
                            acceptance_rate = scorecard_data.acceptance_rate
                            logger.info(f"Fetched acceptance rate from Scorecard: {acceptance_rate:.0%}")
                    except Exception as sc_error:
                        logger.warning(f"Scorecard lookup failed: {sc_error}")
                
                # Fallback to known rates for popular universities
                if not acceptance_rate:
                    import re
                    FALLBACK_RATES = {
                        "berkeley": 0.12, "uc berkeley": 0.12, "university of california-berkeley": 0.12,
                        "ucla": 0.09, "university of california-los angeles": 0.09,
                        "uc san diego": 0.24, "ucsd": 0.24, "university of california-san diego": 0.24,
                        "uc davis": 0.37, "university of california-davis": 0.37,
                        "uc irvine": 0.21, "university of california-irvine": 0.21,
                        "uc santa barbara": 0.26, "university of california-santa barbara": 0.26,
                        "uc santa cruz": 0.47, "university of california-santa cruz": 0.47,
                        "uc riverside": 0.66, "university of california-riverside": 0.66,
                        "uc merced": 0.89, "university of california-merced": 0.89,
                        "purdue university-main campus": 0.50, "purdue university": 0.50,
                        "purdue university fort wayne": 0.86, "purdue university northwest": 0.71,
                        "mit": 0.04, "stanford university": 0.04, "harvard university": 0.03,
                    }
                    name_lower = request.college_name.lower().strip()
                    name_normalized = re.sub(r'\s*\([^)]*\)', '', name_lower).strip()
                    
                    acceptance_rate = FALLBACK_RATES.get(name_lower) or FALLBACK_RATES.get(name_normalized)
                    if not acceptance_rate:
                        for key in FALLBACK_RATES:
                            if key in name_lower or name_lower in key:
                                acceptance_rate = FALLBACK_RATES[key]
                                break
                    if acceptance_rate:
                        logger.info(f"Using fallback rate for {request.college_name}: {acceptance_rate:.0%}")
                
                # Calculate label based on acceptance rate
                if acceptance_rate:
                    if acceptance_rate < 0.20:
                        calculated_label = "reach"
                    elif acceptance_rate > 0.70:
                        calculated_label = "safety"
                    else:
                        calculated_label = "target"
                    logger.info(f"Auto-calculated label for {request.college_name}: {calculated_label} (acceptance: {acceptance_rate:.0%})")
            except Exception as label_error:
                logger.warning(f"Could not auto-calculate label: {label_error}")
                await session.rollback()
                # Recreate repo after rollback
                repo = UserCollegeListRepository(session)
        
        item = await repo.add(
            user_id=user_id,
            data=UserCollegeListItemCreate(
                college_name=request.college_name,
                label=calculated_label,
                notes=request.notes,
            )
        )
        await session.commit()
        
        logger.info(f"User {user_id} added {request.college_name} to list as {calculated_label}")
        
        return CollegeListItemResponse(
            id=item.id,
            college_name=item.college_name,
            label=item.label,
            notes=item.notes,
            added_at=item.added_at.isoformat(),
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Error adding college to list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
