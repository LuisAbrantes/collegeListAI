"""
Analytics Service

High-level service for tracking user behavior and outcomes.
Follows Single Responsibility - only handles analytics concerns.
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.user_event_repository import UserEventRepository
from app.infrastructure.db.repositories.application_outcome_repository import (
    ApplicationOutcomeRepository,
)
from app.infrastructure.db.models.user_event import UserEventCreate, UserEventType
from app.infrastructure.db.models.application_outcome import (
    ApplicationOutcomeCreate,
    OutcomeStatus,
)


logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service for tracking user behavior and admission outcomes.
    
    Provides high-level methods for event tracking and outcome recording.
    Repositories handle the actual data access.
    """
    
    def __init__(self, session: AsyncSession):
        self._event_repo = UserEventRepository(session)
        self._outcome_repo = ApplicationOutcomeRepository(session)
    
    # =========================================================================
    # Event Tracking
    # =========================================================================
    
    async def track_search(
        self,
        user_id: UUID,
        query: str,
        results_count: int,
        major: Optional[str] = None
    ) -> None:
        """Track when user executes a search."""
        event = UserEventCreate(
            user_id=user_id,
            event_type=UserEventType.SEARCH_EXECUTED,
            college_name=None,
            event_data={
                "query": query,
                "results_count": results_count,
                "major": major,
            }
        )
        await self._event_repo.create(event)
        logger.debug(f"[ANALYTICS] Tracked search: {query}")
    
    async def track_recommendation_view(
        self,
        user_id: UUID,
        college_name: str,
        position: int,
        label: Optional[str] = None
    ) -> None:
        """Track when user views a recommendation."""
        event = UserEventCreate(
            user_id=user_id,
            event_type=UserEventType.RECOMMENDATION_VIEWED,
            college_name=college_name,
            event_data={
                "position": position,
                "label": label,
            }
        )
        await self._event_repo.create(event)
    
    async def track_list_add(
        self,
        user_id: UUID,
        college_name: str,
        label: Optional[str] = None
    ) -> None:
        """Track when user adds a college to their list."""
        event = UserEventCreate(
            user_id=user_id,
            event_type=UserEventType.RECOMMENDATION_ADDED,
            college_name=college_name,
            event_data={"label": label}
        )
        await self._event_repo.create(event)
        logger.debug(f"[ANALYTICS] Tracked list add: {college_name}")
    
    async def track_rejection(
        self,
        user_id: UUID,
        college_name: str,
        reason: Optional[str] = None
    ) -> None:
        """Track when user explicitly rejects a recommendation."""
        event = UserEventCreate(
            user_id=user_id,
            event_type=UserEventType.RECOMMENDATION_REJECTED,
            college_name=college_name,
            event_data={"reason": reason}
        )
        await self._event_repo.create(event)
    
    async def track_college_expanded(
        self,
        user_id: UUID,
        college_name: str,
        time_spent_ms: Optional[int] = None
    ) -> None:
        """Track when user expands college details."""
        event = UserEventCreate(
            user_id=user_id,
            event_type=UserEventType.COLLEGE_INFO_EXPANDED,
            college_name=college_name,
            event_data={"time_spent_ms": time_spent_ms}
        )
        await self._event_repo.create(event)
    
    # =========================================================================
    # Outcome Recording
    # =========================================================================
    
    async def record_outcome(
        self,
        user_id: UUID,
        college_name: str,
        outcome_status: OutcomeStatus,
        cycle_year: int,
        predicted_label: Optional[str] = None
    ) -> None:
        """Record an application outcome (creates or updates)."""
        outcome = ApplicationOutcomeCreate(
            user_id=user_id,
            college_name=college_name,
            outcome_status=outcome_status,
            cycle_year=cycle_year,
            predicted_label=predicted_label,
        )
        await self._outcome_repo.upsert(user_id, college_name, outcome)
        logger.info(f"[ANALYTICS] Recorded outcome: {college_name} = {outcome_status}")
    
    async def get_user_outcomes(self, user_id: UUID) -> list:
        """Get all outcomes for a user."""
        return await self._outcome_repo.get_by_user(user_id)
    
    # =========================================================================
    # Analytics Queries
    # =========================================================================
    
    async def get_label_accuracy(self, cycle_year: Optional[int] = None) -> Dict[str, Any]:
        """Get prediction accuracy for Reach/Target/Safety labels."""
        return await self._outcome_repo.get_label_accuracy(cycle_year)
    
    async def get_user_event_counts(self, user_id: UUID) -> Dict[str, int]:
        """Get event counts by type for a user."""
        return await self._event_repo.count_by_type(user_id)
