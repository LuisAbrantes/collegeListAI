"""
College Repository for College List AI

Specialized repository for Smart Sourcing RAG Pipeline.
Handles cache queries with staleness detection.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, or_
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
    
    Supports Smart Sourcing RAG Pipeline:
    - Staleness detection (30 days)
    - Cache-first queries
    - Auto-population upserts
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(College, session)
    
    async def get_by_name(self, name: str) -> Optional[College]:
        """Get a college by its exact name."""
        stmt = select(College).where(College.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def search_by_name(
        self,
        search_term: str,
        limit: int = 10
    ) -> List[College]:
        """Search colleges by name (case-insensitive)."""
        stmt = (
            select(College)
            .where(College.name.ilike(f"%{search_term}%"))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_fresh_colleges(
        self,
        limit: int = 50
    ) -> List[College]:
        """
        Get colleges with fresh data (updated within STALENESS_DAYS).
        
        Phase 1 of RAG Pipeline: Check cache first.
        """
        threshold = datetime.utcnow() - timedelta(days=STALENESS_DAYS)
        stmt = (
            select(College)
            .where(College.updated_at >= threshold)
            .order_by(College.updated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_stale_colleges(
        self,
        limit: int = 100
    ) -> List[College]:
        """Get colleges with stale data needing refresh."""
        threshold = datetime.utcnow() - timedelta(days=STALENESS_DAYS)
        stmt = (
            select(College)
            .where(College.updated_at < threshold)
            .order_by(College.updated_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def count_fresh(self) -> int:
        """Count colleges with fresh data."""
        from sqlalchemy import func
        threshold = datetime.utcnow() - timedelta(days=STALENESS_DAYS)
        stmt = select(func.count()).select_from(College).where(
            College.updated_at >= threshold
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_fresh_colleges_smart(
        self,
        current_provider: str,
        limit: int = 50
    ) -> List[College]:
        """
        Get fresh colleges with Smart Correction.
        
        If current_provider is 'gemini', treat 'ollama_simulated' 
        data as stale regardless of updated_at.
        """
        from sqlalchemy import and_
        threshold = datetime.utcnow() - timedelta(days=STALENESS_DAYS)
        
        if current_provider == "gemini":
            # Exclude ollama_simulated data even if "fresh"
            stmt = (
                select(College)
                .where(and_(
                    College.updated_at >= threshold,
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
                .where(College.updated_at >= threshold)
                .order_by(College.updated_at.desc())
                .limit(limit)
            )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def count_fresh_smart(self, current_provider: str) -> int:
        """Count fresh colleges with Smart Correction."""
        from sqlalchemy import func, and_
        threshold = datetime.utcnow() - timedelta(days=STALENESS_DAYS)
        
        if current_provider == "gemini":
            stmt = select(func.count()).select_from(College).where(and_(
                College.updated_at >= threshold,
                or_(
                    College.data_source != "ollama_simulated",
                    College.data_source.is_(None)
                )
            ))
        else:
            stmt = select(func.count()).select_from(College).where(
                College.updated_at >= threshold
            )
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def upsert(self, data: CollegeCreate) -> College:
        """
        Insert or update a college by name.
        
        Phase 3 of RAG Pipeline: Auto-populate cache.
        Updates timestamp to mark as fresh.
        """
        existing = await self.get_by_name(data.name)
        
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

