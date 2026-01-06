"""
College Search Service for College List AI

Implements Hybrid LLM Pipeline for 429 resilience:
Phase 1: Local cache query (via JOINed tables)
Phase 2: Gemini raw web search → Ollama JSON structuring
Phase 3: Auto-populate cache (normalized relational upsert)
Phase 4: Return combined list for scoring

Architecture:
- Gemini (with Search Grounding): Fetches raw text from web sources
- Ollama (Gemma 3:27b local): Structures raw text into JSON schema
- Resilience: 429 retry with 40s backoff, then cache fallback
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import httpx
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.infrastructure.db.models.college import (
    College,
    CollegeCreate,
    CollegeMajorStats,
    CollegeMajorStatsCreate,
    CollegeWithMajorStats,
)
from app.infrastructure.db.repositories.college_repository import (
    CollegeRepository,
    CollegeMajorStatsRepository,
)
from app.domain.scoring import UniversityData

logger = logging.getLogger(__name__)

# Minimum fresh colleges before triggering web search
MIN_CACHE_THRESHOLD = 10

# Retry configuration for 429 errors
RETRY_WAIT_SECONDS = 40
MAX_RETRIES = 1


# ============== Structured Output Schemas ==============

class UniversityExtraction(BaseModel):
    """Schema for a single university extracted from structured response."""
    name: str = Field(..., description="Full university name")
    campus_setting: Optional[str] = Field(None, description="URBAN, SUBURBAN, or RURAL")
    acceptance_rate: float = Field(..., ge=0.0, le=1.0, description="Acceptance rate as decimal")
    median_gpa: float = Field(..., ge=0.0, le=4.0, description="Median GPA of admitted students")
    sat_25th: int = Field(..., ge=400, le=1600, description="25th percentile SAT score")
    sat_75th: int = Field(..., ge=400, le=1600, description="75th percentile SAT score")
    major_strength_score: int = Field(..., ge=1, le=10, description="Program strength 1-10")
    need_blind_international: bool = Field(..., description="Need-blind for internationals")
    meets_full_need: Optional[bool] = Field(False, description="Meets 100% demonstrated need")


class StructuredUniversityResponse(BaseModel):
    """Schema for structured response from Ollama."""
    universities: List[UniversityExtraction] = Field(..., description="List of universities")


class CollegeSearchService:
    """
    Hybrid search service implementing the Data Flywheel.
    
    TWO-PROVIDER ARCHITECTURE:
    ==========================
    
    SEARCH_PROVIDER (who performs web search):
    - perplexity: Perplexity Sonar API (recommended)
    - gemini: Google Gemini with Search Grounding
    
    SYNTHESIS_PROVIDER (who structures JSON):
    - groq: Groq Cloud API (fast, LLaMA 3.3)
    - perplexity: Perplexity Sonar (same API for everything)
    - ollama: Local Ollama (free, slower)
    """
    
    def __init__(
        self, 
        college_repository: CollegeRepository,
        major_stats_repository: CollegeMajorStatsRepository
    ):
        self.college_repo = college_repository
        self.stats_repo = major_stats_repository
        self._init_clients()
    
    def _init_clients(self):
        """Initialize clients based on provider settings."""
        # Gemini client (for search_provider == gemini)
        if settings.google_api_key:
            self.gemini_client = genai.Client(api_key=settings.google_api_key)
        else:
            self.gemini_client = None
        
        # Perplexity client (for search_provider == perplexity)
        if settings.perplexity_api_key:
            from openai import OpenAI
            self.perplexity_client = OpenAI(
                api_key=settings.perplexity_api_key,
                base_url="https://api.perplexity.ai"
            )
        else:
            self.perplexity_client = None
        
        # College Scorecard service (official IPEDS data)
        from app.infrastructure.services.college_scorecard_service import CollegeScorecardService
        self.scorecard_service = CollegeScorecardService()
        
        logger.info(
            f"Providers: search={settings.search_provider}, "
            f"synthesis={settings.synthesis_provider}, "
            f"scorecard={'enabled' if settings.college_scorecard_api_key else 'disabled'}"
        )

    
    async def hybrid_search(
        self,
        major: str,
        profile: Dict[str, Any],
        student_type: str,
        limit: int = 20,
        force_refresh: bool = False
    ) -> List[UniversityData]:
        """
        Execute hybrid search: cache-first, then ALWAYS discover new.
        
        DATA GROWTH STRATEGY:
        - Even with full cache, discover 3-5 NEW universities
        - Merge cached + discovered (deduplicated)
        - Ensures database keeps growing over time
        
        Args:
            major: Student's intended major
            profile: Student profile dict
            student_type: 'domestic' or 'international'
            limit: Max universities to return
            force_refresh: If True, bypass cache and force web discovery
            
        Returns:
            List of UniversityData ready for scoring
        """
        universities: List[UniversityData] = []
        
        # Force refresh mode: skip cache entirely
        if force_refresh:
            logger.info(f"FORCE REFRESH MODE: Bypassing cache for '{major}', fetching real data from web...")
            try:
                web_results = await self._discover_with_hybrid_pipeline(major, profile, student_type)
                
                # Phase 3: Auto-populate cache with fresh data
                logger.info(f"Phase 3: Auto-populating cache with {len(web_results)} fresh discoveries...")
                for uni_data in web_results:
                    await self._save_to_cache_relational(uni_data, major)
                    universities.append(uni_data)
                
                logger.info(f"FORCE REFRESH COMPLETE: {len(universities)} universities fetched and cached for '{major}'")
                return universities[:limit]
                
            except Exception as e:
                logger.error(f"Force refresh failed: {e}")
                logger.info("Falling back to cache after force refresh failure...")
        
        # Phase 1: Check local cache with Smart Correction for THIS MAJOR
        logger.info(f"Phase 1: Checking local cache for major '{major}' with Smart Correction...")
        fresh_count = await self.stats_repo.count_fresh_smart(
            current_provider="hybrid",  # New hybrid mode
            major_name=major
        )
        cached_colleges = await self.stats_repo.get_fresh_smart(
            current_provider="hybrid",
            major_name=major,
            limit=limit
        )
        
        logger.info(f"Found {fresh_count} fresh colleges for '{major}' in cache")
        
        # Get cached university names for exclusion
        cached_names = set()
        for college_with_stats in cached_colleges:
            uni_data = self._joined_to_university_data(college_with_stats)
            universities.append(uni_data)
            cached_names.add(uni_data.name.lower())
        
        # Phase 2: ALWAYS discover new universities (incremental growth)
        # Even with full cache, try to find 3-5 NEW universities
        should_discover = fresh_count < MIN_CACHE_THRESHOLD or fresh_count < 50  # Always grow until 50+
        
        if should_discover:
            logger.info(f"Phase 2: Discovering new universities for '{major}' (current: {fresh_count})...")
            
            try:
                web_results = await self._discover_with_hybrid_pipeline(major, profile, student_type)
                
                # Filter to only NEW universities (not in cache)
                new_universities = [
                    uni for uni in web_results 
                    if uni.name.lower() not in cached_names
                ]
                
                if new_universities:
                    logger.info(f"Phase 3: Found {len(new_universities)} NEW universities to add to cache!")
                    for uni_data in new_universities:
                        await self._save_to_cache_relational(uni_data, major)
                        universities.append(uni_data)
                else:
                    logger.info("No new universities found (all already in cache)")
                
            except Exception as e:
                logger.warning(f"Incremental discovery failed: {e}. Using cache only.")
        else:
            logger.info(f"Cache mature ({fresh_count} universities), skipping discovery")
        
        # Deduplicate by name (case-insensitive)
        seen = set()
        unique = []
        for uni in universities:
            name_lower = uni.name.lower()
            if name_lower not in seen:
                seen.add(name_lower)
                unique.append(uni)
        
        logger.info(f"Phase 4: Returning {len(unique)} universities for scoring")
        return unique[:limit]
    
    async def discover_single_university(
        self,
        university_name: str,
        major: str,
        profile: Dict[str, Any],
        student_type: str
    ) -> Optional[UniversityData]:
        """
        Discover a SPECIFIC university and save to database.
        
        Priority:
        1. College Scorecard API (official IPEDS data) - US universities
        2. Perplexity fallback (for non-US or missing data)
        
        Returns:
            UniversityData if found, None if not discoverable
        """
        logger.info(f"[DISCOVERY] Looking up '{university_name}'...")
        
        try:
            # ============================================================
            # PHASE 1: Try College Scorecard API (official IPEDS data)
            # ============================================================
            scorecard_data = await self.scorecard_service.search_by_name(university_name)
            
            if scorecard_data:
                logger.info(f"[DISCOVERY] Found in College Scorecard: {scorecard_data.name} (IPEDS: {scorecard_data.ipeds_id})")
                
                # Convert to UniversityData
                uni_data = UniversityData(
                    name=scorecard_data.name,
                    acceptance_rate=scorecard_data.acceptance_rate,
                    sat_25th=scorecard_data.sat_25th,
                    sat_75th=scorecard_data.sat_75th,
                    campus_setting=scorecard_data.campus_setting,
                    state=scorecard_data.state,
                    tuition_in_state=scorecard_data.tuition_in_state,
                    tuition_out_of_state=scorecard_data.tuition_out_of_state,
                    has_major=True,  # Will verify with program data later
                    student_major=major,
                    data_source="college_scorecard",
                )
                
                # Upsert by IPEDS ID to prevent duplicates
                await self._upsert_by_ipeds_id(scorecard_data, major)
                
                return uni_data
            
            # ============================================================
            # PHASE 2: Fallback to Perplexity (non-US or not in Scorecard)
            # ============================================================
            logger.info(f"[DISCOVERY] Not in Scorecard, trying Perplexity fallback...")
            
            if not self.perplexity_client:
                logger.warning("[DISCOVERY] No Perplexity client available")
                return None
            
            system_msg = """You are a college data API. Output ONLY valid JSON.
Never explain. If you don't have data, estimate based on similar schools."""

            user_msg = f"""Return admission data for {university_name} as JSON:
{{"name": "Official Name", "acceptance_rate": 0.XX, "sat_25th": XXXX, "sat_75th": XXXX, "campus_setting": "URBAN/SUBURBAN/RURAL", "state": "XX"}}"""
            
            response = await asyncio.to_thread(
                self.perplexity_client.chat.completions.create,
                model="sonar-pro",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
            )
            response_text = response.choices[0].message.content
            logger.info(f"[DISCOVERY] Perplexity response: {response_text[:300]}")
            
            # Parse JSON
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                logger.warning("[DISCOVERY] No JSON in Perplexity response")
                return None
            
            data = json.loads(response_text[start_idx : end_idx + 1])
            
            # Sanitize and create UniversityData
            uni_data = UniversityData(
                name=data.get("name", university_name),
                acceptance_rate=data.get("acceptance_rate") if data.get("acceptance_rate", 0) > 0 else None,
                sat_25th=data.get("sat_25th") if data.get("sat_25th", 0) >= 400 else None,
                sat_75th=data.get("sat_75th") if data.get("sat_75th", 0) >= 400 else None,
                campus_setting=data.get("campus_setting"),
                state=data.get("state"),
                has_major=True,
                student_major=major,
                data_source="perplexity_fallback",
            )
            
            # Save to cache (no IPEDS ID for non-Scorecard data)
            await self._save_to_cache_relational(uni_data, major)
            
            logger.info(f"[DISCOVERY] Saved from Perplexity: {uni_data.name}")
            return uni_data
            
        except Exception as e:
            logger.error(f"[DISCOVERY] Failed for '{university_name}': {e}", exc_info=True)
            return None
    
    async def _upsert_by_ipeds_id(self, scorecard_data, major: str):
        """Upsert college by IPEDS ID to prevent duplicates."""
        from app.infrastructure.db.models.college import CollegeCreate, CollegeMajorStatsCreate
        
        # Check if exists by IPEDS ID
        existing = await self.college_repo.get_by_ipeds_id(scorecard_data.ipeds_id)
        
        if existing:
            # Update existing record
            logger.info(f"[UPSERT] Updating existing: {existing.name} (IPEDS: {scorecard_data.ipeds_id})")
            existing.acceptance_rate = scorecard_data.acceptance_rate
            existing.sat_25th = scorecard_data.sat_25th
            existing.sat_75th = scorecard_data.sat_75th
            existing.campus_setting = scorecard_data.campus_setting
            existing.tuition_in_state = scorecard_data.tuition_in_state
            existing.tuition_out_of_state = scorecard_data.tuition_out_of_state
            await self.college_repo.update(existing)
        else:
            # Insert new record
            logger.info(f"[UPSERT] Inserting new: {scorecard_data.name} (IPEDS: {scorecard_data.ipeds_id})")
            college_data = CollegeCreate(
                name=scorecard_data.name,
                ipeds_id=scorecard_data.ipeds_id,
                state=scorecard_data.state,
                campus_setting=scorecard_data.campus_setting,
                tuition_in_state=scorecard_data.tuition_in_state,
                tuition_out_of_state=scorecard_data.tuition_out_of_state,
            )
            college = await self.college_repo.create(college_data)
            
            # Add major stats if we have SAT data
            if scorecard_data.sat_25th and scorecard_data.sat_75th:
                stats_data = CollegeMajorStatsCreate(
                    college_id=college.id,
                    target_major=major,
                    acceptance_rate=scorecard_data.acceptance_rate,
                    sat_25th=scorecard_data.sat_25th,
                    sat_75th=scorecard_data.sat_75th,
                )
                await self.stats_repo.create(stats_data)

    
    async def _discover_with_hybrid_pipeline(
        self,
        major: str,
        profile: Dict[str, Any],
        student_type: str
    ) -> List[UniversityData]:
        """
        TWO-PROVIDER PIPELINE:
        
        Step 1: SEARCH (search_provider)
        - perplexity: Perplexity Sonar API
        - gemini: Google Gemini with Search Grounding
        
        Step 2: SYNTHESIS (synthesis_provider)
        - groq: Groq Cloud API (fast)
        - perplexity: Perplexity Sonar (same API)
        - ollama: Local Ollama (free)
        """
        # ======================
        # STEP 1: WEB SEARCH
        # ======================
        raw_text = None
        data_source = settings.search_provider
        
        if settings.search_provider == "perplexity":
            logger.info("[SEARCH] Using Perplexity Sonar...")
            raw_text = await self._perplexity_raw_search_with_retry(major, profile, student_type)
            
        elif settings.search_provider == "gemini":
            logger.info("[SEARCH] Using Gemini with Search Grounding...")
            raw_text = await self._gemini_raw_search_with_retry(major, profile, student_type)
        
        # Search failed - fallback to Ollama standalone
        if not raw_text:
            logger.warning(f"[SEARCH] {settings.search_provider} failed, using Ollama standalone")
            return await self._ollama_standalone_discovery(major, profile, student_type)
        
        # ======================
        # STEP 2: SYNTHESIS (JSON structuring)
        # ======================
        if settings.synthesis_provider == "groq":
            logger.info(f"[SYNTHESIS] Groq structuring {data_source} data...")
            return await self._groq_structure_text(raw_text, major, data_source)
            
        elif settings.synthesis_provider == "perplexity":
            logger.info(f"[SYNTHESIS] Perplexity structuring {data_source} data...")
            return await self._perplexity_structure_text(raw_text, major, data_source)
            
        else:  # ollama
            logger.info(f"[SYNTHESIS] Ollama structuring {data_source} data...")
            return await self._ollama_structure_text(raw_text, major, data_source)
    
    async def _perplexity_raw_search_with_retry(
        self,
        major: str,
        profile: Dict[str, Any],
        student_type: str
    ) -> Optional[str]:
        """
        Perplexity Sonar API for web search (RAW TEXT output).
        
        Uses OpenAI-compatible API format.
        Includes retry logic for 429 rate limits.
        """
        gpa = profile.get("gpa", 3.5)
        is_domestic = student_type == "domestic"
        nationality = profile.get("nationality", "US" if is_domestic else "Unknown")
        
        prompt = f"""Research the LATEST college admission statistics for {major} programs.

Student Profile:
- GPA: {gpa}/4.0
- Type: {"Domestic US" if is_domestic else f"International from {nationality}"}

Find 15 US universities with strong {major} programs. Include:
- 3-4 highly selective (acceptance rate < 20%)
- 5-6 moderately selective (20-50% acceptance rate)
- 5-6 accessible options (> 50% acceptance rate)

For EACH university, provide in a clear format:
1. Full official university name
2. Campus setting (Urban, Suburban, or Rural)
3. Overall acceptance rate (as a percentage)
4. Median GPA of admitted students
5. SAT score range (25th and 75th percentile)
6. Program strength rating for {major} (1-10 scale)
7. Need-blind policy for international students (Yes/No)
8. Whether they meet 100% of demonstrated financial need (Yes/No)

Use the most recent 2024/2025 admission data available."""

        for attempt in range(MAX_RETRIES + 1):
            try:
                logger.info(f"Perplexity search attempt {attempt + 1}/{MAX_RETRIES + 1}...")
                
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        "https://api.perplexity.ai/chat/completions",
                        headers={
                            "Authorization": f"Bearer {settings.perplexity_api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": settings.perplexity_model,
                            "messages": [
                                {"role": "user", "content": prompt}
                            ],
                        },
                    )
                    
                    if response.status_code == 429:
                        if attempt < MAX_RETRIES:
                            logger.warning(f"Perplexity 429 rate limit. Waiting {RETRY_WAIT_SECONDS}s...")
                            await asyncio.sleep(RETRY_WAIT_SECONDS)
                            continue
                        else:
                            logger.error("Perplexity 429 after all retries")
                            return None
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    raw_text = data["choices"][0]["message"]["content"]
                    logger.info(f"Perplexity returned {len(raw_text)} characters")
                    return raw_text
                    
            except httpx.HTTPError as e:
                logger.error(f"Perplexity API error: {e}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_WAIT_SECONDS)
                    continue
                return None
            except (KeyError, IndexError) as e:
                logger.error(f"Perplexity response parsing error: {e}")
                return None
        
        return None
    
    async def _gemini_raw_search_with_retry(
        self,
        major: str,
        profile: Dict[str, Any],
        student_type: str
    ) -> Optional[str]:
        """
        Gemini Search Grounding for RAW TEXT (no JSON).
        
        Includes 429 resilience: wait 40s and retry once.
        """
        if not self.gemini_client:
            logger.warning("Gemini client not initialized, skipping web search")
            return None
        
        gpa = profile.get("gpa", 3.5)
        is_domestic = student_type == "domestic"
        nationality = profile.get("nationality", "US" if is_domestic else "Unknown")
        
        # Prompt for RAW TEXT output (NOT JSON)
        prompt = f"""Research the LATEST college admission statistics for {major} programs.

Student Profile:
- GPA: {gpa}/4.0
- Type: {"Domestic US" if is_domestic else f"International from {nationality}"}

Find 15 US universities with strong {major} programs. Include:
- 3-4 highly selective (acceptance rate < 20%)
- 5-6 moderately selective (20-50% acceptance rate)
- 5-6 accessible options (> 50% acceptance rate)

For EACH university, provide the following information in a clear format:
1. Full official university name
2. Campus setting (Urban, Suburban, or Rural)
3. Overall acceptance rate (as a percentage)
4. Median GPA of admitted students
5. SAT score range (25th and 75th percentile)
6. Program strength rating for {major} (1-10 scale)
7. Need-blind policy for international students (Yes/No)
8. Whether they meet 100% of demonstrated financial need (Yes/No)

Use the most recent 2024/2025 admission data available. Present the information clearly."""

        for attempt in range(MAX_RETRIES + 1):
            try:
                logger.info(f"Gemini raw search attempt {attempt + 1}/{MAX_RETRIES + 1}...")
                
                response = self.gemini_client.models.generate_content(
                    model=settings.gemini_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        max_output_tokens=4000,
                        # NO response_mime_type or response_schema - raw text only
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )
                )
                
                raw_text = response.text or ""
                logger.info(f"Gemini returned {len(raw_text)} characters of raw text")
                return raw_text
                
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    if attempt < MAX_RETRIES:
                        logger.warning(f"Gemini 429 rate limit hit. Waiting {RETRY_WAIT_SECONDS}s before retry...")
                        await asyncio.sleep(RETRY_WAIT_SECONDS)
                        continue
                    else:
                        logger.error(f"Gemini 429 after {MAX_RETRIES + 1} attempts. Using cache fallback.")
                        return None
                else:
                    logger.error(f"Gemini error: {e}")
                    raise
        
        return None
    
    async def _ollama_structure_text(
        self,
        raw_text: str,
        major: str,
        data_source: str = "hybrid"
    ) -> List[UniversityData]:
        """
        Use local Ollama to structure raw text into JSON.
        
        Args:
            raw_text: Unstructured text from search provider
            major: Student's intended major
            data_source: Which provider fetched the data (perplexity/gemini)
        """
        structuring_prompt = f"""You are a data extraction assistant. Extract university information from the following text and format it as valid JSON.

RAW TEXT:
{raw_text}

IMPORTANT: Extract ALL universities mentioned and format them according to this EXACT JSON schema:
{{
  "universities": [
    {{
      "name": "Full University Name",
      "campus_setting": "URBAN" | "SUBURBAN" | "RURAL",
      "acceptance_rate": 0.15,
      "median_gpa": 3.9,
      "sat_25th": 1400,
      "sat_75th": 1550,
      "major_strength_score": 8,
      "need_blind_international": false,
      "meets_full_need": false
    }}
  ]
}}

RULES:
1. acceptance_rate must be a decimal between 0 and 1 (e.g., 15% → 0.15)
2. median_gpa must be between 0.0 and 4.0
3. SAT scores must be between 400 and 1600
4. major_strength_score must be an integer from 1 to 10
5. If data is missing, use reasonable estimates based on the university's selectivity
6. campus_setting must be exactly "URBAN", "SUBURBAN", or "RURAL"

CRITICAL - NEED-BLIND POLICY:
- need_blind_international should be TRUE ONLY for these confirmed schools: Harvard, Yale, Princeton, MIT, Amherst, Dartmouth, Bowdoin
- For ALL other schools, default to FALSE unless explicitly stated otherwise
- Most public universities (like Penn State, UC schools, state universities) are NOT need-blind for international students
- When in doubt, use FALSE

Return ONLY the valid JSON object, nothing else."""

        try:
            logger.info(f"Ollama is structuring the {data_source} response...")
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": structuring_prompt,
                        "format": "json",
                        "stream": False,
                    },
                )
                response.raise_for_status()
                result = response.json()
                json_text = result.get("response", "")
                
                return self._parse_structured_response(json_text, major, data_source=data_source)
                
        except httpx.HTTPError as e:
            logger.error(f"Ollama structuring failed: {e}")
            # Try to parse anything useful from the raw text
            return self._fallback_parse_raw_text(raw_text, major)
    
    async def _groq_structure_text(
        self,
        raw_text: str,
        major: str,
        data_source: str = "perplexity"
    ) -> List[UniversityData]:
        """
        Use Groq API to structure raw text into JSON.
        
        Groq provides fast inference (~500 tokens/s) with LLaMA 3.3 70B.
        Uses OpenAI-compatible API format.
        """
        structuring_prompt = f"""You are a data extraction assistant. Extract university information from the following text and format it as valid JSON.

RAW TEXT:
{raw_text}

OUTPUT FORMAT (JSON):
{{
  "universities": [
    {{
      "name": "University Name",
      "campus_setting": "URBAN" | "SUBURBAN" | "RURAL",
      "acceptance_rate": 0.15,
      "median_gpa": 3.9,
      "sat_25th": 1400,
      "sat_75th": 1550,
      "major_strength_score": 8,
      "need_blind_international": false,
      "meets_full_need": false
    }}
  ]
}}

RULES:
1. acceptance_rate must be a decimal between 0 and 1 (e.g., 15% → 0.15)
2. median_gpa must be between 0.0 and 4.0
3. SAT scores must be between 400 and 1600 (use 0 if unknown)
4. major_strength_score must be an integer from 1 to 10
5. campus_setting must be exactly "URBAN", "SUBURBAN", or "RURAL"

CRITICAL - NEED-BLIND POLICY:
- need_blind_international = TRUE ONLY for: Harvard, Yale, Princeton, MIT, Amherst, Dartmouth, Bowdoin
- ALL other schools (especially public universities like Penn State, UC schools) = FALSE
- When in doubt, use FALSE

Return ONLY the valid JSON object."""

        try:
            logger.info(f"Groq is structuring the {data_source} response...")
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.groq_model,
                        "messages": [
                            {"role": "user", "content": structuring_prompt}
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.1,
                    },
                )
                
                if response.status_code == 429:
                    logger.warning("Groq rate limit hit, falling back to Ollama...")
                    return await self._ollama_structure_text(raw_text, major, data_source)
                
                response.raise_for_status()
                data = response.json()
                json_text = data["choices"][0]["message"]["content"]
                
                logger.info(f"Groq structured response received")
                return self._parse_structured_response(json_text, major, data_source=data_source)
                
        except httpx.HTTPError as e:
            logger.error(f"Groq structuring failed: {e}, falling back to Ollama...")
            return await self._ollama_structure_text(raw_text, major, data_source)
        except (KeyError, IndexError) as e:
            logger.error(f"Groq response parsing error: {e}")
            return self._fallback_parse_raw_text(raw_text, major)
    
    async def _perplexity_structure_text(
        self,
        raw_text: str,
        major: str,
        data_source: str = "perplexity"
    ) -> List[UniversityData]:
        """
        Use Perplexity Sonar to structure raw text into JSON.
        
        For Production: Use same Perplexity API for both search AND synthesis.
        This simplifies the architecture (one vendor, one API key).
        """
        structuring_prompt = f"""You are a data extraction assistant. Extract university information from the following text and format it as valid JSON.

RAW TEXT:
{raw_text}

OUTPUT FORMAT (JSON):
{{
  "universities": [
    {{
      "name": "University Name",
      "campus_setting": "URBAN" | "SUBURBAN" | "RURAL",
      "acceptance_rate": 0.15,
      "median_gpa": 3.9,
      "sat_25th": 1400,
      "sat_75th": 1550,
      "major_strength_score": 8,
      "need_blind_international": true,
      "meets_full_need": true
    }}
  ]
}}

RULES:
1. acceptance_rate must be a decimal between 0 and 1 (e.g., 15% → 0.15)
2. median_gpa must be between 0.0 and 4.0
3. SAT scores must be between 400 and 1600 (use 0 if unknown)
4. major_strength_score must be an integer from 1 to 10
5. campus_setting must be exactly "URBAN", "SUBURBAN", or "RURAL"

Return ONLY the valid JSON object."""

        try:
            logger.info(f"Perplexity is structuring the {data_source} response...")
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.perplexity_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.perplexity_model,
                        "messages": [
                            {"role": "user", "content": structuring_prompt}
                        ],
                        "temperature": 0.1,
                    },
                )
                
                if response.status_code == 429:
                    logger.warning("Perplexity rate limit hit, falling back to Ollama...")
                    return await self._ollama_structure_text(raw_text, major, data_source)
                
                response.raise_for_status()
                data = response.json()
                json_text = data["choices"][0]["message"]["content"]
                
                logger.info("Perplexity structured response received")
                return self._parse_structured_response(json_text, major, data_source=data_source)
                
        except httpx.HTTPError as e:
            logger.error(f"Perplexity structuring failed: {e}, falling back to Ollama...")
            return await self._ollama_structure_text(raw_text, major, data_source)
        except (KeyError, IndexError) as e:
            logger.error(f"Perplexity response parsing error: {e}")
            return self._fallback_parse_raw_text(raw_text, major)
    
    async def _ollama_standalone_discovery(
        self,
        major: str,
        profile: Dict[str, Any],
        student_type: str
    ) -> List[UniversityData]:
        """
        Fallback: Use Ollama alone for simulated discovery.
        
        Used when Gemini is completely unavailable.
        """
        gpa = profile.get("gpa", 3.5)
        is_domestic = student_type == "domestic"
        nationality = profile.get("nationality", "US" if is_domestic else "Unknown")
        
        prompt = f"""You are simulating an expert college admissions database.

Generate realistic 2025 admission data for 15 US universities with strong {major} programs.

Student Profile:
- GPA: {gpa}/4.0  
- Type: {"Domestic US" if is_domestic else f"International from {nationality}"}

Include a diverse mix:
- 3-4 highly selective (acceptance rate < 20%)
- 5-6 moderately selective (20-50%)
- 5-6 accessible options (> 50%)

Return ONLY valid JSON matching this exact schema:
{{
  "universities": [
    {{
      "name": "Full University Name",
      "campus_setting": "URBAN",
      "acceptance_rate": 0.15,
      "median_gpa": 3.9,
      "sat_25th": 1400,
      "sat_75th": 1550,
      "major_strength_score": 8,
      "need_blind_international": true,
      "meets_full_need": true
    }}
  ]
}}"""

        try:
            logger.info("Ollama standalone mode: generating simulated data...")
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
                return self._parse_structured_response(
                    result.get("response", ""), 
                    major, 
                    data_source="ollama_simulated"
                )
        except httpx.HTTPError as e:
            logger.error(f"Ollama standalone failed: {e}")
            raise RuntimeError(f"Ollama discovery failed: {e}")
    
    def _parse_structured_response(
        self,
        text: str,
        major: str,
        data_source: str = "hybrid"
    ) -> List[UniversityData]:
        """
        Parse JSON response into structured UniversityData.
        
        Handles normalized schema with both institutional and major-specific data.
        SAT scores of 0 or out of valid range (400-1600) are replaced with None.
        """
        universities = []
        
        def validate_sat(score) -> Optional[int]:
            """Validate SAT score - must be 400-1600, else None."""
            try:
                val = int(score) if score else 0
                return val if 400 <= val <= 1600 else None
            except (ValueError, TypeError):
                return None
        
        try:
            data = json.loads(text)
            uni_list = data.get("universities", []) if isinstance(data, dict) else data
            
            for uni in uni_list:
                try:
                    # Validate SAT scores (0 or out-of-range becomes None)
                    sat_25 = validate_sat(uni.get("sat_25th"))
                    sat_75 = validate_sat(uni.get("sat_75th"))
                    
                    uni_name = uni.get("name", "Unknown University")
                    
                    universities.append(UniversityData(
                        name=uni_name,
                        acceptance_rate=float(uni.get("acceptance_rate", 0.5)),
                        median_gpa=float(uni.get("median_gpa", 3.5)),
                        sat_25th=sat_25,
                        sat_75th=sat_75,
                        major_ranking=uni.get("major_strength_score"),
                        need_blind_international=bool(uni.get("need_blind_international", False)),
                        data_source=data_source,
                        has_major=True,
                        student_major=major,
                        # New fields for normalized schema
                        campus_setting=uni.get("campus_setting"),
                        meets_full_need=bool(uni.get("meets_full_need", False)),
                    ))
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Skipping malformed university entry: {e}")
                    continue
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {text[:500]}...")
        
        logger.info(f"Parsed {len(universities)} universities from {data_source} response")
        return universities
    
    def _fallback_parse_raw_text(
        self,
        raw_text: str,
        major: str
    ) -> List[UniversityData]:
        """
        Emergency fallback: Extract university names from raw text.
        
        Used if both Gemini structuring and Ollama fail.
        """
        # Known top universities as fallback
        known_universities = [
            "Massachusetts Institute of Technology",
            "Stanford University", 
            "Carnegie Mellon University",
            "University of California, Berkeley",
            "Georgia Institute of Technology",
            "University of Illinois Urbana-Champaign",
            "University of Michigan",
            "Cornell University",
            "University of Texas at Austin",
            "Purdue University",
        ]
        
        universities = []
        for name in known_universities:
            if name.lower() in raw_text.lower():
                universities.append(UniversityData(
                    name=name,
                    acceptance_rate=0.2,  # Default estimate
                    median_gpa=3.7,
                    sat_25th=1350,
                    sat_75th=1520,
                    major_ranking=8,
                    need_blind_international=False,
                    data_source="fallback",
                    has_major=True,
                    student_major=major,
                ))
        
        logger.warning(f"Fallback parser extracted {len(universities)} known universities")
        return universities
    
    async def _save_to_cache_relational(
        self, 
        uni_data: UniversityData, 
        major: str
    ) -> None:
        """
        RELATIONAL UPSERT: Save to normalized tables.
        
        Step 1: Upsert College (institutional data) → get college.id
        Step 2: Upsert CollegeMajorStats (major-specific) with college_id FK
        """
        # Step 1: Upsert institutional data to colleges table
        college_data = CollegeCreate(
            name=uni_data.name,
            campus_setting=getattr(uni_data, 'campus_setting', None),
            need_blind_international=uni_data.need_blind_international or False,
            meets_full_need=getattr(uni_data, 'meets_full_need', False),
        )
        college, created = await self.college_repo.get_or_create(college_data)
        
        if created:
            logger.debug(f"Created new college: {college.name}")
        else:
            # Update institutional data if changed
            if hasattr(uni_data, 'campus_setting') and uni_data.campus_setting:
                college.campus_setting = uni_data.campus_setting
            if uni_data.need_blind_international is not None:
                college.need_blind_international = uni_data.need_blind_international
            if hasattr(uni_data, 'meets_full_need'):
                college.meets_full_need = getattr(uni_data, 'meets_full_need', False)
        
        # Step 2: Upsert major-specific stats with FK reference
        stats_data = CollegeMajorStatsCreate(
            college_id=college.id,
            major_name=major,
            acceptance_rate=uni_data.acceptance_rate,
            median_gpa=uni_data.median_gpa,
            sat_25th=uni_data.sat_25th,
            sat_75th=uni_data.sat_75th,
            major_strength=uni_data.major_ranking,
            data_source=uni_data.data_source or "hybrid",
        )
        await self.stats_repo.upsert(college.id, stats_data)
        
        logger.debug(f"Cached {college.name} stats for {major}")
    
    def _joined_to_university_data(
        self,
        college_with_stats: CollegeWithMajorStats
    ) -> UniversityData:
        """Convert JOINed result to UniversityData for scoring."""
        return UniversityData(
            name=college_with_stats.name,
            acceptance_rate=college_with_stats.acceptance_rate,
            median_gpa=college_with_stats.median_gpa,
            sat_25th=college_with_stats.sat_25th,
            sat_75th=college_with_stats.sat_75th,
            need_blind_international=college_with_stats.need_blind_international,
            major_ranking=college_with_stats.major_strength,
            data_source=college_with_stats.data_source or "cache",
            has_major=True,
            student_major=college_with_stats.major_name,
        )
