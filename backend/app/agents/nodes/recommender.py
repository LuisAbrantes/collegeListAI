"""
Recommender Node for College List AI

Generates final college recommendations using scored candidates.
Produces formatted output with match transparency breakdown.
"""

import logging
from typing import Dict, Any, List

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
    Recommender node: Generates final college recommendations.
    
    Uses pre-scored candidates from scorer node to generate
    detailed recommendations with match transparency.
    
    Args:
        state: Current agent state (includes scored recommendations)
        
    Returns:
        State updates with formatted recommendations
    """
    try:
        recommendations = state.get("recommendations", [])
        
        # If we have scored recommendations, enhance with AI reasoning
        if recommendations:
            client = genai.Client(api_key=settings.google_api_key)
            
            # Build enhancement prompt
            profile = state["profile"]
            is_domestic = state["student_type"] == "domestic"
            
            uni_names = [r.get("name", "") for r in recommendations[:5]]
            
            enhance_prompt = f"""Provide brief (1-2 sentence) personalized reasoning for why each of these universities fits this student:

Student Profile:
- Major: {profile.get('major', 'Undeclared')}
- GPA: {profile.get('gpa', 3.5)}/4.0
- Type: {"Domestic" if is_domestic else "International"} student
{f"- State: {profile.get('state_of_residence')}" if is_domestic else f"- Nationality: {profile.get('nationality')}"}
- Financial Need: {profile.get('household_income_tier', 'MEDIUM')}

Universities to explain:
{chr(10).join(f"- {name}" for name in uni_names)}

For each university, provide:
1. A brief reasoning why it's a good fit (considering academics, culture, opportunities)
2. A one-line financial aid summary for this student type

Format as:
UNIVERSITY_NAME
Reasoning: [your reasoning]
Financial: [financial summary]

Keep it concise and actionable."""

            # Get AI enhancement
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=enhance_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.5,
                    max_output_tokens=1500,
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            
            # Parse and attach reasoning to recommendations
            if response.text:
                enhanced_content = response.text
                for rec in recommendations:
                    name = rec.get("name", "")
                    # Simple extraction - find content after university name
                    if name in enhanced_content:
                        # Extract reasoning
                        rec["reasoning"] = _extract_reasoning(enhanced_content, name)
                        rec["financial_aid_summary"] = _extract_financial(
                            enhanced_content, name, is_domestic
                        )
        
        # Format final output
        final_output = format_recommendations_for_output(recommendations, state)
        
        logger.info(f"Recommender formatted {len(recommendations)} recommendations")
        
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

