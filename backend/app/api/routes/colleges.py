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
    
    Deduplication:
    - Prioritizes records with IPEDS ID (official Scorecard data)
    - Filters out duplicate entries with similar names
    """
    import re
    
    repo = CollegeRepository(session)
    # Fetch more than limit to allow for deduplication filtering
    colleges = await repo.search_by_name(q, limit=limit * 3)
    
    def normalize_name(name: str) -> str:
        """Normalize university name for duplicate detection."""
        normalized = name.lower().strip()
        normalized = re.sub(r'\([^)]*\)', '', normalized)  # Remove parenthetical
        normalized = re.sub(r'[-,]', ' ', normalized)       # Replace hyphens/commas
        normalized = re.sub(r'\s+', ' ', normalized)        # Collapse spaces
        return normalized.strip()
    
    # Deduplicate: keep first occurrence based on normalized name
    # Priority: records with IPEDS ID come first
    seen_normalized = set()
    unique_colleges = []
    
    # Sort: IPEDS records first
    sorted_colleges = sorted(colleges, key=lambda c: (c.ipeds_id is None, c.name))
    
    for college in sorted_colleges:
        norm = normalize_name(college.name)
        
        # Check if we've seen a similar name
        is_duplicate = False
        for seen in seen_normalized:
            # Check for high overlap (one contains the other)
            if norm in seen or seen in norm:
                is_duplicate = True
                break
        
        if not is_duplicate:
            seen_normalized.add(norm)
            unique_colleges.append(college)
            
            if len(unique_colleges) >= limit:
                break
    
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
        for college in unique_colleges
    ]


@router.post("/admin/deduplicate", response_model=dict)
async def deduplicate_colleges(
    session: AsyncSession = Depends(get_session),
):
    """
    Admin endpoint to find and merge duplicate college records.
    
    This will:
    1. Find colleges with IPEDS ID (authoritative) that have duplicates without IPEDS
    2. Merge the duplicates into the authoritative record
    3. Delete the legacy records
    """
    from app.infrastructure.services.deduplication_service import UniversityDeduplicator
    
    dedup = UniversityDeduplicator(session)
    
    # Find duplicates first
    duplicates = await dedup.find_duplicates()
    
    if not duplicates:
        return {"status": "no_duplicates", "deleted": 0, "message": "No duplicates found"}
    
    # Get details for response
    details = []
    for auth, dupes in duplicates:
        details.append({
            "keep": auth.name,
            "ipeds_id": auth.ipeds_id,
            "delete": [d.name for d in dupes]
        })
    
    # Merge and delete
    deleted = await dedup.merge_and_delete_duplicates()
    
    return {
        "status": "success",
        "deleted": deleted,
        "details": details
    }
