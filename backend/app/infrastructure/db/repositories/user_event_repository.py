"""
User Event Repository

Extends BaseRepository with event-specific queries.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.base_repository import BaseRepository
from app.infrastructure.db.models.user_event import (
    UserEvent,
    UserEventCreate,
    UserEventType,
)


class UserEventRepository(BaseRepository[UserEvent, UserEventCreate, UserEventCreate]):
    """Repository for user behavior events."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(UserEvent, session)
    
    async def get_by_user(
        self,
        user_id: UUID,
        limit: int = 100
    ) -> List[UserEvent]:
        """Get events for a specific user."""
        stmt = (
            select(UserEvent)
            .where(UserEvent.user_id == user_id)
            .order_by(UserEvent.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_type(
        self,
        user_id: UUID,
        event_type: UserEventType
    ) -> List[UserEvent]:
        """Get events of a specific type for a user."""
        stmt = (
            select(UserEvent)
            .where(
                UserEvent.user_id == user_id,
                UserEvent.event_type == event_type
            )
            .order_by(UserEvent.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def count_by_type(self, user_id: UUID) -> Dict[str, int]:
        """Get event counts grouped by type for a user."""
        stmt = (
            select(
                UserEvent.event_type,
                func.count(UserEvent.id).label("count")
            )
            .where(UserEvent.user_id == user_id)
            .group_by(UserEvent.event_type)
        )
        result = await self._session.execute(stmt)
        return {row.event_type: row.count for row in result.all()}
    
    async def get_recent(
        self,
        hours: int = 24,
        limit: int = 1000
    ) -> List[UserEvent]:
        """Get recent events across all users (for analytics)."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = (
            select(UserEvent)
            .where(UserEvent.created_at >= since)
            .order_by(UserEvent.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
