"""
College Repository for College List AI

Specialized repository for college cache operations.
Note: Vector/embedding operations remain in VectorService.
"""

from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.college import (
    College,
    CollegeCreate,
)
from app.infrastructure.db.repositories.base_repository import BaseRepository
from sqlmodel import SQLModel


class CollegeUpdate(SQLModel):
    """Update schema for College (minimal fields)."""
    name: Optional[str] = None
    content: Optional[str] = None


class CollegeRepository(
    BaseRepository[College, CollegeCreate, CollegeUpdate]
):
    """
    Repository for College cache operations.
    
    Handles basic CRUD for college cache entries.
    Vector/similarity operations remain in VectorService.
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(College, session)
    
    async def get_by_name(self, name: str) -> Optional[College]:
        """
        Get a college by its name.
        
        Args:
            name: University name
            
        Returns:
            College or None if not found
        """
        stmt = select(College).where(College.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def search_by_name(
        self,
        search_term: str,
        limit: int = 10
    ) -> List[College]:
        """
        Search colleges by name (case-insensitive).
        
        Args:
            search_term: Partial name to search
            limit: Max results
            
        Returns:
            List of matching colleges
        """
        stmt = (
            select(College)
            .where(College.name.ilike(f"%{search_term}%"))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def upsert(self, data: CollegeCreate) -> College:
        """
        Insert or update a college by name.
        
        Args:
            data: College data
            
        Returns:
            Created or updated College
        """
        existing = await self.get_by_name(data.name)
        
        if existing:
            # Update existing
            if data.content:
                existing.content = data.content
            self.session.add(existing)
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        else:
            # Create new
            return await self.create(data)
