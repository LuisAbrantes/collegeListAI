"""
Scorer Node for College List AI

Scores and classifies universities using the domain scoring engine.
NO HARDCODED FALLBACK - relies entirely on cache + Gemini Search.
"""

import logging
from typing import Dict, Any, List

from app.agents.state import RecommendationAgentState
from app.domain.scoring import (
    MatchScorer,
    StudentContext,
    UniversityData,
    ScoredUniversity,
)

logger = logging.getLogger(__name__)


def build_student_context(state: RecommendationAgentState) -> StudentContext:
    """Build StudentContext from agent state."""
    profile = state["profile"]
    is_domestic = state["student_type"] == "domestic"
    
    return StudentContext(
        is_domestic=is_domestic,
        citizenship_status=profile.get("citizenship_status", "INTERNATIONAL"),
        nationality=profile.get("nationality"),
        state_of_residence=profile.get("state_of_residence"),
        gpa=profile.get("gpa", 0.0),
        sat_score=profile.get("sat_score"),
        act_score=profile.get("act_score"),
        ap_count=profile.get("ap_class_count", 0),
        intended_major=profile.get("major", "Undeclared"),
        income_tier=profile.get("household_income_tier", "MEDIUM"),
        is_first_gen=profile.get("is_first_gen", False),
        campus_preference=profile.get("campus_vibe"),
        post_grad_goal=profile.get("post_grad_goal"),
        is_athlete=profile.get("is_student_athlete", False),
        has_legacy=profile.get("has_legacy_status", False),
        legacy_universities=profile.get("legacy_universities") or [],
    )


async def scorer_node(state: RecommendationAgentState) -> Dict[str, Any]:
    """
    Scorer node: Scores universities from research/cache.
    
    NO HARDCODED FALLBACK - If no universities found, returns error message.
    
    Args:
        state: Current agent state with matched_universities
        
    Returns:
        State updates with scored candidates or error message
    """
    try:
        # Build student context
        context = build_student_context(state)
        
        # Get universities from matched_universities (from researcher)
        universities: List[UniversityData] = []
        
        for matched in state.get("matched_universities", []):
            if isinstance(matched, dict) and matched.get("name"):
                universities.append(UniversityData(
                    name=matched.get("name", "Unknown"),
                    acceptance_rate=matched.get("acceptance_rate"),
                    median_gpa=matched.get("median_gpa"),
                    sat_25th=matched.get("sat_25th"),
                    sat_75th=matched.get("sat_75th"),
                    need_blind_international=matched.get("need_blind_international", False),
                    data_source=matched.get("data_source", "cache"),
                    student_major=context.intended_major,
                ))
        
        # Check if we have universities to score
        if not universities:
            logger.warning("Scorer: No universities found from research")
            error_msg = (
                "⚠️ **Search temporarily unavailable**\n\n"
                "Our system is currently experiencing high demand. "
                "Please try again in a few seconds.\n\n"
                "If this persists, try being more specific with your query."
            )
            return {
                "recommendations": [],
                "stream_content": [error_msg],
                "error": "No universities found - cache empty and API unavailable",
            }
        
        # Score universities with requested counts
        scorer = MatchScorer()
        counts = state.get("requested_counts", {"reach": 1, "target": 2, "safety": 2})
        recommendations = scorer.select_recommendations(context, universities, counts=counts)
        
        logger.info(f"Scorer produced {len(recommendations)} recommendations")
        
        # Convert to dict format for state
        scored_list = [r.to_dict() for r in recommendations]
        
        # Log found universities
        for rec in recommendations:
            logger.info(f"  - {rec.university.name} ({rec.label.value}) - {rec.match_score:.0f}% match")
        
        return {
            "recommendations": scored_list,
            "stream_content": [],  # Reserved for final recommendations only
        }
        
    except Exception as e:
        logger.error(f"Scorer node error: {e}")
        error_msg = (
            "⚠️ **An error occurred**\n\n"
            "We couldn't process your request. Please try again."
        )
        return {
            "error": f"Scoring failed: {str(e)}",
            "recommendations": [],
            "stream_content": [error_msg],
        }
