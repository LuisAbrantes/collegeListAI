"""
College Search Service for College List AI

Implements Smart Sourcing RAG Pipeline:
Phase 1: Local cache query
Phase 2: Gemini/Ollama discovery (if needed)
Phase 3: Auto-populate cache
Phase 4: Return combined list for scoring
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import httpx
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.infrastructure.db.models.college import College, CollegeCreate
from app.infrastructure.db.repositories.college_repository import CollegeRepository
from app.domain.scoring import UniversityData

logger = logging.getLogger(__name__)

# Minimum fresh colleges before triggering web search
MIN_CACHE_THRESHOLD = 10


# ============== Structured Output Schemas ==============

class UniversityExtraction(BaseModel):
    """Schema for a single university extracted from Gemini response."""
    name: str = Field(..., description="Full university name")
    acceptance_rate: float = Field(..., ge=0.0, le=1.0, description="Acceptance rate as decimal (e.g., 0.15 for 15%)")
    median_gpa: float = Field(..., ge=0.0, le=4.0, description="Median GPA of ADMITTED students")
    sat_25th: int = Field(..., ge=400, le=1600, description="25th percentile SAT score of admitted students")
    sat_75th: int = Field(..., ge=400, le=1600, description="75th percentile SAT score of admitted students")
    major_strength_score: int = Field(..., ge=1, le=10, description="Program strength rating 1-10 for student's major")
    need_blind_international: bool = Field(..., description="Whether the school is need-blind for international students")


class GeminiUniversityResponse(BaseModel):
    """Schema for the complete Gemini structured response."""
    universities: List[UniversityExtraction] = Field(..., description="List of universities with admission data")


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
        self._init_llm_client()
    
    def _init_llm_client(self):
        """Initialize LLM client based on provider setting."""
        if settings.llm_provider == "gemini":
            self.client = genai.Client(api_key=settings.google_api_key)
        else:
            # Ollama uses HTTP requests, no persistent client needed
            self.client = None
    
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
        # Phase 1: Check local cache with Smart Correction
        logger.info("Phase 1: Checking local cache with Smart Correction...")
        fresh_count = await self.repository.count_fresh_smart(settings.llm_provider)
        cached_colleges = await self.repository.get_fresh_colleges_smart(
            current_provider=settings.llm_provider,
            limit=limit
        )
        
        logger.info(f"Found {fresh_count} fresh colleges in cache (provider: {settings.llm_provider})")
        
        universities: List[UniversityData] = []
        
        # Convert cached colleges to UniversityData
        for college in cached_colleges:
            universities.append(self._college_to_university_data(college, major))
        
        # Phase 2: Discovery - only if cache is insufficient
        if fresh_count < MIN_CACHE_THRESHOLD:
            logger.info(f"Phase 2: Cache below threshold ({fresh_count} < {MIN_CACHE_THRESHOLD}), triggering discovery...")
            
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
        Route to appropriate LLM provider based on settings.
        
        If Gemini fails with 429, logs a warning suggesting switch to Ollama.
        """
        if settings.llm_provider == "ollama":
            logger.info("Using Ollama for local development discovery")
            return await self._discover_via_ollama(major, profile, student_type)
        
        # Gemini path with 429 fallback warning
        try:
            return await self._discover_via_gemini(major, profile, student_type)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                logger.warning(
                    f"Gemini 429 rate limit hit: {e}. "
                    "Consider switching to LLM_PROVIDER=ollama for local development."
                )
            raise
    
    async def _discover_via_ollama(
        self,
        major: str,
        profile: Dict[str, Any],
        student_type: str
    ) -> List[UniversityData]:
        """
        Use local Ollama API for university discovery.
        
        Since Ollama is local, simulates latest 2025 admission data
        for testing the Auto-Populate Cache flow.
        """
        gpa = profile.get("gpa", 3.5)
        nationality = profile.get("nationality", "international")
        is_domestic = student_type == "domestic"
        
        prompt = f"""You are simulating an expert college admissions database.

IMPORTANT: Since this is a LOCAL DEVELOPMENT environment, simulate realistic 
2025 admission data for testing purposes. Generate plausible statistics.

Find 15 US universities for a student with these characteristics:
- Intended Major: {major}
- Current GPA: {gpa}/4.0
- Student Type: {"Domestic US" if is_domestic else f"International from {nationality}"}

Include a strategically diverse mix:
- 3 highly selective (acceptance rate < 20%)
- 5 moderately selective (acceptance rate 20-50%)
- 7 less selective (acceptance rate > 50%)

Return ONLY valid JSON matching this exact schema:
{{
  "universities": [
    {{
      "name": "Full University Name",
      "acceptance_rate": 0.15,
      "median_gpa": 3.9,
      "sat_25th": 1400,
      "sat_75th": 1550,
      "major_strength_score": 8,
      "need_blind_international": true
    }}
  ]
}}"""

        try:
            logger.info("Ollama is generating the structured response...")
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": prompt,
                        "format": "json",
                        "stream": False,
                    },
                )
                response.raise_for_status()
                result = response.json()
                return self._parse_structured_response(result.get("response", ""), major)
        except httpx.HTTPError as e:
            logger.error(f"Ollama API error: {e}")
            raise RuntimeError(f"Ollama discovery failed: {e}")
    
    async def _discover_via_gemini(
        self,
        major: str,
        profile: Dict[str, Any],
        student_type: str
    ) -> List[UniversityData]:
        """
        Use Gemini Search Grounding with Structured Output to discover universities.
        
        Returns validated UniversityData objects parsed from JSON response.
        """
        gpa = profile.get("gpa", 3.5)
        nationality = profile.get("nationality", "international")
        is_domestic = student_type == "domestic"
        
        # Build discovery prompt with LATEST DATA requirements
        prompt = f"""You are an expert college admissions counselor with access to the LATEST admission statistics.

CRITICAL REQUIREMENTS:
1. Use data from the LATEST admission cycle (Class of 2028/2029, admitted Fall 2024/2025)
2. Report the MEDIAN or AVERAGE statistics of ADMITTED students, NOT minimum requirements
3. SAT scores must be the 25th and 75th percentile of ENROLLED students
4. GPA must be the median GPA of admitted students on a 4.0 scale

Find 15 US universities for a student with these characteristics:
- Intended Major: {major}
- Current GPA: {gpa}/4.0
- Student Type: {"Domestic US" if is_domestic else f"International student from {nationality}"}

Include a strategically diverse mix:
- 3 highly selective universities (acceptance rate < 20%)
- 5 moderately selective universities (acceptance rate 20-50%)
- 7 less selective universities (acceptance rate > 50%)

For EACH university, provide:
- Full official university name
- Acceptance rate as a decimal (e.g., 0.15 for 15%)
- Median GPA of ADMITTED students (not minimum required)
- 25th percentile SAT score of admitted students
- 75th percentile SAT score of admitted students
- Program strength score (1-10) for {major} specifically
- Whether the school is need-blind for international student admissions

IMPORTANT: Focus on universities with strong {major} programs. Use real 2024/2025 admission data."""

        try:
            response = self.client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=4000,
                    response_mime_type="application/json",
                    response_schema=GeminiUniversityResponse,
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            
            # Parse structured JSON response
            return self._parse_structured_response(response.text or "", major)
            
        except Exception as e:
            logger.error(f"Gemini structured output failed: {e}")
            # Fallback: try without structured output
            return await self._discover_from_web_fallback(major, profile, student_type)
    
    async def _discover_from_web_fallback(
        self,
        major: str,
        profile: Dict[str, Any],
        student_type: str
    ) -> List[UniversityData]:
        """Fallback discovery without structured output (basic JSON parsing)."""
        gpa = profile.get("gpa", 3.5)
        nationality = profile.get("nationality", "international")
        is_domestic = student_type == "domestic"
        
        prompt = f"""Find 15 US universities for a {major} student with {gpa} GPA.
Student type: {"Domestic" if is_domestic else f"International from {nationality}"}

Return a JSON object with a "universities" array containing objects with these fields:
- name (string): Full university name
- acceptance_rate (number): Decimal 0-1, e.g. 0.15 for 15%
- median_gpa (number): Median GPA of admitted students
- sat_25th (integer): 25th percentile SAT
- sat_75th (integer): 75th percentile SAT
- major_strength_score (integer): 1-10 program strength for {major}
- need_blind_international (boolean): Need-blind for international students

Use the latest 2024/2025 admission data. Focus on {major} programs."""

        response = self.client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=3000,
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        
        return self._parse_structured_response(response.text or "", major)
    
    def _parse_structured_response(
        self,
        text: str,
        major: str
    ) -> List[UniversityData]:
        """
        Parse Gemini JSON response into structured UniversityData.
        
        Handles both structured output and fallback JSON formats.
        """
        universities = []
        
        try:
            # Parse JSON response
            data = json.loads(text)
            
            # Handle both direct list and nested object formats
            uni_list = data.get("universities", []) if isinstance(data, dict) else data
            
            for uni in uni_list:
                try:
                    universities.append(UniversityData(
                        name=uni.get("name", "Unknown University"),
                        acceptance_rate=float(uni.get("acceptance_rate", 0.5)),
                        median_gpa=float(uni.get("median_gpa", 3.5)),
                        sat_25th=int(uni.get("sat_25th", 1200)),
                        sat_75th=int(uni.get("sat_75th", 1400)),
                        major_ranking=uni.get("major_strength_score"),
                        need_blind_international=bool(uni.get("need_blind_international", False)),
                        data_source="gemini",
                        has_major=True,
                        student_major=major,
                    ))
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Skipping malformed university entry: {e}")
                    continue
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.debug(f"Raw response: {text[:500]}...")
        
        logger.info(f"Parsed {len(universities)} universities from LLM response")
        return universities
    
    async def _save_to_cache(self, uni_data: UniversityData) -> None:
        """Save a university to the cache (auto-population)."""
        # Determine data source based on current provider
        data_source = "ollama_simulated" if settings.llm_provider == "ollama" else "gemini"
        
        college_create = CollegeCreate(
            name=uni_data.name,
            acceptance_rate=uni_data.acceptance_rate,
            median_gpa=uni_data.median_gpa,
            sat_25th=uni_data.sat_25th,
            sat_75th=uni_data.sat_75th,
            need_blind_international=uni_data.need_blind_international or False,
            major_strength=uni_data.major_ranking,  # Store program strength
            data_source=data_source,
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
            major_ranking=college.major_strength,  # Read from cache
            data_source=college.data_source or "cache",
            has_major=True,
            student_major=major,
        )
