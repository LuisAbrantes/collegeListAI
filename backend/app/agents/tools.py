"""
Agent Tools for College List AI

Defines tools (functions) that the LLM can call to get data.
Each tool wraps existing services - no logic duplication.

Design Patterns:
- Facade: Tools are simple interfaces to complex services
- Strategy: LLM chooses which tool to use
- Dependency Injection: Services passed at runtime
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from app.domain.scoring.interfaces import UniversityData, StudentContext
from app.domain.scoring.match_scorer import MatchScorer, ScoredUniversity
from app.infrastructure.services.college_search_service import CollegeSearchService
from app.infrastructure.db.repositories.college_repository import (
    CollegeRepository,
    CollegeMajorStatsRepository,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Tool Definitions (JSON Schema for Function Calling)
# =============================================================================

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_colleges",
            "description": "Search and score colleges for a major. Use when user wants a new college list or recommendations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "major": {
                        "type": "string",
                        "description": "The student's intended major (e.g., 'Computer Science', 'Economics')"
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of colleges to return (default 10)",
                        "default": 10
                    },
                    "reach_count": {
                        "type": "integer",
                        "description": "Number of Reach schools to include",
                        "default": 1
                    },
                    "target_count": {
                        "type": "integer",
                        "description": "Number of Target schools to include",
                        "default": 2
                    },
                    "safety_count": {
                        "type": "integer",
                        "description": "Number of Safety schools to include",
                        "default": 2
                    }
                },
                "required": ["major"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_college_info",
            "description": "Get detailed information about a specific college. Use when user asks about a particular school.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the college (e.g., 'MIT', 'Stanford University')"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_student_profile",
            "description": "Get the current student's profile including GPA, SAT, nationality, etc. Use when referencing student data.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]


# =============================================================================
# Tool Executor
# =============================================================================

class ToolExecutor:
    """
    Executes tools called by the LLM.
    
    Single Responsibility: Execute tool calls and return results.
    Facade: Wraps complex service interactions.
    """
    
    def __init__(
        self,
        college_search_service: CollegeSearchService,
        college_repository: CollegeRepository,
        scorer: MatchScorer
    ):
        self.search_service = college_search_service
        self.college_repo = college_repository
        self.scorer = scorer
    
    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        student_profile: Dict[str, Any],
        student_type: str
    ) -> Dict[str, Any]:
        """
        Execute a tool and return results.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments from LLM
            student_profile: Current student profile
            student_type: 'domestic' or 'international'
        
        Returns:
            Tool result as dict
        """
        logger.info(f"[TOOL] Executing {tool_name} with args: {arguments}")
        
        if tool_name == "search_colleges":
            return await self._search_colleges(arguments, student_profile, student_type)
        
        elif tool_name == "get_college_info":
            return await self._get_college_info(arguments)
        
        elif tool_name == "get_student_profile":
            return self._get_student_profile(student_profile)
        
        else:
            logger.warning(f"Unknown tool: {tool_name}")
            return {"error": f"Unknown tool: {tool_name}"}
    
    async def _search_colleges(
        self,
        args: Dict[str, Any],
        profile: Dict[str, Any],
        student_type: str
    ) -> Dict[str, Any]:
        """
        Search and score colleges.
        
        Wraps: CollegeSearchService.hybrid_search + MatchScorer.select_recommendations
        """
        # Get major from args, then profile. No hardcoded fallback.
        major = args.get("major") or profile.get("major")
        
        if not major:
            return {
                "success": False,
                "message": "Major is required. Please specify a major in your profile or request.",
                "colleges": []
            }
        
        reach_count = args.get("reach_count", 1)
        target_count = args.get("target_count", 2)
        safety_count = args.get("safety_count", 2)
        
        # Step 1: Search for universities
        universities = await self.search_service.hybrid_search(
            major=major,
            profile=profile,
            student_type=student_type,
            limit=20
        )
        
        if not universities:
            return {
                "success": False,
                "message": f"No colleges found for {major}",
                "colleges": []
            }
        
        # Step 2: Build student context for scoring
        context = StudentContext(
            gpa=profile.get("gpa", 3.5),
            sat_score=profile.get("sat_score"),
            act_score=profile.get("act_score"),
            intended_major=major,
            is_international=student_type == "international",
            household_income_tier=profile.get("household_income_tier"),
            preferred_region=None,
            preferred_setting=profile.get("campus_vibe"),
            is_athlete=profile.get("is_student_athlete", False),
            has_legacy=profile.get("has_legacy_status", False),
            legacy_universities=profile.get("legacy_universities"),
            is_first_gen=profile.get("is_first_gen", False),
        )
        
        # Step 3: Score and select recommendations
        counts = {
            "reach": reach_count,
            "target": target_count,
            "safety": safety_count
        }
        recommendations = self.scorer.select_recommendations(context, universities, counts)
        
        # Step 4: Format results
        colleges = []
        for rec in recommendations:
            colleges.append({
                "name": rec.university.name,
                "label": rec.label.value,
                "match_score": round(rec.match_score),
                "admission_probability": round(rec.admission_probability),
                "acceptance_rate": rec.university.acceptance_rate,
                "median_gpa": rec.university.median_gpa,
                "sat_range": f"{rec.university.sat_25th or '?'}-{rec.university.sat_75th or '?'}",
                "need_blind": rec.university.need_blind_international if student_type == "international" else rec.university.need_blind_domestic,
                "campus_setting": rec.university.campus_setting,
                "reasoning": rec.reasoning,
            })
        
        return {
            "success": True,
            "major": major,
            "student_type": student_type,
            "colleges": colleges
        }
    
    async def _get_college_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get details about a specific college.
        
        Wraps: CollegeRepository.get_by_name
        """
        name = args.get("name", "")
        
        if not name:
            return {"error": "College name is required"}
        
        # Search for college in cache
        college = await self.college_repo.get_by_name(name)
        
        if not college:
            # Try fuzzy search
            colleges = await self.college_repo.search_by_name(name, limit=1)
            if colleges:
                college = colleges[0]
        
        if not college:
            return {
                "found": False,
                "message": f"No information found for '{name}'. Try using search_colleges to get fresh data."
            }
        
        return {
            "found": True,
            "name": college.name,
            "acceptance_rate": college.acceptance_rate,
            "median_gpa": college.median_gpa,
            "tuition_in_state": college.tuition_in_state,
            "tuition_out_of_state": college.tuition_out_of_state,
            "tuition_international": college.tuition_international,
            "campus_setting": college.campus_setting,
            "state": college.state,
            "need_blind_domestic": college.need_blind_domestic,
            "need_blind_international": college.need_blind_international,
            "meets_full_need": college.meets_full_need,
        }
    
    def _get_student_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get current student profile.
        
        Simply returns the profile from state.
        """
        return {
            "gpa": profile.get("gpa"),
            "major": profile.get("major"),
            "minor": profile.get("minor"),
            "sat_score": profile.get("sat_score"),
            "act_score": profile.get("act_score"),
            "citizenship_status": profile.get("citizenship_status"),
            "nationality": profile.get("nationality"),
            "household_income_tier": profile.get("household_income_tier"),
            "campus_vibe": profile.get("campus_vibe"),
            "is_student_athlete": profile.get("is_student_athlete"),
            "has_legacy_status": profile.get("has_legacy_status"),
            "is_first_gen": profile.get("is_first_gen"),
        }
