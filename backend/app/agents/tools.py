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
    },
    # =========================================================================
    # College List Management Tools
    # =========================================================================
    {
        "type": "function",
        "function": {
            "name": "add_to_college_list",
            "description": "Add a college to the user's saved college list. Use when user says 'add X to my list' or 'save X'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "college_name": {
                        "type": "string",
                        "description": "Name of the college to add"
                    },
                    "label": {
                        "type": "string",
                        "enum": ["reach", "target", "safety"],
                        "description": "Category for the college"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes about this school"
                    }
                },
                "required": ["college_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_from_college_list",
            "description": "Remove a college from the user's saved list. Use when user says 'remove X from my list'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "college_name": {
                        "type": "string",
                        "description": "Name of the college to remove"
                    }
                },
                "required": ["college_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "exclude_college",
            "description": "Exclude a college from future recommendations. Use when user says 'never show me X again' or 'I'm not interested in X'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "college_name": {
                        "type": "string",
                        "description": "Name of the college to exclude"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Optional reason for exclusion"
                    }
                },
                "required": ["college_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_college_list",
            "description": "Get the user's saved college list. Use when user asks 'show my list' or 'what's in my college list'.",
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
            return await self._get_college_info(arguments, student_profile)
        
        elif tool_name == "get_student_profile":
            return self._get_student_profile(student_profile)
        
        # College List Management Tools
        elif tool_name == "add_to_college_list":
            return await self._add_to_college_list(arguments, student_profile)
        
        elif tool_name == "remove_from_college_list":
            return await self._remove_from_college_list(arguments, student_profile)
        
        elif tool_name == "exclude_college":
            return await self._exclude_college(arguments, student_profile)
        
        elif tool_name == "get_my_college_list":
            return await self._get_my_college_list(student_profile)
        
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
        
        # Calculate search limit based on requested counts (with buffer for filtering)
        total_requested = reach_count + target_count + safety_count
        search_limit = max(50, total_requested * 2)  # At least 50, or 2x requested
        
        # Step 1: Search for universities
        universities = await self.search_service.hybrid_search(
            major=major,
            profile=profile,
            student_type=student_type,
            limit=search_limit
        )
        
        if not universities:
            return {
                "success": False,
                "message": f"No colleges found for {major}",
                "colleges": []
            }
        
        # Step 2: Build student context for scoring
        context = StudentContext(
            is_domestic=student_type == "domestic",
            citizenship_status=profile.get("citizenship_status", "domestic" if student_type == "domestic" else "international"),
            nationality=profile.get("nationality"),
            state_of_residence=profile.get("state_of_residence"),
            gpa=profile.get("gpa", 3.5),
            sat_score=profile.get("sat_score"),
            act_score=profile.get("act_score"),
            intended_major=major,
            income_tier=profile.get("household_income_tier", "MEDIUM"),
            is_first_gen=profile.get("is_first_gen", False),
            campus_preference=profile.get("campus_vibe"),
            post_grad_goal=profile.get("post_grad_goal"),
            is_athlete=profile.get("is_student_athlete", False),
            has_legacy=profile.get("has_legacy_status", False),
            legacy_universities=profile.get("legacy_universities") or [],
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
    
    async def _get_college_info(
        self,
        args: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get DETAILED information about a specific college.
        
        Returns institutional data + major-specific stats if available.
        """
        name = args.get("name", "")
        major = profile.get("major", "Computer Science")
        
        if not name:
            return {"error": "College name is required"}
        
        # Try exact match first
        college = await self.college_repo.get_by_name(name)
        
        if not college:
            # Try fuzzy search
            colleges = await self.college_repo.search_by_name(name, limit=1)
            if colleges:
                college = colleges[0]
        
        if not college:
            return {
                "found": False,
                "name": name,
                "message": f"'{name}' is not in our database yet. You could ask for a new college list to discover this school."
            }
        
        # Get major-specific stats if available
        from app.infrastructure.db.repositories.college_repository import CollegeMajorStatsRepository
        
        # Build response with available data
        result = {
            "found": True,
            "name": college.name,
            "campus_setting": college.campus_setting,
            "state": college.state,
            "tuition_in_state": college.tuition_in_state,
            "tuition_out_of_state": college.tuition_out_of_state,
            "tuition_international": college.tuition_international,
            "need_blind_domestic": college.need_blind_domestic,
            "need_blind_international": college.need_blind_international,
            "meets_full_need": college.meets_full_need,
        }
        
        # Try to get major-specific stats
        try:
            college_with_stats = await self.college_repo.get_with_stats_by_name(
                college.name, major
            )
            if college_with_stats:
                result["major"] = major
                result["acceptance_rate"] = college_with_stats.acceptance_rate
                result["median_gpa"] = college_with_stats.median_gpa
                result["sat_25th"] = college_with_stats.sat_25th
                result["sat_75th"] = college_with_stats.sat_75th
                result["major_strength"] = college_with_stats.major_strength
        except Exception:
            # Major stats not available, still return institutional data
            pass
        
        return result
    
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
    
    # =========================================================================
    # College List Management Tool Implementations
    # =========================================================================
    
    async def _add_to_college_list(
        self, 
        args: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add a college to user's saved list."""
        from app.infrastructure.db.repositories.user_college_list_repository import (
            UserCollegeListRepository
        )
        from app.infrastructure.db.models.user_college_list import UserCollegeListItemCreate
        from app.infrastructure.db.database import get_session_context
        
        college_name = args.get("college_name", "")
        label = args.get("label")
        notes = args.get("notes")
        user_id = profile.get("user_id")
        
        if not college_name:
            return {"success": False, "message": "College name is required"}
        
        if not user_id:
            return {"success": False, "message": "User not authenticated"}
        
        try:
            async with get_session_context() as session:
                repo = UserCollegeListRepository(session)
                item = await repo.add(
                    user_id=user_id,
                    data=UserCollegeListItemCreate(
                        college_name=college_name,
                        label=label,
                        notes=notes,
                    )
                )
                await session.commit()
                
                return {
                    "success": True,
                    "message": f"Added {college_name} to your college list",
                    "college_name": item.college_name,
                    "label": item.label,
                }
        except Exception as e:
            logger.error(f"Error adding to college list: {e}")
            return {"success": False, "message": str(e)}
    
    async def _remove_from_college_list(
        self,
        args: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Remove a college from user's saved list."""
        from app.infrastructure.db.repositories.user_college_list_repository import (
            UserCollegeListRepository
        )
        from app.infrastructure.db.database import get_session_context
        
        college_name = args.get("college_name", "")
        user_id = profile.get("user_id")
        
        if not college_name:
            return {"success": False, "message": "College name is required"}
        
        if not user_id:
            return {"success": False, "message": "User not authenticated"}
        
        try:
            async with get_session_context() as session:
                repo = UserCollegeListRepository(session)
                removed = await repo.remove(user_id, college_name)
                await session.commit()
                
                if removed:
                    return {
                        "success": True,
                        "message": f"Removed {college_name} from your college list",
                    }
                else:
                    return {
                        "success": False,
                        "message": f"{college_name} was not in your list",
                    }
        except Exception as e:
            logger.error(f"Error removing from college list: {e}")
            return {"success": False, "message": str(e)}
    
    async def _exclude_college(
        self,
        args: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Exclude a college from future recommendations."""
        from app.infrastructure.db.repositories.user_college_list_repository import (
            UserExclusionRepository
        )
        from app.infrastructure.db.models.user_college_list import UserExclusionCreate
        from app.infrastructure.db.database import get_session_context
        
        college_name = args.get("college_name", "")
        reason = args.get("reason")
        user_id = profile.get("user_id")
        
        if not college_name:
            return {"success": False, "message": "College name is required"}
        
        if not user_id:
            return {"success": False, "message": "User not authenticated"}
        
        try:
            async with get_session_context() as session:
                repo = UserExclusionRepository(session)
                exclusion = await repo.add(
                    user_id=user_id,
                    data=UserExclusionCreate(
                        college_name=college_name,
                        reason=reason,
                    )
                )
                await session.commit()
                
                return {
                    "success": True,
                    "message": f"{college_name} will no longer appear in your recommendations",
                    "college_name": exclusion.college_name,
                }
        except Exception as e:
            logger.error(f"Error excluding college: {e}")
            return {"success": False, "message": str(e)}
    
    async def _get_my_college_list(
        self,
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get user's saved college list."""
        from app.infrastructure.db.repositories.user_college_list_repository import (
            UserCollegeListRepository
        )
        from app.infrastructure.db.database import get_session_context
        
        user_id = profile.get("user_id")
        
        if not user_id:
            return {"success": False, "message": "User not authenticated", "colleges": []}
        
        try:
            async with get_session_context() as session:
                repo = UserCollegeListRepository(session)
                items = await repo.get_all(user_id)
                
                # Group by label
                colleges = [
                    {
                        "name": item.college_name,
                        "label": item.label or "uncategorized",
                        "notes": item.notes,
                        "added_at": item.added_at.isoformat(),
                    }
                    for item in items
                ]
                
                return {
                    "success": True,
                    "total": len(colleges),
                    "colleges": colleges,
                }
        except Exception as e:
            logger.error(f"Error getting college list: {e}")
            return {"success": False, "message": str(e), "colleges": []}

