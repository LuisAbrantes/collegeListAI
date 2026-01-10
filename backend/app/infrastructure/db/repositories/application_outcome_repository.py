"""
Application Outcome Repository

Extends BaseRepository with outcome-specific queries for ML training.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.base_repository import BaseRepository
from app.infrastructure.db.models.application_outcome import (
    ApplicationOutcome,
    ApplicationOutcomeCreate,
    ApplicationOutcomeUpdate,
    OutcomeStatus,
)


class ApplicationOutcomeRepository(
    BaseRepository[ApplicationOutcome, ApplicationOutcomeCreate, ApplicationOutcomeUpdate]
):
    """Repository for application outcomes."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(ApplicationOutcome, session)
    
    async def get_by_user(self, user_id: UUID) -> List[ApplicationOutcome]:
        """Get all outcomes for a user."""
        stmt = (
            select(ApplicationOutcome)
            .where(ApplicationOutcome.user_id == user_id)
            .order_by(ApplicationOutcome.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_college(self, college_name: str) -> List[ApplicationOutcome]:
        """Get all outcomes for a specific college (for accuracy analysis)."""
        stmt = (
            select(ApplicationOutcome)
            .where(ApplicationOutcome.college_name == college_name)
            .order_by(ApplicationOutcome.cycle_year.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_user_and_college(
        self,
        user_id: UUID,
        college_name: str
    ) -> Optional[ApplicationOutcome]:
        """Get specific outcome for user + college combination."""
        stmt = (
            select(ApplicationOutcome)
            .where(
                ApplicationOutcome.user_id == user_id,
                ApplicationOutcome.college_name == college_name
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def upsert(
        self,
        user_id: UUID,
        college_name: str,
        data: ApplicationOutcomeCreate
    ) -> ApplicationOutcome:
        """Create or update outcome for user + college."""
        existing = await self.get_by_user_and_college(user_id, college_name)
        
        if existing:
            existing.outcome_status = data.outcome_status
            existing.submitted_at = data.submitted_at
            existing.updated_at = datetime.utcnow()
            self._session.add(existing)
            await self._session.flush()
            await self._session.refresh(existing)
            return existing
        
        return await self.create(data)
    
    async def get_label_accuracy(self, cycle_year: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculate prediction accuracy for Reach/Target/Safety labels.
        
        Returns accuracy metrics for ML training validation.
        """
        conditions = [ApplicationOutcome.predicted_label.isnot(None)]
        if cycle_year:
            conditions.append(ApplicationOutcome.cycle_year == cycle_year)
        
        stmt = (
            select(
                ApplicationOutcome.predicted_label,
                ApplicationOutcome.outcome_status,
                func.count(ApplicationOutcome.id).label("count")
            )
            .where(and_(*conditions))
            .group_by(
                ApplicationOutcome.predicted_label,
                ApplicationOutcome.outcome_status
            )
        )
        result = await self._session.execute(stmt)
        rows = result.all()
        
        # Build accuracy matrix
        accuracy = {"reach": {}, "target": {}, "safety": {}}
        for row in rows:
            label = row.predicted_label.lower() if row.predicted_label else "unknown"
            if label in accuracy:
                accuracy[label][row.outcome_status] = row.count
        
        return accuracy
