"""
College Search Service for College List AI

Implements Smart Sourcing RAG Pipeline:
Phase 1: Local cache query
Phase 2: Gemini discovery (if needed)
Phase 3: Auto-populate cache
Phase 4: Return combined list for scoring
"""

import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from google import genai
from google.genai import types

from app.config.settings import settings
from app.infrastructure.db.models.college import College, CollegeCreate
from app.infrastructure.db.repositories.college_repository import CollegeRepository
from app.domain.scoring import UniversityData

logger = logging.getLogger(__name__)

# Minimum fresh colleges before triggering web search
MIN_CACHE_THRESHOLD = 10


class CollegeSearchService:
    """
    Hybrid search service implementing the Data Flywheel.
    
    Flow:
    1. Check local cache for fresh data
    2. If cache < threshold, discover from web via Gemini
    3. Auto-populate cache with new discoveries
    4. Return combined list for scoring
    """
    
    def __init__(self, repository: CollegeRepository):
        self.repository = repository
        self.client = genai.Client(api_key=settings.google_api_key)
    
    async def hybrid_search(
        self,
        major: str,
        profile: Dict[str, Any],
        student_type: str,
        limit: int = 20
    ) -> List[UniversityData]:
        """
        Execute hybrid search: cache-first, then web discovery.
        
        Args:
            major: Student's intended major
            profile: Student profile dict
            student_type: 'domestic' or 'international'
            limit: Max universities to return
            
        Returns:
            List of UniversityData ready for scoring
        """
        # Phase 1: Check local cache
        logger.info("Phase 1: Checking local cache...")
        fresh_count = await self.repository.count_fresh()
        cached_colleges = await self.repository.get_fresh_colleges(limit=limit)
        
        logger.info(f"Found {fresh_count} fresh colleges in cache")
        
        universities: List[UniversityData] = []
        
        # Convert cached colleges to UniversityData
        for college in cached_colleges:
            universities.append(self._college_to_university_data(college, major))
        
        # Phase 2: Discovery - only if cache is insufficient
        if fresh_count < MIN_CACHE_THRESHOLD:
            logger.info(f"Phase 2: Cache below threshold ({fresh_count} < {MIN_CACHE_THRESHOLD}), triggering Gemini discovery...")
            
            try:
                web_results = await self._discover_from_web(major, profile, student_type)
                
                # Phase 3: Auto-populate cache
                logger.info(f"Phase 3: Auto-populating cache with {len(web_results)} discoveries...")
                for uni_data in web_results:
                    await self._save_to_cache(uni_data)
                    universities.append(uni_data)
                
            except Exception as e:
                logger.warning(f"Web discovery failed: {e}. Using cache only.")
        else:
            logger.info("Cache sufficient, skipping web discovery")
        
        # Deduplicate by name
        seen = set()
        unique = []
        for uni in universities:
            if uni.name not in seen:
                seen.add(uni.name)
                unique.append(uni)
        
        logger.info(f"Phase 4: Returning {len(unique)} universities for scoring")
        return unique[:limit]
    
    async def _discover_from_web(
        self,
        major: str,
        profile: Dict[str, Any],
        student_type: str
    ) -> List[UniversityData]:
        """
        Use Gemini Search Grounding to discover universities.
        
        Parses response to extract structured university data.
        """
        gpa = profile.get("gpa", 3.5)
        nationality = profile.get("nationality", "international")
        is_domestic = student_type == "domestic"
        
        # Build discovery prompt
        prompt = f"""Find 15 US universities for a student with these characteristics:
- Major: {major}
- GPA: {gpa}/4.0
- Student Type: {"Domestic US" if is_domestic else f"International from {nationality}"}

For each university, provide this information in a structured format:
UNIVERSITY: [Name]
ACCEPTANCE_RATE: [percentage, e.g. 15%]
MEDIAN_GPA: [e.g. 3.8]
SAT_RANGE: [e.g. 1400-1550]
NEED_BLIND_INTL: [Yes/No]

Include a diverse mix:
- 3 highly selective (acceptance < 20%)
- 5 moderately selective (20-50%)
- 7 less selective (> 50%)

Focus on schools with strong {major} programs. Use current 2025 data."""

        response = self.client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=3000,
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        
        # Parse response into UniversityData objects
        return self._parse_gemini_response(response.text or "", major)
    
    def _parse_gemini_response(
        self,
        text: str,
        major: str
    ) -> List[UniversityData]:
        """
        Parse Gemini response into structured UniversityData.
        
        Extracts: name, acceptance_rate, median_gpa, SAT range.
        """
        universities = []
        
        # Pattern to extract university blocks
        uni_pattern = r"UNIVERSITY:\s*(.+?)(?:\n|$)"
        rate_pattern = r"ACCEPTANCE_RATE:\s*([\d.]+)%?"
        gpa_pattern = r"MEDIAN_GPA:\s*([\d.]+)"
        sat_pattern = r"SAT_RANGE:\s*(\d+)\s*[-–]\s*(\d+)"
        need_blind_pattern = r"NEED_BLIND_INTL:\s*(Yes|No)"
        
        # Split by UNIVERSITY: marker
        blocks = re.split(r"(?=UNIVERSITY:)", text, flags=re.IGNORECASE)
        
        for block in blocks:
            if not block.strip():
                continue
            
            # Extract name
            name_match = re.search(uni_pattern, block, re.IGNORECASE)
            if not name_match:
                continue
            
            name = name_match.group(1).strip()
            
            # Extract stats
            acceptance_rate = None
            rate_match = re.search(rate_pattern, block)
            if rate_match:
                acceptance_rate = float(rate_match.group(1)) / 100.0
            
            median_gpa = None
            gpa_match = re.search(gpa_pattern, block)
            if gpa_match:
                median_gpa = float(gpa_match.group(1))
            
            sat_25th, sat_75th = None, None
            sat_match = re.search(sat_pattern, block)
            if sat_match:
                sat_25th = int(sat_match.group(1))
                sat_75th = int(sat_match.group(2))
            
            need_blind = False
            need_blind_match = re.search(need_blind_pattern, block, re.IGNORECASE)
            if need_blind_match:
                need_blind = need_blind_match.group(1).lower() == "yes"
            
            universities.append(UniversityData(
                name=name,
                acceptance_rate=acceptance_rate,
                median_gpa=median_gpa,
                sat_25th=sat_25th,
                sat_75th=sat_75th,
                need_blind_international=need_blind,
                data_source="gemini",
                has_major=True,
                student_major=major,
            ))
        
        logger.info(f"Parsed {len(universities)} universities from Gemini response")
        return universities
    
    async def _save_to_cache(self, uni_data: UniversityData) -> None:
        """Save a university to the cache (auto-population)."""
        college_create = CollegeCreate(
            name=uni_data.name,
            acceptance_rate=uni_data.acceptance_rate,
            median_gpa=uni_data.median_gpa,
            sat_25th=uni_data.sat_25th,
            sat_75th=uni_data.sat_75th,
            need_blind_international=uni_data.need_blind_international or False,
            data_source="gemini",
        )
        await self.repository.upsert(college_create)
    
    def _college_to_university_data(
        self,
        college: College,
        major: str
    ) -> UniversityData:
        """Convert a cached College to UniversityData for scoring."""
        return UniversityData(
            name=college.name,
            acceptance_rate=college.acceptance_rate,
            median_gpa=college.median_gpa,
            sat_25th=college.sat_25th,
            sat_75th=college.sat_75th,
            need_blind_international=college.need_blind_international,
            data_source=college.data_source or "cache",
            has_major=True,
            student_major=major,
        )
