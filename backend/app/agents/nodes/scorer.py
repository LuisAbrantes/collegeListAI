"""
Scorer Node for College List AI

Scores and classifies universities using the domain scoring engine.
Implements Step C of the hybrid search flow.
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


def parse_universities_from_research(
    research_results: List[Dict[str, Any]],
    student_context: StudentContext
) -> List[UniversityData]:
    """
    Parse university data from research results.
    
    Extracts structured data from Gemini search grounding results.
    Includes student's intended major for context.
    """
    universities: List[UniversityData] = []
    seen_names: set = set()
    
    # Get the student's intended major for context
    student_major = student_context.intended_major
    
    for result in research_results:
        content = result.get("content", "")
        sources = result.get("sources", [])
        
        # Extract university mentions from sources
        for source in sources:
            url = source.get("uri", "")
            title = source.get("title", "")
            
            # Try to identify university from source
            uni_name = _extract_university_name(title, url)
            
            if uni_name and uni_name not in seen_names:
                seen_names.add(uni_name)
                
                # Create university data with student's major context
                universities.append(UniversityData(
                    name=uni_name,
                    data_source="Gemini_Grounding",
                    official_url=url,
                    has_major=True,  # Assume yes from search context
                    student_major=student_major,  # Track which major we're evaluating
                ))
    
    return universities


def _extract_university_name(title: str, url: str) -> str | None:
    """Extract university name from source title or URL."""
    title_lower = title.lower()
    
    # Common patterns
    patterns = [
        "university", "college", "institute", "school",
    ]
    
    for pattern in patterns:
        if pattern in title_lower:
            # Return cleaned title as university name
            # Remove common suffixes
            name = title.split(" - ")[0].split(" | ")[0].strip()
            if len(name) > 5:  # Reasonable length
                return name
    
    return None


async def scorer_node(state: RecommendationAgentState) -> Dict[str, Any]:
    """
    Scorer node: Scores and classifies universities.
    
    This node:
    1. Builds StudentContext from profile
    2. Parses universities from research results
    3. Scores each university using MatchScorer
    4. Selects top 5: 2 Safety, 2 Target, 1 Reach
    
    Args:
        state: Current agent state
        
    Returns:
        State updates with scored candidates
    """
    try:
        # Build student context
        context = build_student_context(state)
        
        # Parse universities from research
        universities = parse_universities_from_research(
            state.get("research_results", []),
            context
        )
        
        # Enrich with matched_universities from analyzer (if any)
        for matched in state.get("matched_universities", []):
            if isinstance(matched, dict):
                universities.append(UniversityData(
                    name=matched.get("name", "Unknown"),
                    acceptance_rate=matched.get("acceptance_rate"),
                    median_gpa=matched.get("median_gpa"),
                    sat_25th=matched.get("sat_25th"),
                    sat_75th=matched.get("sat_75th"),
                    need_blind_international=matched.get("need_blind_international", False),
                    data_source=matched.get("data_source", "database"),
                    student_major=context.intended_major,  # Use context's intended major
                ))
        
        # Score universities
        scorer = MatchScorer()
        recommendations = scorer.select_recommendations(context, universities)
        
        logger.info(f"Scorer produced {len(recommendations)} recommendations")
        
        # Convert to dict format for state
        scored_list = [r.to_dict() for r in recommendations]
        
        # Build stream message
        stream_msg = f"🎯 Found {len(recommendations)} universities matching your profile:\n\n"
        for rec in recommendations:
            stream_msg += f"• **{rec.university.name}** ({rec.label.value}) - {rec.match_score:.0f}% match\n"
        stream_msg += "\n"
        
        return {
            "recommendations": scored_list,
            "stream_content": [stream_msg],
        }
        
    except Exception as e:
        logger.error(f"Scorer node error: {e}")
        return {
            "error": f"Scoring failed: {str(e)}",
            "recommendations": [],
            "stream_content": ["⚠️ Unable to score universities.\n\n"],
        }
