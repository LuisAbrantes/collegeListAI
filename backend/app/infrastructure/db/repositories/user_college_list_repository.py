"""
Repositories for User College List and Exclusions

CRUD operations for:
- UserCollegeListRepository: Manage saved colleges
- UserExclusionRepository: Manage exclusions
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.user_college_list import (
    UserCollegeListItem,
    UserCollegeListItemCreate,
    UserCollegeListItemUpdate,
    UserExclusion,
    UserExclusionCreate,
)


class UserCollegeListRepository:
    """Repository for user's saved college list."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_all(self, user_id: UUID) -> List[UserCollegeListItem]:
        """Get all colleges in user's list."""
        stmt = (
            select(UserCollegeListItem)
            .where(UserCollegeListItem.user_id == user_id)
            .order_by(UserCollegeListItem.added_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_name(
        self, 
        user_id: UUID, 
        college_name: str
    ) -> Optional[UserCollegeListItem]:
        """Get a specific college from user's list."""
        stmt = select(UserCollegeListItem).where(and_(
            UserCollegeListItem.user_id == user_id,
            UserCollegeListItem.college_name.ilike(college_name)
        ))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def add(
        self, 
        user_id: UUID, 
        data: UserCollegeListItemCreate
    ) -> UserCollegeListItem:
        """Add a college to user's list."""
        # Check if already exists
        existing = await self.get_by_name(user_id, data.college_name)
        if existing:
            # Update existing entry
            if data.label:
                existing.label = data.label
            if data.notes:
                existing.notes = data.notes
            await self.session.flush()
            return existing
        
        # Create new entry
        item = UserCollegeListItem(
            user_id=user_id,
            college_name=data.college_name,
            label=data.label,
            notes=data.notes,
        )
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item
    
    async def update(
        self,
        user_id: UUID,
        college_name: str,
        data: UserCollegeListItemUpdate
    ) -> Optional[UserCollegeListItem]:
        """Update a college list item."""
        item = await self.get_by_name(user_id, college_name)
        if not item:
            return None
        
        if data.label is not None:
            item.label = data.label
        if data.notes is not None:
            item.notes = data.notes
        
        await self.session.flush()
        return item
    
    async def remove(self, user_id: UUID, college_name: str) -> bool:
        """Remove a college from user's list."""
        stmt = delete(UserCollegeListItem).where(and_(
            UserCollegeListItem.user_id == user_id,
            UserCollegeListItem.college_name.ilike(college_name)
        ))
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def count(self, user_id: UUID) -> int:
        """Count colleges in user's list."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(UserCollegeListItem).where(
            UserCollegeListItem.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0


class UserExclusionRepository:
    """Repository for user's excluded colleges."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_all(self, user_id: UUID) -> List[UserExclusion]:
        """Get all exclusions for user."""
        stmt = (
            select(UserExclusion)
            .where(UserExclusion.user_id == user_id)
            .order_by(UserExclusion.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_names(self, user_id: UUID) -> List[str]:
        """Get just the names of excluded colleges (for filtering)."""
        stmt = select(UserExclusion.college_name).where(
            UserExclusion.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]
    
    async def is_excluded(self, user_id: UUID, college_name: str) -> bool:
        """Check if a college is excluded."""
        stmt = select(UserExclusion).where(and_(
            UserExclusion.user_id == user_id,
            UserExclusion.college_name.ilike(college_name)
        ))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    async def add(
        self, 
        user_id: UUID, 
        data: UserExclusionCreate
    ) -> UserExclusion:
        """Add a college to exclusions."""
        # Check if already excluded
        is_excluded = await self.is_excluded(user_id, data.college_name)
        if is_excluded:
            # Return existing
            stmt = select(UserExclusion).where(and_(
                UserExclusion.user_id == user_id,
                UserExclusion.college_name.ilike(data.college_name)
            ))
            result = await self.session.execute(stmt)
            return result.scalar_one()
        
        # Create new exclusion
        exclusion = UserExclusion(
            user_id=user_id,
            college_name=data.college_name,
            reason=data.reason,
        )
        self.session.add(exclusion)
        await self.session.flush()
        await self.session.refresh(exclusion)
        return exclusion
    
    async def remove(self, user_id: UUID, college_name: str) -> bool:
        """Remove an exclusion (un-exclude a college)."""
        stmt = delete(UserExclusion).where(and_(
            UserExclusion.user_id == user_id,
            UserExclusion.college_name.ilike(college_name)
        ))
        result = await self.session.execute(stmt)
        return result.rowcount > 0
