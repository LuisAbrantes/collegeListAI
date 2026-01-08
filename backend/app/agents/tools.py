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
            "description": "Get detailed information about a SPECIFIC college by name. ALWAYS use this when user asks about a particular school like 'tell me about X university'. Returns complete data including admission_category (Reach/Target/Safety) which is AUTO-CALCULATED based on acceptance rate - you MUST use this field, do NOT calculate categories yourself.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The exact name of the college (e.g., 'Stetson University', 'Reed College', 'MIT')"
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
            "description": "Add a college to the user's saved college list. The admission label (Reach/Target/Safety) is calculated AUTOMATICALLY based on acceptance rate - do NOT try to set it. Use when user says 'add X to my list' or 'save X'. IMPORTANT: Do NOT call exclude_college after adding - they are separate actions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "college_name": {
                        "type": "string",
                        "description": "Name of the college to add"
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
        major_stats_repository,
        scorer: MatchScorer
    ):
        self.search_service = college_search_service
        self.college_repo = college_repository
        self.stats_repo = major_stats_repository
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
            return await self._get_college_info(arguments, student_profile, student_type)
        
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
        profile: Dict[str, Any],
        student_type: str = "domestic"
    ) -> Dict[str, Any]:
        """
        Get DETAILED information about a specific college.
        
        Uses CollegeDataService for cache-first strategy with freshness checking.
        Returns complete institutional data from College Scorecard.
        """
        from app.infrastructure.services.college_data_service import CollegeDataService
        from app.infrastructure.services.college_scorecard_service import CollegeScorecardService
        
        name = args.get("name", "")
        
        if not name:
            return {"error": "College name is required"}
        
        logger.info(f"[TOOL] Executing get_college_info with args: {args}")
        
        # Use CollegeDataService for complete data with freshness checking
        scorecard_service = CollegeScorecardService()
        data_service = CollegeDataService(
            college_repo=self.college_repo,
            stats_repo=self.stats_repo,
            scorecard_service=scorecard_service,
        )
        
        dto = await data_service.get_college(name)
        
        if not dto:
            return {
                "found": False,
                "name": name,
                "message": f"Could not find '{name}' in US College databases. Please check the spelling or try the full official name."
            }
        
        # Calculate admission category based on acceptance rate
        admission_category = "Unknown"
        if dto.acceptance_rate is not None:
            if dto.acceptance_rate < 0.20:
                admission_category = "Reach"
            elif dto.acceptance_rate > 0.70:
                admission_category = "Safety"
            else:
                admission_category = "Target"
        
        # Return complete data from DTO
        result = {
            "found": True,
            "name": dto.name,
            "state": dto.state,
            "city": dto.city,
            "campus_setting": dto.campus_setting,
            "acceptance_rate": dto.acceptance_rate,
            "acceptance_rate_display": dto.acceptance_rate_percent,
            "admission_category": admission_category,  # Auto-calculated: Reach (<20%), Target (20-70%), Safety (>70%)
            "sat_range": dto.sat_range,
            "sat_25th": dto.sat_25th,
            "sat_75th": dto.sat_75th,
            "act_range": dto.act_range,
            "act_25th": dto.act_25th,
            "act_75th": dto.act_75th,
            "tuition_in_state": dto.tuition_in_state,
            "tuition_out_of_state": dto.tuition_out_of_state,
            "tuition_international": dto.tuition_international,
            "student_size": dto.student_size,
            "need_blind_domestic": dto.need_blind_domestic,
            "need_blind_international": dto.need_blind_international,
            "meets_full_need": dto.meets_full_need,
            "data_source": dto.data_source,
            "data_freshness": "current" if dto.is_fresh else "may be outdated",
        }
        
        logger.info(f"[TOOL] Returning college data: {dto.name} (source: {dto.data_source}, category: {admission_category})")
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
        
        # Validate college name - reject obvious invalid values
        invalid_names = [
            "this college", "this university", "that college", "that university",
            "it", "this", "that", "the college", "the university", "this one",
        ]
        if college_name.lower().strip() in invalid_names:
            return {
                "success": False, 
                "message": f"Please specify the actual college name. '{college_name}' is not a valid college name."
            }
        
        # Verify it looks like a real university name (at least 3 words or ends with University/College)
        words = college_name.split()
        if len(words) < 2 and not any(kw in college_name.lower() for kw in ["mit", "ucla", "nyu", "usc"]):
            return {
                "success": False,
                "message": f"'{college_name}' doesn't appear to be a valid college name."
            }
        
        if not user_id:
            return {"success": False, "message": "User not authenticated"}
        
        try:
            async with get_session_context() as session:
                # ALWAYS auto-calculate label based on acceptance rate - ignore any passed label
                calculated_label = None  # Force calculation
                
                # Try to calculate the correct label based on acceptance rate
                from app.domain.scoring.label_classifier import LabelClassifier
                from app.domain.scoring.interfaces import StudentContext, UniversityData
                from app.infrastructure.db.repositories.college_repository import CollegeRepository
                
                college_repo = CollegeRepository(session)
                college = await college_repo.get_by_name(college_name)
                
                if not college:
                    # Try fuzzy search
                    colleges = await college_repo.search_by_name(college_name, limit=1)
                    if colleges:
                        college = colleges[0]
                
                if college:
                    # Build context and university data for classification
                    student_ctx = StudentContext(
                        is_domestic=profile.get("citizenship_status", "international") != "international",
                        citizenship_status=profile.get("citizenship_status", "international"),
                        nationality=profile.get("nationality"),
                        gpa=profile.get("gpa", 3.5),
                        sat_score=profile.get("sat_score"),
                        act_score=profile.get("act_score"),
                        intended_major=profile.get("major", "Undeclared"),
                        income_tier=profile.get("household_income_tier", "MEDIUM"),
                        campus_preference=profile.get("campus_vibe"),
                    )
                    
                    # Get acceptance rate - try local first, then Scorecard, then fallback
                    local_rate = getattr(college, 'acceptance_rate', None)
                    logger.info(f"[TOOL] Local acceptance_rate for {college_name}: {local_rate} (type: {type(local_rate).__name__})")
                    
                    # Fallback rates for popular universities (2024-2025 data)
                    KNOWN_ACCEPTANCE_RATES = {
                        # UC System
                        "berkeley": 0.12,
                        "uc berkeley": 0.12,
                        "university of california, berkeley": 0.12,
                        "university of california-berkeley": 0.12,
                        "ucla": 0.09,
                        "uc los angeles": 0.09,
                        "university of california, los angeles": 0.09,
                        "university of california-los angeles": 0.09,
                        "uc san diego": 0.24,
                        "ucsd": 0.24,
                        "university of california, san diego": 0.24,
                        "university of california-san diego": 0.24,
                        "uc davis": 0.37,
                        "university of california, davis": 0.37,
                        "university of california-davis": 0.37,
                        "uc irvine": 0.21,
                        "uci": 0.21,
                        "university of california, irvine": 0.21,
                        "university of california-irvine": 0.21,
                        "uc santa barbara": 0.26,
                        "ucsb": 0.26,
                        "university of california, santa barbara": 0.26,
                        "university of california-santa barbara": 0.26,
                        "uc santa cruz": 0.47,
                        "ucsc": 0.47,
                        "university of california, santa cruz": 0.47,
                        "university of california-santa cruz": 0.47,
                        "uc riverside": 0.66,
                        "ucr": 0.66,
                        "university of california, riverside": 0.66,
                        "university of california-riverside": 0.66,
                        "uc merced": 0.89,
                        "university of california, merced": 0.89,
                        "university of california-merced": 0.89,
                        
                        # Purdue System
                        "purdue": 0.50,
                        "purdue university": 0.50,
                        "purdue university-main campus": 0.50,
                        "purdue fort wayne": 0.86,
                        "purdue university fort wayne": 0.86,
                        "purdue northwest": 0.71,
                        "purdue university northwest": 0.71,
                        
                        # Ivy League + Elite
                        "mit": 0.04,
                        "massachusetts institute of technology": 0.04,
                        "stanford": 0.04,
                        "stanford university": 0.04,
                        "harvard": 0.03,
                        "harvard university": 0.03,
                        "yale": 0.05,
                        "yale university": 0.05,
                        "princeton": 0.04,
                        "princeton university": 0.04,
                        "columbia": 0.04,
                        "columbia university": 0.04,
                        "upenn": 0.06,
                        "university of pennsylvania": 0.06,
                        "cornell": 0.07,
                        "cornell university": 0.07,
                        "duke": 0.06,
                        "duke university": 0.06,
                        "northwestern": 0.07,
                        "northwestern university": 0.07,
                        "carnegie mellon": 0.11,
                        "carnegie mellon university": 0.11,
                        "cmu": 0.11,
                        "usc": 0.12,
                        "university of southern california": 0.12,
                        "georgia tech": 0.16,
                        "georgia institute of technology": 0.16,
                        "university of michigan": 0.18,
                        "umich": 0.18,
                    }
                    
                    acceptance_rate = None
                    if local_rate and local_rate > 0:
                        acceptance_rate = local_rate
                    
                    if not acceptance_rate:
                        logger.info(f"[TOOL] No local rate, fetching from Scorecard...")
                        try:
                            from app.infrastructure.services.college_scorecard_service import CollegeScorecardService
                            scorecard = CollegeScorecardService()
                            scorecard_data = await scorecard.search_by_name(college_name)
                            if scorecard_data and scorecard_data.acceptance_rate:
                                acceptance_rate = scorecard_data.acceptance_rate
                                logger.info(f"[TOOL] Fetched acceptance rate from Scorecard: {acceptance_rate:.0%}")
                            else:
                                logger.warning(f"[TOOL] Scorecard returned no acceptance rate")
                        except Exception as sc_err:
                            logger.warning(f"[TOOL] Scorecard lookup failed: {sc_err}")
                    
                    # Fallback to known rates if still no acceptance rate
                    if not acceptance_rate:
                        import re
                        # Normalize name: remove parentheses, extra spaces, lowercase
                        name_lower = college_name.lower().strip()
                        name_normalized = re.sub(r'\s*\([^)]*\)', '', name_lower).strip()  # Remove (...)
                        name_normalized = re.sub(r'\s+', ' ', name_normalized)  # Collapse spaces
                        
                        # Try exact match first
                        acceptance_rate = KNOWN_ACCEPTANCE_RATES.get(name_lower)
                        
                        # Try normalized (without parentheses)
                        if not acceptance_rate:
                            acceptance_rate = KNOWN_ACCEPTANCE_RATES.get(name_normalized)
                        
                        # Try key parts (e.g., "berkeley" from "University of California, Berkeley")
                        if not acceptance_rate:
                            for key in KNOWN_ACCEPTANCE_RATES:
                                if key in name_lower or name_lower in key:
                                    acceptance_rate = KNOWN_ACCEPTANCE_RATES[key]
                                    break
                        
                        if acceptance_rate:
                            logger.info(f"[TOOL] Using fallback acceptance rate for {college_name}: {acceptance_rate:.0%}")
                    
                    uni_data = UniversityData(
                        name=college.name,
                        acceptance_rate=acceptance_rate,
                        sat_25th=getattr(college, 'sat_25th', None),
                        sat_75th=getattr(college, 'sat_75th', None),
                    )
                    
                    classifier = LabelClassifier()
                    label_result = classifier.classify(student_ctx, uni_data)
                    calculated_label = label_result.value  # "reach", "target", or "safety"
                    logger.info(f"[TOOL] Auto-calculated label for {college_name}: {calculated_label} (acceptance: {acceptance_rate:.0%})" if acceptance_rate else f"[TOOL] Label for {college_name}: {calculated_label} (no acceptance rate)")
                
                # Convert AdmissionLabel enum to lowercase string if needed
                if calculated_label and hasattr(calculated_label, 'value'):
                    calculated_label = calculated_label.value.lower()
                elif calculated_label:
                    calculated_label = str(calculated_label).lower()
                
                logger.info(f"[TOOL] Final label for {college_name}: {calculated_label}")
                
                repo = UserCollegeListRepository(session)
                item = await repo.add(
                    user_id=user_id,
                    data=UserCollegeListItemCreate(
                        college_name=college_name,
                        label=calculated_label,
                        notes=notes,
                    )
                )
                await session.commit()
                
                logger.info(f"[TOOL] Successfully saved {college_name} with label {item.label}")
                
                return {
                    "success": True,
                    "message": f"Added {college_name} to your college list as a {calculated_label.upper() if calculated_label else 'UNCATEGORIZED'} school",
                    "college_name": item.college_name,
                    "label": item.label,
                }
        except Exception as e:
            logger.error(f"Error adding to college list: {e}")
            import traceback
            logger.error(traceback.format_exc())
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

