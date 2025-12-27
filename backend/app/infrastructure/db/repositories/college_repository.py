"""
College Repositories for College List AI

Implemented for normalized schema with proper repository pattern:
- CollegeRepository: Handles college institutional data
- CollegeMajorStatsRepository: Handles major-specific RAG data
- Specialized JOIN methods for hybrid queries
"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.db.models.college import (
    College,
    CollegeCreate,
    CollegeMajorStats,
    CollegeMajorStatsCreate,
    CollegeWithMajorStats,
)
from app.infrastructure.db.repositories.base_repository import BaseRepository
from sqlmodel import SQLModel


# Staleness threshold: 30 days
STALENESS_DAYS = 30


class CollegeUpdate(SQLModel):
    """Update schema for College institutional data."""
    name: Optional[str] = None
    campus_setting: Optional[str] = None
    need_blind_international: Optional[bool] = None
    meets_full_need: Optional[bool] = None


class CollegeMajorStatsUpdate(SQLModel):
    """Update schema for major-specific stats."""
    major_name: Optional[str] = None
    acceptance_rate: Optional[float] = None
    median_gpa: Optional[float] = None
    sat_25th: Optional[int] = None
    sat_75th: Optional[int] = None
    major_strength: Optional[int] = None
    data_source: Optional[str] = None


class CollegeRepository(BaseRepository[College, CollegeCreate, CollegeUpdate]):
    """
    Repository for College institutional data.
    
    Handles fixed university data that doesn't change per major.
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(College, session)
    
    async def get_by_name(self, name: str) -> Optional[College]:
        """Get a college by its unique name."""
        stmt = select(College).where(College.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_with_major_stats(
        self, 
        name: str, 
        major_name: str
    ) -> Optional[CollegeWithMajorStats]:
        """
        Get college with specific major stats via JOIN.
        
        Args:
            name: University name
            major_name: Target major (e.g., 'Computer Science')
        
        Returns:
            Combined view with institutional + major-specific data
        """
        stmt = (
            select(
                College.id,
                College.name,
                College.campus_setting,
                College.need_blind_international,
                College.meets_full_need,
                CollegeMajorStats.major_name,
                CollegeMajorStats.acceptance_rate,
                CollegeMajorStats.median_gpa,
                CollegeMajorStats.sat_25th,
                CollegeMajorStats.sat_75th,
                CollegeMajorStats.major_strength,
                CollegeMajorStats.data_source,
                CollegeMajorStats.updated_at,
            )
            .join(CollegeMajorStats, College.id == CollegeMajorStats.college_id)
            .where(and_(
                College.name == name,
                CollegeMajorStats.major_name == major_name
            ))
        )
        result = await self.session.execute(stmt)
        row = result.first()
        
        if not row:
            return None
        
        return CollegeWithMajorStats(
            id=row.id,
            name=row.name,
            campus_setting=row.campus_setting,
            need_blind_international=row.need_blind_international,
            meets_full_need=row.meets_full_need,
            major_name=row.major_name,
            acceptance_rate=row.acceptance_rate,
            median_gpa=row.median_gpa,
            sat_25th=row.sat_25th,
            sat_75th=row.sat_75th,
            major_strength=row.major_strength,
            data_source=row.data_source,
            updated_at=row.updated_at,
        )
    
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
    
    async def get_or_create(self, data: CollegeCreate) -> Tuple[College, bool]:
        """
        Get existing college by name or create new one.
        
        Returns:
            Tuple of (College, created_flag)
        """
        existing = await self.get_by_name(data.name)
        if existing:
            return existing, False
        
        new_college = await self.create(data)
        return new_college, True


class CollegeMajorStatsRepository(
    BaseRepository[CollegeMajorStats, CollegeMajorStatsCreate, CollegeMajorStatsUpdate]
):
    """
    Repository for major-specific statistics (RAG data).
    
    Supports Smart Sourcing RAG Pipeline with:
    - Staleness detection (30 days)
    - Cache-first queries filtered by major_name
    - Auto-population upserts by (college_id, major_name) composite key
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(CollegeMajorStats, session)
    
    async def get_by_college_and_major(
        self, 
        college_id: UUID, 
        major_name: str
    ) -> Optional[CollegeMajorStats]:
        """Get stats for a specific college+major combination."""
        stmt = select(CollegeMajorStats).where(and_(
            CollegeMajorStats.college_id == college_id,
            CollegeMajorStats.major_name == major_name
        ))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_fresh_for_major(
        self,
        major_name: str,
        limit: int = 50
    ) -> List[CollegeWithMajorStats]:
        """
        Get colleges with fresh stats for a specific major.
        
        Phase 1 of RAG Pipeline: Check cache first.
        Returns JOINed data ready for scoring.
        """
        threshold = datetime.utcnow() - timedelta(days=STALENESS_DAYS)
        
        stmt = (
            select(
                College.id,
                College.name,
                College.campus_setting,
                College.need_blind_international,
                College.meets_full_need,
                CollegeMajorStats.major_name,
                CollegeMajorStats.acceptance_rate,
                CollegeMajorStats.median_gpa,
                CollegeMajorStats.sat_25th,
                CollegeMajorStats.sat_75th,
                CollegeMajorStats.major_strength,
                CollegeMajorStats.data_source,
                CollegeMajorStats.updated_at,
            )
            .join(CollegeMajorStats, College.id == CollegeMajorStats.college_id)
            .where(and_(
                CollegeMajorStats.major_name == major_name,
                CollegeMajorStats.updated_at >= threshold
            ))
            .order_by(CollegeMajorStats.updated_at.desc())
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        rows = result.all()
        
        return [
            CollegeWithMajorStats(
                id=row.id,
                name=row.name,
                campus_setting=row.campus_setting,
                need_blind_international=row.need_blind_international,
                meets_full_need=row.meets_full_need,
                major_name=row.major_name,
                acceptance_rate=row.acceptance_rate,
                median_gpa=row.median_gpa,
                sat_25th=row.sat_25th,
                sat_75th=row.sat_75th,
                major_strength=row.major_strength,
                data_source=row.data_source,
                updated_at=row.updated_at,
            )
            for row in rows
        ]
    
    async def get_fresh_smart(
        self,
        current_provider: str,
        major_name: str,
        limit: int = 50
    ) -> List[CollegeWithMajorStats]:
        """
        Get fresh colleges with Smart Correction.
        
        If current_provider is 'gemini', treat 'ollama_simulated'
        data as stale regardless of updated_at.
        """
        threshold = datetime.utcnow() - timedelta(days=STALENESS_DAYS)
        
        base_conditions = [
            CollegeMajorStats.major_name == major_name,
            CollegeMajorStats.updated_at >= threshold
        ]
        
        if current_provider == "gemini":
            base_conditions.append(
                or_(
                    CollegeMajorStats.data_source != "ollama_simulated",
                    CollegeMajorStats.data_source.is_(None)
                )
            )
        
        stmt = (
            select(
                College.id,
                College.name,
                College.campus_setting,
                College.need_blind_international,
                College.meets_full_need,
                CollegeMajorStats.major_name,
                CollegeMajorStats.acceptance_rate,
                CollegeMajorStats.median_gpa,
                CollegeMajorStats.sat_25th,
                CollegeMajorStats.sat_75th,
                CollegeMajorStats.major_strength,
                CollegeMajorStats.data_source,
                CollegeMajorStats.updated_at,
            )
            .join(CollegeMajorStats, College.id == CollegeMajorStats.college_id)
            .where(and_(*base_conditions))
            .order_by(CollegeMajorStats.updated_at.desc())
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        rows = result.all()
        
        return [
            CollegeWithMajorStats(
                id=row.id,
                name=row.name,
                campus_setting=row.campus_setting,
                need_blind_international=row.need_blind_international,
                meets_full_need=row.meets_full_need,
                major_name=row.major_name,
                acceptance_rate=row.acceptance_rate,
                median_gpa=row.median_gpa,
                sat_25th=row.sat_25th,
                sat_75th=row.sat_75th,
                major_strength=row.major_strength,
                data_source=row.data_source,
                updated_at=row.updated_at,
            )
            for row in rows
        ]
    
    async def count_fresh(self, major_name: str) -> int:
        """Count fresh stats entries for a specific major."""
        from sqlalchemy import func
        threshold = datetime.utcnow() - timedelta(days=STALENESS_DAYS)
        
        stmt = select(func.count()).select_from(CollegeMajorStats).where(and_(
            CollegeMajorStats.major_name == major_name,
            CollegeMajorStats.updated_at >= threshold
        ))
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def count_fresh_smart(
        self, 
        current_provider: str, 
        major_name: str
    ) -> int:
        """Count fresh stats with Smart Correction."""
        from sqlalchemy import func
        threshold = datetime.utcnow() - timedelta(days=STALENESS_DAYS)
        
        base_conditions = [
            CollegeMajorStats.major_name == major_name,
            CollegeMajorStats.updated_at >= threshold
        ]
        
        if current_provider == "gemini":
            base_conditions.append(
                or_(
                    CollegeMajorStats.data_source != "ollama_simulated",
                    CollegeMajorStats.data_source.is_(None)
                )
            )
        
        stmt = select(func.count()).select_from(CollegeMajorStats).where(
            and_(*base_conditions)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def upsert(
        self, 
        college_id: UUID, 
        data: CollegeMajorStatsCreate
    ) -> CollegeMajorStats:
        """
        Insert or update major stats by (college_id, major_name) key.
        
        Phase 3 of RAG Pipeline: Auto-populate cache.
        Updates timestamp to mark as fresh.
        """
        existing = await self.get_by_college_and_major(college_id, data.major_name)
        
        if existing:
            # Update existing with new data
            for field in ['acceptance_rate', 'median_gpa', 'sat_25th', 'sat_75th',
                         'major_strength', 'data_source']:
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
            # Create new with college_id set
            stats_data = CollegeMajorStatsCreate(
                college_id=college_id,
                major_name=data.major_name,
                acceptance_rate=data.acceptance_rate,
                median_gpa=data.median_gpa,
                sat_25th=data.sat_25th,
                sat_75th=data.sat_75th,
                major_strength=data.major_strength,
                data_source=data.data_source,
            )
            return await self.create(stats_data)
