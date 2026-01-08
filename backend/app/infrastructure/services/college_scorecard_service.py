"""
College Scorecard Service

Fetches official IPEDS data from the College Scorecard API.
This provides verified admission statistics for US institutions.

API Docs: https://collegescorecard.ed.gov/data/documentation/
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ScorecardCollegeData:
    """Data returned from College Scorecard API."""
    ipeds_id: int
    name: str
    state: Optional[str] = None
    city: Optional[str] = None
    campus_setting: Optional[str] = None  # URBAN, SUBURBAN, RURAL
    acceptance_rate: Optional[float] = None
    sat_25th: Optional[int] = None
    sat_75th: Optional[int] = None
    act_25th: Optional[int] = None
    act_75th: Optional[int] = None
    tuition_in_state: Optional[float] = None
    tuition_out_of_state: Optional[float] = None
    student_size: Optional[int] = None


class CollegeScorecardService:
    """
    Service for fetching college data from the College Scorecard API.
    
    Uses official IPEDS data from the US Department of Education.
    Rate limit: 1000 requests/hour per IP.
    """
    
    BASE_URL = "https://api.data.gov/ed/collegescorecard/v1/schools"
    
    # Locale codes to campus setting mapping
    # 11-13: City, 21-23: Suburb, 31-33: Town, 41-43: Rural
    LOCALE_MAP = {
        11: "URBAN", 12: "URBAN", 13: "URBAN",
        21: "SUBURBAN", 22: "SUBURBAN", 23: "SUBURBAN",
        31: "SUBURBAN", 32: "SUBURBAN", 33: "SUBURBAN",  # Town = Suburban
        41: "RURAL", 42: "RURAL", 43: "RURAL",
    }
    
    def __init__(self):
        self.api_key = settings.college_scorecard_api_key
        if not self.api_key:
            logger.warning("COLLEGE_SCORECARD_API_KEY not configured")
    
    @property
    def _fields(self) -> str:
        """Fields to request from the API."""
        return ",".join([
            "id",
            "school.name",
            "school.state",
            "school.city",
            "school.locale",
            "latest.admissions.admission_rate.overall",
            "latest.admissions.sat_scores.25th_percentile.critical_reading",
            "latest.admissions.sat_scores.25th_percentile.math",
            "latest.admissions.sat_scores.75th_percentile.critical_reading",
            "latest.admissions.sat_scores.75th_percentile.math",
            "latest.admissions.act_scores.25th_percentile.cumulative",
            "latest.admissions.act_scores.75th_percentile.cumulative",
            "latest.cost.tuition.in_state",
            "latest.cost.tuition.out_of_state",
            "latest.student.size",
        ])
    
    async def search_by_name(self, name: str) -> Optional[ScorecardCollegeData]:
        """
        Search for a college by name.
        
        Returns the best match or None if not found.
        Prioritizes main campus over satellite campuses for multi-campus universities.
        Retries with alternative name formats if initial search fails.
        """
        if not self.api_key:
            logger.error("[SCORECARD] API key not configured")
            return None
        
        # Expand UC abbreviations FIRST
        expanded_name = name
        name_lower = name.lower().strip()
        if name_lower.startswith('uc ') and len(name_lower) > 3:
            # "UC Berkeley" -> "University of California-Berkeley"
            campus = name[3:].strip()
            expanded_name = f"University of California-{campus}"
        elif name_lower == 'ucla':
            expanded_name = "University of California-Los Angeles"
        elif name_lower == 'ucsd':
            expanded_name = "University of California-San Diego"
        elif name_lower == 'uci':
            expanded_name = "University of California-Irvine"
        elif name_lower == 'ucsb':
            expanded_name = "University of California-Santa Barbara"
        elif name_lower == 'ucsc':
            expanded_name = "University of California-Santa Cruz"
        elif name_lower == 'ucr':
            expanded_name = "University of California-Riverside"
        
        # Try different name formats - Scorecard API is picky about formatting
        name_variants = [
            expanded_name,
            name,  # Original name as fallback
            expanded_name.replace(", ", "-"),
            expanded_name.replace(",", "-"),
            expanded_name.replace("-", ", "),
        ]
        # Remove duplicates while preserving order
        name_variants = list(dict.fromkeys(name_variants))
        
        for variant in name_variants:
            result = await self._search_single(variant)
            if result:
                return result
        
        return None
    
    async def _search_single(self, name: str) -> Optional[ScorecardCollegeData]:
        """Search for a single name variant."""
        logger.info(f"[SCORECARD] Searching for '{name}'...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "api_key": self.api_key,
                        "school.name": name,
                        "fields": self._fields,
                        "per_page": 10,  # Get more results to find main campus
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                if not results:
                    logger.info(f"[SCORECARD] No results for '{name}'")
                    return None
                
                # Find the best match - prioritize by:
                # 1. Exact name match (for main campus)
                # 2. Largest student size (main campuses are typically larger)
                best_result = None
                name_lower = name.lower().strip()
                
                for result in results:
                    result_name = result.get("school.name", "").lower()
                    
                    # Exact match preferred
                    if result_name == name_lower or result_name == f"{name_lower}-main campus":
                        best_result = result
                        break
                    
                    # Check for "main campus" or "west lafayette" for Purdue
                    if "main campus" in result_name or "west lafayette" in result_name:
                        best_result = result
                        break
                    
                    # Check for flagship indicators
                    if "university park" in result_name:  # Penn State main
                        best_result = result
                        break
                
                # If no exact match, find largest by student size (main campus indicator)
                if not best_result:
                    results_with_size = [r for r in results if r.get("latest.student.size")]
                    if results_with_size:
                        best_result = max(results_with_size, key=lambda r: r.get("latest.student.size", 0))
                    else:
                        best_result = results[0]
                
                college = self._parse_result(best_result)
                logger.info(f"[SCORECARD] Found: {college.name} (IPEDS: {college.ipeds_id}, Size: {college.student_size})")
                return college
                
        except httpx.HTTPStatusError as e:
            # Don't log full HTML error, just status code
            logger.warning(f"[SCORECARD] HTTP {e.response.status_code} for '{name}'")
            return None
        except Exception as e:
            logger.error(f"[SCORECARD] Error searching for '{name}': {e}")
            return None
    
    async def get_by_ipeds_id(self, ipeds_id: int) -> Optional[ScorecardCollegeData]:
        """
        Get college data by IPEDS Unit ID.
        
        This is the most reliable way to fetch a specific institution.
        """
        if not self.api_key:
            return None
        
        logger.info(f"[SCORECARD] Fetching IPEDS ID {ipeds_id}...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "api_key": self.api_key,
                        "id": ipeds_id,
                        "fields": self._fields,
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                if not results:
                    return None
                
                return self._parse_result(results[0])
                
        except Exception as e:
            logger.error(f"[SCORECARD] Error fetching IPEDS {ipeds_id}: {e}")
            return None
    
    def _parse_result(self, result: Dict[str, Any]) -> ScorecardCollegeData:
        """Parse API result into ScorecardCollegeData."""
        
        # Calculate combined SAT scores (Reading + Math)
        sat_25th = None
        sat_75th = None
        
        reading_25 = result.get("latest.admissions.sat_scores.25th_percentile.critical_reading")
        math_25 = result.get("latest.admissions.sat_scores.25th_percentile.math")
        if reading_25 and math_25:
            sat_25th = reading_25 + math_25
        
        reading_75 = result.get("latest.admissions.sat_scores.75th_percentile.critical_reading")
        math_75 = result.get("latest.admissions.sat_scores.75th_percentile.math")
        if reading_75 and math_75:
            sat_75th = reading_75 + math_75
        
        # Map locale code to campus setting
        locale = result.get("school.locale")
        campus_setting = self.LOCALE_MAP.get(locale) if locale else None
        
        return ScorecardCollegeData(
            ipeds_id=result.get("id"),
            name=result.get("school.name"),
            state=result.get("school.state"),
            city=result.get("school.city"),
            campus_setting=campus_setting,
            acceptance_rate=result.get("latest.admissions.admission_rate.overall"),
            sat_25th=sat_25th,
            sat_75th=sat_75th,
            act_25th=result.get("latest.admissions.act_scores.25th_percentile.cumulative"),
            act_75th=result.get("latest.admissions.act_scores.75th_percentile.cumulative"),
            tuition_in_state=result.get("latest.cost.tuition.in_state"),
            tuition_out_of_state=result.get("latest.cost.tuition.out_of_state"),
            student_size=result.get("latest.student.size"),
        )
