"""
Recommender Node for College List AI

Generates final college recommendations using scored candidates.
Produces formatted output with match transparency breakdown.
"""

import logging
from typing import Dict, Any, List

import httpx
from google import genai
from google.genai import types

from app.config.settings import settings
from app.agents.state import RecommendationAgentState

logger = logging.getLogger(__name__)


def format_recommendations_for_output(
    recommendations: List[Dict[str, Any]],
    state: RecommendationAgentState
) -> str:
    """
    Format scored recommendations for final output.
    
    Includes match transparency breakdown.
    """
    if not recommendations:
        return "Unable to generate recommendations with your current profile.\n"
    
    profile = state["profile"]
    is_domestic = state["student_type"] == "domestic"
    
    output_parts = []
    
    # Header
    major = profile.get("major", "your chosen field")
    output_parts.append(f"# 🎓 Top University Recommendations for {major}\n\n")
    
    # Group by label
    reaches = [r for r in recommendations if r.get("label") == "Reach"]
    targets = [r for r in recommendations if r.get("label") == "Target"]
    safeties = [r for r in recommendations if r.get("label") == "Safety"]
    
    # Format each group
    if reaches:
        output_parts.append("## 🎯 Reach Schools\n\n")
        for rec in reaches:
            output_parts.append(_format_single_recommendation(rec, is_domestic))
    
    if targets:
        output_parts.append("## ✅ Target Schools\n\n")
        for rec in targets:
            output_parts.append(_format_single_recommendation(rec, is_domestic))
    
    if safeties:
        output_parts.append("## 🛡️ Safety Schools\n\n")
        for rec in safeties:
            output_parts.append(_format_single_recommendation(rec, is_domestic))
    
    # Add summary
    output_parts.append("\n---\n\n")
    output_parts.append("### 📊 Match Score Legend\n")
    output_parts.append("- **90%+**: Exceptional fit for your profile\n")
    output_parts.append("- **80-89%**: Strong match across most factors\n")
    output_parts.append("- **70-79%**: Good fit with some considerations\n")
    output_parts.append("- **60-69%**: Viable option worth exploring\n\n")
    
    return "".join(output_parts)


def _format_single_recommendation(rec: Dict[str, Any], is_domestic: bool) -> str:
    """Format a single recommendation with match transparency."""
    name = rec.get("name", "Unknown University")
    match_score = rec.get("match_score", 0)
    admission_prob = rec.get("admission_probability", 50)
    transparency = rec.get("match_transparency", {})
    reasoning = rec.get("reasoning", "")
    financial_summary = rec.get("financial_aid_summary", "")
    
    output = f"### {name}\n\n"
    output += f"**Overall Match: {match_score:.0f}%** | "
    output += f"Admission Probability: ~{admission_prob:.0f}%\n\n"
    
    # Match transparency breakdown
    if transparency:
        output += "**Match Breakdown:**\n"
        
        if transparency.get("academic_fit"):
            output += f"- 📚 Academic Fit: {transparency['academic_fit']:.0f}%\n"
        if transparency.get("major_strength"):
            output += f"- 🎓 Major Strength: {transparency['major_strength']:.0f}%\n"
        if transparency.get("financial_fit"):
            output += f"- 💰 Financial Fit: {transparency['financial_fit']:.0f}%\n"
        if transparency.get("location_fit"):
            output += f"- 📍 Location Fit: {transparency['location_fit']:.0f}%\n"
        if transparency.get("special_factors") and transparency.get("special_factors") > 0:
            output += f"- ⭐ Special Factors: {transparency['special_factors']:.0f}%\n"
        
        output += "\n"
    
    if reasoning:
        output += f"**Why this school:** {reasoning}\n\n"
    
    if financial_summary:
        emoji = "🏠" if is_domestic else "🌍"
        output += f"**{emoji} Financial Aid:** {financial_summary}\n\n"
    
    return output


async def recommender_node(state: RecommendationAgentState) -> Dict[str, Any]:
    """
    Recommender node: Generates QUERY-AWARE college recommendations.
    
    IMPORTANT: This node generates responses based on the ACTUAL user query,
    not just a template. If the user asks about scholarships, it responds
    about scholarships. If about specific schools, it responds about those.
    
    Supports both Gemini and Ollama providers based on settings.llm_provider.
    
    Args:
        state: Current agent state (includes scored recommendations)
        
    Returns:
        State updates with formatted recommendations
    """
    try:
        recommendations = state.get("recommendations", [])
        user_query = state.get("user_query", "").lower()
        profile = state["profile"]
        is_domestic = state["student_type"] == "domestic"
        is_follow_up = state.get("is_follow_up", False)
        
        # Handle empty recommendations gracefully
        if not recommendations:
            logger.warning("Recommender received 0 recommendations from scorer. Returning fallback response.")
            fallback_message = (
                "I couldn't find specific university recommendations based on your profile. "
                "This could be due to limited data in our cache. "
                "Please try again or adjust your profile settings.\n\n"
                "In the meantime, consider exploring:\n"
                "- **Reach**: Top 20 universities in your field\n"
                "- **Target**: State flagship universities\n"
                "- **Safety**: Universities with higher acceptance rates in your major"
            )
            return {
                "stream_content": [fallback_message],
                "recommendations": [],
            }
        
        # Build context from recommendations
        uni_summary = "\n".join([
            f"- {r.get('name')}: {r.get('label')} school, {r.get('match_score', 0):.0f}% match, Financial: {r.get('match_transparency', {}).get('financial_fit', 0):.0f}%"
            for r in recommendations[:5]
        ])
        
        # Determine intent from query
        is_scholarship_query = any(kw in user_query for kw in 
            ["scholarship", "financial", "aid", "cost", "afford", "money", "fee", "tuition"])
        is_specific_school_query = any(kw in user_query for kw in 
            ["mit", "stanford", "harvard", "berkeley", "cmu", "carnegie", "georgia tech"])
        is_chance_query = any(kw in user_query for kw in 
            ["chance", "odds", "likely", "probability", "can i get", "will i"])
        
        # Build appropriate prompt based on intent
        if is_follow_up or is_scholarship_query:
            prompt = f"""You are a college advisor. The student asked: "{state.get('user_query', '')}"

Student Profile:
- Major: {profile.get('major', 'Undeclared')}
- GPA: {profile.get('gpa', 3.5)}/4.0
- Type: {"Domestic" if is_domestic else f"International from {profile.get('nationality', 'unknown')}"}
- Income Tier: {profile.get('household_income_tier', 'MEDIUM')}

Previously recommended schools:
{uni_summary}

ANSWER THE SPECIFIC QUESTION. If about scholarships, explain:
1. Which of these schools offer best financial aid for this student
2. Specific scholarship opportunities (need-blind, merit scholarships)
3. Estimated cost after aid

Be conversational, specific, and helpful. Use markdown formatting.
DO NOT just repeat the list of schools. Answer the question directly."""

        elif is_chance_query:
            prompt = f"""You are a college advisor. The student asked: "{state.get('user_query', '')}"

Student Profile:
- GPA: {profile.get('gpa', 3.5)}/4.0
- SAT: {profile.get('sat_score', 'Not provided')}
- Major: {profile.get('major', 'Undeclared')}

Previously recommended schools with admission probability:
{uni_summary}

Provide a realistic chance assessment. Be encouraging but honest.
Explain what affects their chances at each tier (Reach/Target/Safety)."""

        else:
            # Default: Generate college list with context
            prompt = f"""You are a college advisor. Generate recommendations for: "{state.get('user_query', '')}"

Student Profile:
- Major: {profile.get('major', 'Undeclared')}
- GPA: {profile.get('gpa', 3.5)}/4.0
- Type: {"Domestic" if is_domestic else f"International from {profile.get('nationality', 'unknown')}"}

Based on analysis, here are the best matches:
{uni_summary}

Format the response as a clear college list with:
- 🎯 **Reach Schools** (1 school)
- ✅ **Target Schools** (2 schools)
- 🛡️ **Safety Schools** (2 schools)

For each school, include match percentage and brief reasoning.
Use markdown formatting. Be conversational."""

        # Route to appropriate LLM provider
        if settings.llm_provider == "ollama":
            final_output = await _generate_with_ollama(prompt)
        else:
            final_output = await _generate_with_gemini(prompt)
        
        if not final_output:
            final_output = format_recommendations_for_output(recommendations, state)
        
        logger.info(f"Recommender generated query-aware response for: '{user_query[:50]}...'")
        
        return {
            "stream_content": [final_output],
            "recommendations": recommendations,
        }
        
    except Exception as e:
        logger.error(f"Recommender node error: {e}")
        
        # Fallback: format whatever recommendations we have
        recommendations = state.get("recommendations", [])
        fallback_output = format_recommendations_for_output(recommendations, state)
        
        return {
            "stream_content": [fallback_output],
            "recommendations": recommendations,
            "error": str(e),
        }


async def _generate_with_ollama(prompt: str) -> str:
    """Generate response using local Ollama API."""
    try:
        logger.info("Ollama is generating the structured response...")
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
    except httpx.HTTPError as e:
        logger.error(f"Ollama API error in recommender: {e}")
        raise RuntimeError(f"Ollama generation failed: {e}")


async def _generate_with_gemini(prompt: str) -> str:
    """Generate response using Gemini API with search grounding."""
    client = genai.Client(api_key=settings.google_api_key)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=2000,
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )
    return response.text if response.text else ""


def _extract_reasoning(content: str, uni_name: str) -> str:
    """Extract reasoning for a university from AI response."""
    try:
        # Find section for this university
        start = content.find(uni_name)
        if start == -1:
            return ""
        
        section = content[start:start + 500]
        
        # Find "Reasoning:" line
        if "Reasoning:" in section:
            reason_start = section.find("Reasoning:") + len("Reasoning:")
            reason_end = section.find("\n", reason_start)
            if reason_end > reason_start:
                return section[reason_start:reason_end].strip()
        
        return ""
    except:
        return ""


def _extract_financial(content: str, uni_name: str, is_domestic: bool) -> str:
    """Extract financial summary for a university."""
    try:
        start = content.find(uni_name)
        if start == -1:
            return ""
        
        section = content[start:start + 500]
        
        if "Financial:" in section:
            fin_start = section.find("Financial:") + len("Financial:")
            fin_end = section.find("\n", fin_start)
            if fin_end > fin_start:
                return section[fin_start:fin_end].strip()
        
        # Default based on student type
        if is_domestic:
            return "Check FAFSA eligibility and institutional aid."
        else:
            return "Review international student scholarship options."
    except:
        return ""

