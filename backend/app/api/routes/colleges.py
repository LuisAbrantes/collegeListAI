"""
Colleges API Routes

Public endpoints for searching colleges from the database.
"""

from typing import List, Optional
from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.database import get_session
from app.infrastructure.db.repositories.college_repository import CollegeRepository


router = APIRouter(prefix="/api/colleges", tags=["colleges"])


class CollegeSearchResult(BaseModel):
    """College search result with key metrics."""
    id: str
    name: str
    campus_setting: Optional[str] = None
    need_blind_domestic: Optional[bool] = None
    need_blind_international: Optional[bool] = None
    meets_full_need: Optional[bool] = None
    state: Optional[str] = None


@router.get("/search", response_model=List[CollegeSearchResult])
async def search_colleges(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    """
    Search colleges by name.
    
    Returns matching colleges for display in the college list.
    Supports partial matching (e.g., "MIT" matches "Massachusetts Institute of Technology").
    """
    repo = CollegeRepository(session)
    colleges = await repo.search_by_name(q, limit=limit)
    
    return [
        CollegeSearchResult(
            id=str(college.id),
            name=college.name,
            campus_setting=college.campus_setting,
            need_blind_domestic=college.need_blind_domestic,
            need_blind_international=college.need_blind_international,
            meets_full_need=college.meets_full_need,
            state=college.state,
        )
        for college in colleges
    ]
