"""
Analyzer Node for College List AI

Analyzes research results and matches universities to student profile.
Applies different logic for domestic vs international students.
"""

import logging
from typing import Dict, Any, List

from app.agents.state import RecommendationAgentState

logger = logging.getLogger(__name__)


def build_financial_aid_context(state: RecommendationAgentState) -> str:
    """Build financial aid context based on student type and profile."""
    profile = state["profile"]
    is_domestic = state["student_type"] == "domestic"
    
    if is_domestic:
        income_tier = profile.get("household_income_tier", "MEDIUM")
        state_res = profile.get("state_of_residence", "")
        is_first_gen = profile.get("is_first_gen", False)
        
        context_parts = [
            "## Domestic Student Financial Aid Context",
            "",
            f"**Income Tier:** {income_tier}",
        ]
        
        if income_tier == "LOW":
            context_parts.extend([
                "- Likely eligible for **Pell Grant** (up to $7,395 for 2024-25)",
                "- Should qualify for **Federal Work-Study**",
                "- Many institutions offer full need-met financial aid",
                "- Look for **no-loan policies** at top institutions",
            ])
        elif income_tier == "MEDIUM":
            context_parts.extend([
                "- May qualify for partial **Pell Grant**",
                "- Focus on **merit scholarships** + need-based aid combination",
                "- Consider public in-state options for cost savings",
            ])
        else:  # HIGH
            context_parts.extend([
                "- Focus on **merit-based scholarships**",
                "- Consider **honors programs** with scholarship packages",
                "- Some schools have automatic merit for high GPA/test scores",
            ])
        
        if state_res:
            context_parts.append(f"- In-state tuition available in **{state_res}**")
        
        if is_first_gen:
            context_parts.extend([
                "",
                "**First-Generation Advantage:**",
                "- Many schools offer special first-gen scholarships",
                "- QuestBridge and similar programs available",
            ])
            
    else:  # International
        nationality = profile.get("nationality", "Unknown")
        income_tier = profile.get("household_income_tier", "MEDIUM")
        
        context_parts = [
            "## International Student Financial Aid Context",
            "",
            f"**Nationality:** {nationality}",
            f"**Financial Need:** {income_tier}",
            "",
            "### Need-Blind vs Need-Aware Policies",
            "",
        ]
        
        # Add info about need-blind schools for internationals
        if income_tier in ["LOW", "MEDIUM"]:
            context_parts.extend([
                "**Truly Need-Blind for Internationals:**",
                "- Harvard, Yale, Princeton, MIT, Amherst (5 schools only)",
                "- These evaluate admission without considering ability to pay",
                "",
                "**Need-Aware but Generous:**",
                "- Stanford, Columbia, Duke, UChicago, Northwestern",
                "- Consider finances but still provide substantial aid",
                "",
                f"**For students from {nationality}:**",
                "- Check if specific country has bilateral scholarships",
                "- Fulbright and similar country programs may apply",
            ])
        else:
            context_parts.extend([
                "**Merit Scholarship Focus:**",
                "- With lower financial need, focus on merit-based awards",
                "- International student merit scholarships available at many schools",
                "- Consider schools with strong international student support",
            ])
    
    return "\n".join(context_parts)


def calculate_match_factors(state: RecommendationAgentState) -> Dict[str, Any]:
    """Calculate match factors for university ranking."""
    profile = state["profile"]
    
    factors = {
        "gpa": profile.get("gpa", 3.0),
        "has_test_scores": bool(profile.get("sat_score") or profile.get("act_score")),
        "sat_score": profile.get("sat_score"),
        "act_score": profile.get("act_score"),
        "is_athlete": profile.get("is_student_athlete", False),
        "has_legacy": profile.get("has_legacy_status", False),
        "legacy_schools": profile.get("legacy_universities", []),
        "post_grad_goal": profile.get("post_grad_goal", "UNDECIDED"),
        "campus_preference": profile.get("campus_vibe"),
        "ap_count": profile.get("ap_class_count", 0),
    }
    
    return factors


async def analyzer_node(state: RecommendationAgentState) -> Dict[str, Any]:
    """
    Analyzer node: Matches research results to student profile.
    
    This node:
    1. Builds financial aid context based on student type
    2. Calculates match factors from profile
    3. Prepares data for the recommender node
    
    Args:
        state: Current agent state
        
    Returns:
        State updates with financial context and match factors
    """
    try:
        # Build financial aid context
        financial_context = build_financial_aid_context(state)
        
        # Calculate match factors
        match_factors = calculate_match_factors(state)
        
        # Extract university mentions from research
        research_content = ""
        for result in state.get("research_results", []):
            research_content += result.get("content", "") + "\n\n"
        
        # Prepare matched universities context
        matched_universities = []
        
        # Parse research for university mentions (simplified)
        # In production, this would use NER or structured extraction
        logger.info(f"Analyzer processed {len(state.get('research_results', []))} research results")
        
        # Log progress (not streamed to user)
        if state["student_type"] == "domestic":
            logger.info(f"Analyzing options for domestic student in {state['profile'].get('state_of_residence', 'US')}")
        else:
            logger.info(f"Analyzing options for international student from {state['profile'].get('nationality', 'abroad')}")
        
        return {
            "financial_aid_context": financial_context,
            "stream_content": []  # Reserved for final recommendations only
        }
        
    except Exception as e:
        logger.error(f"Analyzer node error: {e}")
        return {
            "error": f"Analysis failed: {str(e)}",
            "financial_aid_context": "",
            "stream_content": []  # Don't stream error status
        }
