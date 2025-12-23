"""
Recommender Node for College List AI

Generates final college recommendations using Gemini with all context.
Produces formatted recommendations with Reach/Target/Safety labels.
"""

import logging
from typing import Dict, Any, List, Generator

from google import genai
from google.genai import types

from app.config.settings import settings
from app.agents.state import RecommendationAgentState, CollegeRecommendation

logger = logging.getLogger(__name__)


def build_recommendation_prompt(state: RecommendationAgentState) -> str:
    """Build the final recommendation prompt with all context."""
    profile = state["profile"]
    is_domestic = state["student_type"] == "domestic"
    
    # Profile summary
    profile_section = f"""## Student Profile

**Student Type:** {"Domestic (US-based)" if is_domestic else "International"}
**GPA:** {profile.get('gpa', 'N/A')}/4.0
**Intended Major:** {profile.get('major', 'Undeclared')}
"""
    
    # Test scores
    if profile.get('sat_score'):
        profile_section += f"**SAT:** {profile['sat_score']}/1600\n"
    if profile.get('act_score'):
        profile_section += f"**ACT:** {profile['act_score']}/36\n"
    
    # Type-specific info
    if is_domestic:
        if profile.get('state_of_residence'):
            profile_section += f"**Home State:** {profile['state_of_residence']}\n"
        if profile.get('household_income_tier'):
            profile_section += f"**Income Tier:** {profile['household_income_tier']}\n"
        if profile.get('is_first_gen'):
            profile_section += "**First-Generation:** Yes\n"
    else:
        if profile.get('nationality'):
            profile_section += f"**Nationality:** {profile['nationality']}\n"
        if profile.get('english_proficiency_score'):
            test_type = profile.get('english_test_type', 'TOEFL')
            profile_section += f"**{test_type}:** {profile['english_proficiency_score']}\n"
    
    # Additional factors
    if profile.get('is_student_athlete'):
        profile_section += "**Student Athlete:** Yes\n"
    if profile.get('has_legacy_status') and profile.get('legacy_universities'):
        profile_section += f"**Legacy:** {', '.join(profile['legacy_universities'])}\n"
    if profile.get('campus_vibe'):
        profile_section += f"**Campus Preference:** {profile['campus_vibe']}\n"
    if profile.get('post_grad_goal'):
        profile_section += f"**Post-Grad Goal:** {profile['post_grad_goal']}\n"
    
    # Research context
    research_section = "## Research Findings\n\n"
    for result in state.get("research_results", []):
        research_section += result.get("content", "") + "\n\n"
    
    # Financial aid context
    financial_section = state.get("financial_aid_context", "")
    
    # Exclusions
    excluded = state.get("excluded_colleges", [])
    exclusion_section = ""
    if excluded:
        exclusion_section = f"\n**DO NOT RECOMMEND:** {', '.join(excluded)}\n"
    
    # Final prompt
    prompt = f"""{profile_section}

{financial_section}

{research_section}

{exclusion_section}

## User Query
{state['user_query']}

## Instructions

Based on all the context above, recommend **exactly 5 universities** that are the best fit for this student.

For each university, provide:
1. **University Name** (official name)
2. **Label:** Reach, Target, or Safety
   - Reach: Acceptance unlikely but possible (<25% admission rate or GPA above student's)
   - Target: Good chance of admission, strong fit
   - Safety: High likelihood of admission with student's stats
3. **Match Score:** 0-100 based on fit with profile
4. **Brief Reasoning:** 2-3 sentences on why this fits
5. **Financial Aid Summary:** Specific to student's situation

{"Focus on in-state options and FAFSA eligibility." if is_domestic else "Consider need-blind status and international student support."}

Format each recommendation clearly, separating universities with blank lines."""

    return prompt


async def recommender_node(state: RecommendationAgentState) -> Dict[str, Any]:
    """
    Recommender node: Generates final college recommendations.
    
    This node:
    1. Builds comprehensive prompt with all context
    2. Calls Gemini for final recommendations
    3. Formats output for streaming
    
    Args:
        state: Current agent state
        
    Returns:
        State updates with recommendations
    """
    try:
        client = genai.Client(api_key=settings.google_api_key)
        
        # Build recommendation prompt
        prompt = build_recommendation_prompt(state)
        
        # Generate recommendations with Gemini
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.6,
                max_output_tokens=2048,
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        
        recommendation_text = response.text or ""
        
        logger.info(f"Recommender generated {len(recommendation_text)} chars of recommendations")
        
        return {
            "stream_content": [recommendation_text],
            "recommendations": []  # Would parse structured recommendations here
        }
        
    except Exception as e:
        logger.error(f"Recommender node error: {e}")
        return {
            "error": f"Recommendation generation failed: {str(e)}",
            "stream_content": [f"⚠️ Unable to generate recommendations: {str(e)}"],
            "recommendations": []
        }


def recommender_node_streaming(state: RecommendationAgentState) -> Generator[str, None, Dict[str, Any]]:
    """
    Streaming version of recommender node.
    
    Yields chunks of text as they're generated by Gemini.
    Returns final state updates when complete.
    """
    try:
        client = genai.Client(api_key=settings.google_api_key)
        
        # Build recommendation prompt
        prompt = build_recommendation_prompt(state)
        
        # Stream recommendations
        response = client.models.generate_content_stream(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.6,
                max_output_tokens=2048,
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        
        full_content = []
        for chunk in response:
            if chunk.text:
                full_content.append(chunk.text)
                yield chunk.text
        
        # Return final state update
        return {
            "stream_content": full_content,
            "recommendations": []
        }
        
    except Exception as e:
        logger.error(f"Recommender streaming error: {e}")
        yield f"⚠️ Error: {str(e)}"
        return {
            "error": str(e),
            "stream_content": [],
            "recommendations": []
        }
