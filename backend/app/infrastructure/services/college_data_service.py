"""
College Data Service

Orchestrates college data retrieval following clean architecture principles.
Implements cache-first strategy with freshness checking.

Design Pattern: Facade + Strategy
- Facade: Single entry point for college data
- Strategy: Multiple data sources (Scorecard, Perplexity)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

from app.domain.college_dto import CollegeDTO
from app.infrastructure.db.repositories.college_repository import (
    CollegeRepository,
    CollegeMajorStatsRepository,
)
from app.infrastructure.services.college_scorecard_service import (
    CollegeScorecardService,
    ScorecardCollegeData,
)
from app.infrastructure.db.models.college import (
    College,
    CollegeCreate,
    CollegeMajorStatsCreate,
)

logger = logging.getLogger(__name__)

# Cache freshness threshold
CACHE_TTL_DAYS = 30


class CollegeDataService:
    """
    Orchestrates college data retrieval with cache-first strategy.
    
    Flow:
    1. Check local cache (with freshness)
    2. If stale/missing → fetch from College Scorecard
    3. Upsert to cache
    4. Return complete DTO
    
    Fallback to Perplexity for non-US institutions.
    """
    
    def __init__(
        self,
        college_repo: CollegeRepository,
        stats_repo: CollegeMajorStatsRepository,
        scorecard_service: CollegeScorecardService,
    ):
        self.college_repo = college_repo
        self.stats_repo = stats_repo
        self.scorecard = scorecard_service
    
    async def get_college(self, name: str) -> Optional[CollegeDTO]:
        """
        Get complete college data with cache-first strategy.
        
        Args:
            name: College name to search for
            
        Returns:
            CollegeDTO with complete data, or None if not found
        """
        logger.info(f"[DATA-SERVICE] Getting college: '{name}'")
        
        # 1. Check cache with freshness
        cached, needs_refresh = await self._get_with_freshness(name)
        
        if cached and not needs_refresh:
            logger.info(f"[DATA-SERVICE] Cache hit (fresh): {cached.name}")
            dto = self._college_to_dto(cached, is_fresh=True)
            
            # Enrich via Perplexity if SAT missing
            if dto.sat_25th is None or dto.sat_75th is None:
                dto = await self._enrich_via_perplexity(dto)
            
            return dto
        
        # 2. Fetch fresh data from College Scorecard
        scorecard_data = await self.scorecard.search_by_name(name)
        
        if scorecard_data:
            logger.info(f"[DATA-SERVICE] Scorecard hit: {scorecard_data.name} (IPEDS: {scorecard_data.ipeds_id})")
            college = await self._upsert_from_scorecard(scorecard_data)
            dto = self._college_to_dto(college, is_fresh=True, source="college_scorecard")
            
            # Enrich via Perplexity if SAT missing from Scorecard
            if dto.sat_25th is None or dto.sat_75th is None:
                dto = await self._enrich_via_perplexity(dto)
                # Update cache with enriched data
                if dto.sat_25th is not None:
                    await self._update_sat_data(college.name, dto.sat_25th, dto.sat_75th)
            
            return dto
        
        # 3. If we have stale cache, return it
        if cached:
            logger.info(f"[DATA-SERVICE] Returning stale cache: {cached.name}")
            return self._college_to_dto(cached, is_fresh=False)
        
        # 4. Not found anywhere
        logger.info(f"[DATA-SERVICE] Not found: '{name}'")
        return None
    
    async def _enrich_via_perplexity(self, dto: CollegeDTO) -> CollegeDTO:
        """
        Enrich college data via Perplexity when Scorecard is missing data.
        
        Uses Perplexity Sonar to get real-time SAT data from web.
        """
        try:
            from app.config.settings import settings
            import httpx
            import json
            
            if not settings.perplexity_api_key:
                logger.warning("[DATA-SERVICE] Perplexity API key not configured, skipping enrichment")
                return dto
            
            logger.info(f"[DATA-SERVICE] Enriching {dto.name} via Perplexity for SAT data...")
            
            prompt = f"""What are the SAT score ranges for {dto.name}? 
            
Please provide ONLY the following in JSON format:
{{
    "sat_25th_percentile": <number or null>,
    "sat_75th_percentile": <number or null>,
    "acceptance_rate": <decimal 0-1 or null>
}}

Use the most recent available data (2024-2025 if available). SAT scores should be the combined total (max 1600). Return null if data is not available."""

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.perplexity_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.perplexity_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                content = data["choices"][0]["message"]["content"]
                
                # Extract JSON from response
                import re
                json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
                if json_match:
                    enriched_data = json.loads(json_match.group())
                    
                    if enriched_data.get("sat_25th_percentile"):
                        dto.sat_25th = int(enriched_data["sat_25th_percentile"])
                        logger.info(f"[DATA-SERVICE] Perplexity: SAT 25th = {dto.sat_25th}")
                    
                    if enriched_data.get("sat_75th_percentile"):
                        dto.sat_75th = int(enriched_data["sat_75th_percentile"])
                        logger.info(f"[DATA-SERVICE] Perplexity: SAT 75th = {dto.sat_75th}")
                    
                    if enriched_data.get("acceptance_rate") and dto.acceptance_rate is None:
                        dto.acceptance_rate = float(enriched_data["acceptance_rate"])
                        logger.info(f"[DATA-SERVICE] Perplexity: Acceptance = {dto.acceptance_rate:.0%}")
                    
                    dto.data_source = "college_scorecard+perplexity"
                else:
                    logger.warning(f"[DATA-SERVICE] Perplexity response had no JSON: {content[:200]}")
                    
        except Exception as e:
            logger.error(f"[DATA-SERVICE] Perplexity enrichment failed: {e}")
        
        return dto
    
    async def _update_sat_data(self, college_name: str, sat_25th: int, sat_75th: int) -> None:
        """Update SAT data in cache after Perplexity enrichment."""
        try:
            college = await self.college_repo.get_by_name(college_name)
            if college:
                college.sat_25th = sat_25th
                college.sat_75th = sat_75th
                await self.college_repo.session.commit()
                logger.info(f"[DATA-SERVICE] Updated SAT data for {college_name}: {sat_25th}-{sat_75th}")
        except Exception as e:
            logger.error(f"[DATA-SERVICE] Failed to update SAT data: {e}")
    
    async def _get_with_freshness(self, name: str) -> Tuple[Optional[College], bool]:
        """
        Get college from cache and check if it needs refresh.
        
        Uses normalized name matching to find colleges regardless of formatting
        (e.g., "University of California, Berkeley" matches "University of California-Berkeley")
        
        Returns:
            Tuple of (College or None, needs_refresh bool)
        """
        # Try exact match first
        college = await self.college_repo.get_by_name(name)
        
        if not college:
            # Try fuzzy search (ILIKE)
            colleges = await self.college_repo.search_by_name(name, limit=5)
            if colleges:
                # Pick best match
                college = colleges[0]
        
        if not college:
            # Try normalized name matching
            from app.infrastructure.services.deduplication_service import UniversityDeduplicator
            college = await self.college_repo.find_similar_name(
                name, 
                normalizer=UniversityDeduplicator.normalize_name
            )
            if college:
                logger.info(f"[DATA-SERVICE] Found via normalized match: {college.name}")
        
        if not college:
            return None, True  # Not in cache, needs fetch
        
        # Check freshness
        needs_refresh = self._is_stale(college)
        
        return college, needs_refresh
    
    def _is_stale(self, college: College) -> bool:
        """Check if cached data is stale (older than TTL)."""
        if not college.updated_at:
            return True
        
        # If no ipeds_id, data came from Perplexity and should be refreshed from Scorecard
        if not college.ipeds_id:
            return True
        
        age = datetime.utcnow() - college.updated_at
        return age > timedelta(days=CACHE_TTL_DAYS)
    
    async def _upsert_from_scorecard(self, data: ScorecardCollegeData) -> College:
        """
        Upsert college from Scorecard data (dedup by ipeds_id).
        
        Returns the updated/created College.
        """
        # Check if exists by IPEDS ID
        existing = await self.college_repo.get_by_ipeds_id(data.ipeds_id)
        
        if existing:
            # Update existing record with fresh data
            logger.info(f"[DATA-SERVICE] Updating: {existing.name} (IPEDS: {data.ipeds_id})")
            existing.name = data.name
            existing.state = data.state
            existing.city = data.city
            existing.campus_setting = data.campus_setting
            existing.acceptance_rate = data.acceptance_rate
            existing.sat_25th = data.sat_25th
            existing.sat_75th = data.sat_75th
            existing.act_25th = data.act_25th
            existing.act_75th = data.act_75th
            existing.tuition_in_state = data.tuition_in_state
            existing.tuition_out_of_state = data.tuition_out_of_state
            existing.student_size = data.student_size
            existing.updated_at = datetime.utcnow()
            return await self.college_repo.update(existing)
        
        # Check if exists by name (might be Perplexity data without ipeds_id)
        existing_by_name = await self.college_repo.get_by_name(data.name)
        
        if existing_by_name:
            # Upgrade existing record with IPEDS data
            logger.info(f"[DATA-SERVICE] Upgrading with IPEDS: {existing_by_name.name}")
            existing_by_name.ipeds_id = data.ipeds_id
            existing_by_name.state = data.state
            existing_by_name.city = data.city
            existing_by_name.campus_setting = data.campus_setting
            existing_by_name.acceptance_rate = data.acceptance_rate
            existing_by_name.sat_25th = data.sat_25th
            existing_by_name.sat_75th = data.sat_75th
            existing_by_name.act_25th = data.act_25th
            existing_by_name.act_75th = data.act_75th
            existing_by_name.tuition_in_state = data.tuition_in_state
            existing_by_name.tuition_out_of_state = data.tuition_out_of_state
            existing_by_name.student_size = data.student_size
            existing_by_name.updated_at = datetime.utcnow()
            return await self.college_repo.update(existing_by_name)
        
        # Check for similar names using normalization (e.g., "UC Berkeley" vs "University of California-Berkeley")
        from app.infrastructure.services.deduplication_service import UniversityDeduplicator
        similar = await self.college_repo.find_similar_name(
            data.name, 
            normalizer=UniversityDeduplicator.normalize_name
        )
        
        if similar:
            # Upgrade similar record with IPEDS data
            logger.info(f"[DATA-SERVICE] Upgrading similar '{similar.name}' with IPEDS: {data.name}")
            similar.ipeds_id = data.ipeds_id
            similar.name = data.name  # Use official Scorecard name
            similar.state = data.state
            similar.city = data.city
            similar.campus_setting = data.campus_setting
            similar.acceptance_rate = data.acceptance_rate
            similar.sat_25th = data.sat_25th
            similar.sat_75th = data.sat_75th
            similar.act_25th = data.act_25th
            similar.act_75th = data.act_75th
            similar.tuition_in_state = data.tuition_in_state
            similar.tuition_out_of_state = data.tuition_out_of_state
            similar.student_size = data.student_size
            similar.updated_at = datetime.utcnow()
            return await self.college_repo.update(similar)
        
        # Create new record
        logger.info(f"[DATA-SERVICE] Inserting new: {data.name} (IPEDS: {data.ipeds_id})")
        college_data = CollegeCreate(
            name=data.name,
            ipeds_id=data.ipeds_id,
            state=data.state,
            city=data.city,
            campus_setting=data.campus_setting,
            acceptance_rate=data.acceptance_rate,
            sat_25th=data.sat_25th,
            sat_75th=data.sat_75th,
            act_25th=data.act_25th,
            act_75th=data.act_75th,
            tuition_in_state=data.tuition_in_state,
            tuition_out_of_state=data.tuition_out_of_state,
            student_size=data.student_size,
        )
        return await self.college_repo.create(college_data)
    
    def _college_to_dto(
        self,
        college: College,
        is_fresh: bool,
        source: str = "cache"
    ) -> CollegeDTO:
        """Convert College model to DTO with all fields."""
        return CollegeDTO(
            ipeds_id=college.ipeds_id,
            name=college.name,
            state=college.state,
            city=getattr(college, 'city', None),
            campus_setting=college.campus_setting,
            acceptance_rate=getattr(college, 'acceptance_rate', None),
            sat_25th=getattr(college, 'sat_25th', None),
            sat_75th=getattr(college, 'sat_75th', None),
            act_25th=getattr(college, 'act_25th', None),
            act_75th=getattr(college, 'act_75th', None),
            tuition_in_state=college.tuition_in_state,
            tuition_out_of_state=college.tuition_out_of_state,
            tuition_international=college.tuition_international,
            student_size=getattr(college, 'student_size', None),
            need_blind_domestic=college.need_blind_domestic,
            need_blind_international=college.need_blind_international,
            meets_full_need=college.meets_full_need,
            updated_at=college.updated_at,
            data_source=source,
            is_fresh=is_fresh,
        )
    
    def _scorecard_to_dto(
        self,
        data: ScorecardCollegeData,
    ) -> CollegeDTO:
        """Convert Scorecard data to DTO."""
        return CollegeDTO(
            ipeds_id=data.ipeds_id,
            name=data.name,
            state=data.state,
            city=data.city,
            campus_setting=data.campus_setting,
            acceptance_rate=data.acceptance_rate,
            sat_25th=data.sat_25th,
            sat_75th=data.sat_75th,
            act_25th=data.act_25th,
            act_75th=data.act_75th,
            tuition_in_state=data.tuition_in_state,
            tuition_out_of_state=data.tuition_out_of_state,
            student_size=data.student_size,
            data_source="college_scorecard",
            is_fresh=True,
        )
