"""
College List Enrichment Service

Enriches user's college list with detailed data from multiple sources:
1. Local cache (colleges table)
2. College Scorecard API (fallback)
3. Known financial aid policies fallback

Follows Single Responsibility Principle - only handles data enrichment.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.college import College
from app.infrastructure.db.models.user_college_list import UserCollegeListItem
from app.infrastructure.db.repositories.college_repository import CollegeRepository
from app.infrastructure.db.repositories.user_college_list_repository import (
    UserCollegeListRepository,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Known Financial Aid Policies
# These are manually curated from official university websites.
# True = Yes, False = No, None = Unknown
# =============================================================================

# Universities that are need-blind AND meet 100% demonstrated need for international students
NEED_BLIND_FULL_NEED_INTERNATIONAL: Dict[str, Tuple[bool, bool]] = {
    # (need_blind_international, meets_full_need)
    # Ivy League
    "harvard university": (True, True),
    "yale university": (True, True),
    "princeton university": (True, True),
    "massachusetts institute of technology": (True, True),
    "mit": (True, True),
    "amherst college": (True, True),
    "dartmouth college": (True, True),
    
    # Need-aware but meets 100% need
    "stanford university": (False, True),
    "columbia university": (False, True),
    "university of pennsylvania": (False, True),
    "brown university": (False, True),
    "cornell university": (False, True),
    "duke university": (False, True),
    "northwestern university": (False, True),
    "university of chicago": (False, True),
    "johns hopkins university": (False, True),
    "rice university": (False, True),
    "vanderbilt university": (False, True),
    "washington university in st. louis": (False, True),
    "williams college": (False, True),
    "swarthmore college": (False, True),
    "pomona college": (False, True),
    "bowdoin college": (False, True),
    
    # UCs and publics - no need-blind, limited aid for internationals
    "university of california-berkeley": (False, False),
    "university of california-los angeles": (False, False),
    "university of california-san diego": (False, False),
    "university of california-davis": (False, False),
    "university of california-irvine": (False, False),
    "university of california-santa barbara": (False, False),
    "university of california-santa cruz": (False, False),
    "university of california-riverside": (False, False),
    "university of california-merced": (False, False),
    
    # Other publics
    "purdue university-main campus": (False, False),
    "purdue university fort wayne": (False, False),
    "university of michigan-ann arbor": (False, False),
    "university of texas at austin": (False, False),
    "georgia institute of technology-main campus": (False, False),
    "university of illinois urbana-champaign": (False, False),
    "university of wisconsin-madison": (False, False),
    "university of washington-seattle campus": (False, False),
    "pennsylvania state university-main campus": (False, False),
    "ohio state university-main campus": (False, False),
    
    # Others with known policies
    "carnegie mellon university": (False, True),
    "new york university": (False, False),
    "boston university": (False, False),
    "university of southern california": (False, False),
    "northeastern university": (False, False),
    
    # Smaller colleges that meet need
    "grinnell college": (False, True),
    "wellesley college": (False, True),
    "middlebury college": (False, True),
    "colby college": (False, True),
    "hamilton college": (False, True),
    
    # Stetson and Stockton - liberal arts
    "stetson university": (False, False),
    "stockton university": (False, False),
}


@dataclass
class EnrichedCollegeItem:
    """
    Complete college data for spreadsheet view.
    
    Combines user's list item with institutional data.
    """
    # User list data
    id: UUID
    college_name: str
    label: Optional[str]
    notes: Optional[str]
    added_at: str
    
    # Institutional data (from cache or API)
    acceptance_rate: Optional[float] = None
    sat_25th: Optional[int] = None
    sat_75th: Optional[int] = None
    act_25th: Optional[int] = None
    act_75th: Optional[int] = None
    tuition_international: Optional[float] = None
    need_blind_international: Optional[bool] = None
    meets_full_need: Optional[bool] = None
    city: Optional[str] = None
    state: Optional[str] = None
    campus_setting: Optional[str] = None
    student_size: Optional[int] = None


class CollegeListEnrichmentService:
    """
    Service to enrich user's college list with detailed institutional data.
    
    Pipeline:
    1. Fetch user's saved colleges
    2. Look up each in local cache
    3. Fallback to Scorecard API for missing data
    4. Apply financial aid policies from known database
    5. Return enriched items
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
        self._college_repo = CollegeRepository(session)
        self._list_repo = UserCollegeListRepository(session)
    
    async def get_enriched_list(self, user_id: UUID) -> List[EnrichedCollegeItem]:
        """
        Get user's college list with all available institutional data.
        
        Args:
            user_id: The user's UUID
            
        Returns:
            List of enriched college items ready for spreadsheet display
        """
        # 1. Get user's saved colleges
        list_items = await self._list_repo.get_all(user_id)
        
        if not list_items:
            return []
        
        # 2. Enrich each item
        enriched_items: List[EnrichedCollegeItem] = []
        
        for item in list_items:
            enriched = await self._enrich_item(item)
            enriched_items.append(enriched)
        
        return enriched_items
    
    async def _enrich_item(self, item: UserCollegeListItem) -> EnrichedCollegeItem:
        """
        Enrich a single college list item with institutional data.
        
        Tries:
        1. Exact name match in cache
        2. Fuzzy name match in cache
        3. College Scorecard API lookup
        4. Apply known financial aid policies
        """
        # Base item from user's list
        enriched = EnrichedCollegeItem(
            id=item.id,
            college_name=item.college_name,
            label=item.label,
            notes=item.notes,
            added_at=item.added_at.isoformat(),
        )
        
        # Try to find college data in cache
        college = await self._find_college_in_cache(item.college_name)
        
        if college:
            self._apply_college_data(enriched, college)
            logger.debug(f"Enriched '{item.college_name}' from cache")
        else:
            # Fallback: try Scorecard API
            await self._enrich_from_scorecard(enriched, item.college_name)
        
        # Apply known financial aid policies (always, to fill gaps)
        self._apply_financial_aid_policies(enriched)
        
        return enriched
    
    async def _find_college_in_cache(self, name: str) -> Optional[College]:
        """
        Find college in cache by name (exact or fuzzy match).
        """
        # Try exact match first
        college = await self._college_repo.get_by_name(name)
        if college:
            return college
        
        # Try search (partial match)
        results = await self._college_repo.search_by_name(name, limit=1)
        if results:
            return results[0]
        
        return None
    
    def _apply_college_data(
        self, 
        enriched: EnrichedCollegeItem, 
        college: College
    ) -> None:
        """
        Apply college institutional data to enriched item.
        
        For international students, uses tuition_out_of_state as proxy
        for international tuition when tuition_international is missing.
        """
        enriched.acceptance_rate = college.acceptance_rate
        enriched.sat_25th = college.sat_25th
        enriched.sat_75th = college.sat_75th
        enriched.act_25th = college.act_25th
        enriched.act_75th = college.act_75th
        
        # Use tuition_international if available, otherwise use out_of_state as proxy
        if college.tuition_international:
            enriched.tuition_international = college.tuition_international
        elif college.tuition_out_of_state:
            enriched.tuition_international = college.tuition_out_of_state
        
        enriched.need_blind_international = college.need_blind_international
        enriched.meets_full_need = college.meets_full_need
        enriched.city = college.city
        enriched.state = college.state
        enriched.campus_setting = college.campus_setting
        enriched.student_size = college.student_size
    
    def _apply_financial_aid_policies(self, enriched: EnrichedCollegeItem) -> None:
        """
        Apply known financial aid policies from curated database.
        
        Only overwrites if current value is None (respects cache data).
        """
        name_lower = enriched.college_name.lower().strip()
        
        # Try exact match
        policy = NEED_BLIND_FULL_NEED_INTERNATIONAL.get(name_lower)
        
        # Try fuzzy match if exact not found
        if not policy:
            for known_name, known_policy in NEED_BLIND_FULL_NEED_INTERNATIONAL.items():
                if known_name in name_lower or name_lower in known_name:
                    policy = known_policy
                    break
        
        if policy:
            need_blind, meets_need = policy
            
            # Only apply if not already set
            if enriched.need_blind_international is None:
                enriched.need_blind_international = need_blind
            if enriched.meets_full_need is None:
                enriched.meets_full_need = meets_need
    
    async def _enrich_from_scorecard(
        self, 
        enriched: EnrichedCollegeItem, 
        college_name: str
    ) -> None:
        """
        Try to enrich from College Scorecard API.
        
        Updates enriched item in place if data is found.
        Uses out_of_state tuition as proxy for international.
        Also caches the result for future lookups.
        """
        try:
            from app.infrastructure.services.college_scorecard_service import (
                CollegeScorecardService,
            )
            
            scorecard = CollegeScorecardService()
            data = await scorecard.search_by_name(college_name)
            
            if data:
                enriched.acceptance_rate = data.acceptance_rate
                enriched.sat_25th = data.sat_25th
                enriched.sat_75th = data.sat_75th
                enriched.act_25th = data.act_25th
                enriched.act_75th = data.act_75th
                enriched.city = data.city
                enriched.state = data.state
                enriched.student_size = data.student_size
                
                # Use out_of_state tuition as proxy for international
                if data.tuition_out_of_state:
                    enriched.tuition_international = data.tuition_out_of_state
                
                # Cache for future lookups
                await self._cache_scorecard_data(data)
                
                logger.info(f"Enriched '{college_name}' from Scorecard API")
            else:
                logger.debug(f"No Scorecard data found for '{college_name}'")
                
        except Exception as e:
            logger.warning(f"Scorecard lookup failed for '{college_name}': {e}")
    
    async def _cache_scorecard_data(self, data) -> None:
        """
        Cache Scorecard data for future lookups.
        
        Uses upsert to avoid duplicates.
        Stores out_of_state tuition as tuition_international for international students.
        """
        try:
            from app.infrastructure.db.models.college import CollegeCreate
            
            # Check if already exists by IPEDS ID
            existing = None
            if data.ipeds_id:
                existing = await self._college_repo.get_by_ipeds_id(data.ipeds_id)
            
            if not existing:
                existing = await self._college_repo.get_by_name(data.name)
            
            if existing:
                # Update existing record with all available data
                existing.acceptance_rate = data.acceptance_rate or existing.acceptance_rate
                existing.sat_25th = data.sat_25th or existing.sat_25th
                existing.sat_75th = data.sat_75th or existing.sat_75th
                existing.act_25th = data.act_25th or existing.act_25th
                existing.act_75th = data.act_75th or existing.act_75th
                existing.city = data.city or existing.city
                existing.state = data.state or existing.state
                existing.student_size = data.student_size or existing.student_size
                existing.campus_setting = data.campus_setting or existing.campus_setting
                
                # Store tuition data
                existing.tuition_in_state = data.tuition_in_state or existing.tuition_in_state
                existing.tuition_out_of_state = data.tuition_out_of_state or existing.tuition_out_of_state
                
                # Use out_of_state as international if not already set
                if not existing.tuition_international and data.tuition_out_of_state:
                    existing.tuition_international = data.tuition_out_of_state
                
                if data.ipeds_id and not existing.ipeds_id:
                    existing.ipeds_id = data.ipeds_id
                
                await self._college_repo.update(existing)
            else:
                # Create new record
                new_college = CollegeCreate(
                    name=data.name,
                    ipeds_id=data.ipeds_id,
                    acceptance_rate=data.acceptance_rate,
                    sat_25th=data.sat_25th,
                    sat_75th=data.sat_75th,
                    act_25th=data.act_25th,
                    act_75th=data.act_75th,
                    city=data.city,
                    state=data.state,
                    campus_setting=data.campus_setting,
                    student_size=data.student_size,
                    tuition_in_state=data.tuition_in_state,
                    tuition_out_of_state=data.tuition_out_of_state,
                    # Use out_of_state as proxy for international
                    tuition_international=data.tuition_out_of_state,
                )
                await self._college_repo.create(new_college)
            
            await self._session.commit()
            
        except Exception as e:
            logger.warning(f"Failed to cache Scorecard data: {e}")
            await self._session.rollback()
