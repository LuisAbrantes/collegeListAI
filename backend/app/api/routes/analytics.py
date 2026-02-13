"""
Analytics API Routes

Endpoints for tracking user behavior and recording outcomes.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.dependencies import get_session
from app.infrastructure.services.analytics_service import AnalyticsService
from app.infrastructure.db.models.application_outcome import OutcomeStatus
from app.api.dependencies import get_current_user_id as _get_current_user_str


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


# =============================================================================
# Auth Dependency — delegates to centralized JWT verification
# =============================================================================

async def get_current_user_id(
    user_id_str: str = Depends(_get_current_user_str),
) -> UUID:
    """Convert verified JWT user_id (str) to UUID for downstream repos."""
    return UUID(user_id_str)


# =============================================================================
# Request/Response Schemas
# =============================================================================

class TrackSearchRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    results_count: int = Field(..., ge=0, description="Number of results returned")
    major: Optional[str] = Field(None, description="Major searched for")


class TrackViewRequest(BaseModel):
    college_name: str = Field(..., description="College that was viewed")
    position: int = Field(..., ge=0, description="Position in results list")
    label: Optional[str] = Field(None, description="Reach/Target/Safety label")


class TrackListActionRequest(BaseModel):
    college_name: str = Field(..., description="College added to list")
    label: Optional[str] = Field(None, description="Label assigned")


class TrackRejectionRequest(BaseModel):
    college_name: str = Field(..., description="College rejected")
    reason: Optional[str] = Field(None, description="Optional rejection reason")


class RecordOutcomeRequest(BaseModel):
    college_name: str = Field(..., description="College applied to")
    outcome_status: OutcomeStatus = Field(..., description="Admission result")
    cycle_year: int = Field(..., ge=2020, le=2030, description="Admission cycle year")
    predicted_label: Optional[str] = Field(None, description="Original AI prediction")


class OutcomeResponse(BaseModel):
    id: UUID
    college_name: str
    outcome_status: str
    cycle_year: int
    predicted_label: Optional[str]
    created_at: datetime


# =============================================================================
# Event Tracking Endpoints
# =============================================================================

@router.post("/track/search", status_code=status.HTTP_204_NO_CONTENT)
async def track_search(
    request: TrackSearchRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Track a search event."""
    try:
        service = AnalyticsService(session)
        await service.track_search(
            user_id=user_id,
            query=request.query,
            results_count=request.results_count,
            major=request.major,
        )
        await session.commit()
    except Exception as e:
        logger.error(f"Failed to track search event: {e}")
        await session.rollback()
        # Analytics should not block user experience - fail silently
        return


@router.post("/track/view", status_code=status.HTTP_204_NO_CONTENT)
async def track_view(
    request: TrackViewRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Track when user views a recommendation."""
    try:
        service = AnalyticsService(session)
        await service.track_recommendation_view(
            user_id=user_id,
            college_name=request.college_name,
            position=request.position,
            label=request.label,
        )
        await session.commit()
    except Exception as e:
        logger.error(f"Failed to track view event: {e}")
        await session.rollback()


@router.post("/track/add", status_code=status.HTTP_204_NO_CONTENT)
async def track_list_add(
    request: TrackListActionRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Track when user adds a college to their list."""
    try:
        service = AnalyticsService(session)
        await service.track_list_add(
            user_id=user_id,
            college_name=request.college_name,
            label=request.label,
        )
        await session.commit()
    except Exception as e:
        logger.error(f"Failed to track add event: {e}")
        await session.rollback()


@router.post("/track/reject", status_code=status.HTTP_204_NO_CONTENT)
async def track_rejection(
    request: TrackRejectionRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Track when user rejects a recommendation."""
    try:
        service = AnalyticsService(session)
        await service.track_rejection(
            user_id=user_id,
            college_name=request.college_name,
            reason=request.reason,
        )
        await session.commit()
    except Exception as e:
        logger.error(f"Failed to track rejection event: {e}")
        await session.rollback()


# =============================================================================
# Outcome Endpoints
# =============================================================================

@router.post("/outcomes", status_code=status.HTTP_201_CREATED)
async def record_outcome(
    request: RecordOutcomeRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Record an application outcome."""
    service = AnalyticsService(session)
    await service.record_outcome(
        user_id=user_id,
        college_name=request.college_name,
        outcome_status=request.outcome_status,
        cycle_year=request.cycle_year,
        predicted_label=request.predicted_label,
    )
    await session.commit()
    return {"message": "Outcome recorded successfully"}


@router.get("/outcomes")
async def get_my_outcomes(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Get user's recorded outcomes."""
    service = AnalyticsService(session)
    outcomes = await service.get_user_outcomes(user_id)
    return [
        OutcomeResponse(
            id=o.id,
            college_name=o.college_name,
            outcome_status=o.outcome_status.value,
            cycle_year=o.cycle_year,
            predicted_label=o.predicted_label,
            created_at=o.created_at,
        )
        for o in outcomes
    ]


@router.get("/stats")
async def get_event_stats(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Get user's event statistics."""
    service = AnalyticsService(session)
    counts = await service.get_user_event_counts(user_id)
    return {"event_counts": counts}
