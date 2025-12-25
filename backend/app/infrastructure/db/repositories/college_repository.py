"""
College Repository for College List AI

Specialized repository for Smart Sourcing RAG Pipeline.
Handles cache queries with staleness detection and major-segmented storage.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.college import (
    College,
    CollegeCreate,
)
from app.infrastructure.db.repositories.base_repository import BaseRepository
from sqlmodel import SQLModel


# Staleness threshold: 30 days
STALENESS_DAYS = 30


class CollegeUpdate(SQLModel):
    """Update schema for College."""
    name: Optional[str] = None
    target_major: Optional[str] = None
    content: Optional[str] = None
    acceptance_rate: Optional[float] = None
    median_gpa: Optional[float] = None
    sat_25th: Optional[int] = None
    sat_75th: Optional[int] = None
    need_blind_international: Optional[bool] = None
    meets_full_need: Optional[bool] = None
    major_strength: Optional[int] = None
    campus_setting: Optional[str] = None
    data_source: Optional[str] = None


class CollegeRepository(
    BaseRepository[College, CollegeCreate, CollegeUpdate]
):
    """
    Repository for College cache operations.
    
    Supports Smart Sourcing RAG Pipeline with Major-Segmented Cache:
    - Staleness detection (30 days)
    - Cache-first queries filtered by target_major
    - Auto-population upserts by (name, target_major) composite key
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(College, session)
    
    async def get_by_name(self, name: str, target_major: str = "general") -> Optional[College]:
        """
        Get a college by its name and target major (composite key).
        
        Args:
            name: University name
            target_major: Target major (defaults to 'general')
        """
        stmt = select(College).where(
            and_(
                College.name == name,
                College.target_major == target_major
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_name_any_major(self, name: str) -> List[College]:
        """
        Get all cache entries for a college across all majors.
        
        Useful for checking what majors we have cached for a university.
        """
        stmt = select(College).where(College.name == name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def search_by_name(
        self,
        search_term: str,
        target_major: Optional[str] = None,
        limit: int = 10
    ) -> List[College]:
        """
        Search colleges by name (case-insensitive).
        
        Args:
            search_term: Search term for name matching
            target_major: Optional filter by target major
            limit: Max results
        """
        conditions = [College.name.ilike(f"%{search_term}%")]
        
        if target_major:
            conditions.append(College.target_major == target_major)
        
        stmt = (
            select(College)
            .where(and_(*conditions))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_fresh_colleges(
        self,
        target_major: str,
        limit: int = 50
    ) -> List[College]:
        """
        Get colleges with fresh data (updated within STALENESS_DAYS) for a specific major.
        
        Phase 1 of RAG Pipeline: Check cache first.
        
        Args:
            target_major: Filter by this target major
            limit: Max results
        """
        threshold = datetime.utcnow() - timedelta(days=STALENESS_DAYS)
        stmt = (
            select(College)
            .where(and_(
                College.updated_at >= threshold,
                College.target_major == target_major
            ))
            .order_by(College.updated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_stale_colleges(
        self,
        target_major: Optional[str] = None,
        limit: int = 100
    ) -> List[College]:
        """
        Get colleges with stale data needing refresh.
        
        Args:
            target_major: Optional filter by major
            limit: Max results
        """
        threshold = datetime.utcnow() - timedelta(days=STALENESS_DAYS)
        
        conditions = [College.updated_at < threshold]
        if target_major:
            conditions.append(College.target_major == target_major)
        
        stmt = (
            select(College)
            .where(and_(*conditions))
            .order_by(College.updated_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def count_fresh(self, target_major: str) -> int:
        """
        Count colleges with fresh data for a specific major.
        
        Args:
            target_major: Filter by this target major
        """
        from sqlalchemy import func
        threshold = datetime.utcnow() - timedelta(days=STALENESS_DAYS)
        stmt = select(func.count()).select_from(College).where(
            and_(
                College.updated_at >= threshold,
                College.target_major == target_major
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_fresh_colleges_smart(
        self,
        current_provider: str,
        target_major: str,
        limit: int = 50
    ) -> List[College]:
        """
        Get fresh colleges with Smart Correction for a specific major.
        
        If current_provider is 'gemini', treat 'ollama_simulated' 
        data as stale regardless of updated_at.
        
        Args:
            current_provider: 'gemini' or 'ollama'
            target_major: Filter by this target major
            limit: Max results
        """
        threshold = datetime.utcnow() - timedelta(days=STALENESS_DAYS)
        
        # Base conditions: fresh + matching major
        base_conditions = [
            College.updated_at >= threshold,
            College.target_major == target_major
        ]
        
        if current_provider == "gemini":
            # Exclude ollama_simulated data even if "fresh"
            stmt = (
                select(College)
                .where(and_(
                    *base_conditions,
                    or_(
                        College.data_source != "ollama_simulated",
                        College.data_source.is_(None)
                    )
                ))
                .order_by(College.updated_at.desc())
                .limit(limit)
            )
        else:
            # Normal freshness check
            stmt = (
                select(College)
                .where(and_(*base_conditions))
                .order_by(College.updated_at.desc())
                .limit(limit)
            )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def count_fresh_smart(self, current_provider: str, target_major: str) -> int:
        """
        Count fresh colleges with Smart Correction for a specific major.
        
        Args:
            current_provider: 'gemini' or 'ollama'
            target_major: Filter by this target major
        """
        from sqlalchemy import func
        threshold = datetime.utcnow() - timedelta(days=STALENESS_DAYS)
        
        # Base conditions: fresh + matching major
        base_conditions = [
            College.updated_at >= threshold,
            College.target_major == target_major
        ]
        
        if current_provider == "gemini":
            stmt = select(func.count()).select_from(College).where(and_(
                *base_conditions,
                or_(
                    College.data_source != "ollama_simulated",
                    College.data_source.is_(None)
                )
            ))
        else:
            stmt = select(func.count()).select_from(College).where(
                and_(*base_conditions)
            )
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def upsert(self, data: CollegeCreate) -> College:
        """
        Insert or update a college by (name, target_major) composite key.
        
        Phase 3 of RAG Pipeline: Auto-populate cache.
        Updates timestamp to mark as fresh.
        
        IMPORTANT: Uses composite key - Physics data won't overwrite CS data.
        """
        existing = await self.get_by_name(data.name, data.target_major)
        
        if existing:
            # Update existing with new data
            for field in ['acceptance_rate', 'median_gpa', 'sat_25th', 'sat_75th',
                         'need_blind_international', 'meets_full_need', 'major_strength',
                         'campus_setting', 'data_source', 'content']:
                value = getattr(data, field, None)
                if value is not None:
                    setattr(existing, field, value)
            
            # Mark as fresh
            existing.updated_at = datetime.utcnow()
            
            self.session.add(existing)
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        else:
            # Create new
            return await self.create(data)
    
    async def bulk_upsert(self, colleges: List[CollegeCreate]) -> int:
        """
        Bulk upsert multiple colleges.
        
        Returns count of upserted records.
        """
        count = 0
        for college_data in colleges:
            await self.upsert(college_data)
            count += 1
        return count

