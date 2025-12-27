"""
Recommender Node for College List AI

Generates QUERY-AWARE responses based on intent:
- GENERATE_LIST: Create college recommendations
- CLARIFY_QUESTION: Answer the question directly
- UPDATE_PROFILE: Acknowledge the update
- FOLLOW_UP: Provide details about previous recommendations
"""

import logging
from typing import Dict, Any, List

import httpx
from google import genai
from google.genai import types

from app.config.settings import settings
from app.agents.state import (
    RecommendationAgentState, 
    QueryIntent,
    get_effective_major,
    get_effective_minor,
)

logger = logging.getLogger(__name__)


def format_recommendations_for_output(
    recommendations: List[Dict[str, Any]],
    state: RecommendationAgentState
) -> str:
    """Format scored recommendations for final output."""
    if not recommendations:
        return "Unable to generate recommendations with your current profile.\n"
    
    profile = state["profile"]
    is_domestic = state["student_type"] == "domestic"
    major = get_effective_major(state)
    minor = get_effective_minor(state)
    
    output_parts = []
    
    # Header with major/minor
    if minor:
        output_parts.append(f"# 🎓 Top University Recommendations for {major} (Minor: {minor})\n\n")
    else:
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
    Recommender node: Generates INTENT-AWARE responses.
    
    Handles different query intents:
    - GENERATE_LIST: Full college recommendations
    - CLARIFY_QUESTION: Direct answer without listing colleges
    - UPDATE_PROFILE: Acknowledge update, offer to regenerate
    - FOLLOW_UP: Detailed info about specific schools
    - GENERAL_CHAT: Conversational response
    """
    try:
        recommendations = state.get("recommendations", [])
        user_query = state.get("user_query", "")
        profile = state["profile"]
        is_domestic = state["student_type"] == "domestic"
        query_intent = state.get("query_intent", QueryIntent.GENERATE_LIST)
        derived_major = state.get("derived_major")
        derived_minor = state.get("derived_minor")
        conversation_history = state.get("conversation_history", [])
        
        # Get effective major/minor for context
        effective_major = get_effective_major(state)
        effective_minor = get_effective_minor(state)
        
        logger.info(f"Recommender: Handling intent {query_intent.value} for query: '{user_query[:50]}...'")
        
        # === HANDLE CLARIFY_QUESTION INTENT ===
        if query_intent == QueryIntent.CLARIFY_QUESTION:
            clarify_response = await _generate_clarify_response(
                user_query, profile, effective_major, effective_minor, conversation_history
            )
            return {
                "stream_content": [clarify_response],
                "recommendations": [],
            }
        
        # === HANDLE GENERAL_CHAT INTENT ===
        if query_intent == QueryIntent.GENERAL_CHAT:
            chat_response = await _generate_chat_response(user_query, profile)
            return {
                "stream_content": [chat_response],
                "recommendations": [],
            }
        
        # === HANDLE EMPTY RECOMMENDATIONS ===
        if not recommendations:
            logger.warning("Recommender received 0 recommendations from scorer.")
            fallback_message = (
                f"I couldn't find specific university recommendations for {effective_major}"
                + (f" with minor in {effective_minor}" if effective_minor else "")
                + ". This could be due to limited data in our cache. "
                "Please try again or adjust your profile settings.\n\n"
                "In the meantime, consider exploring:\n"
                f"- **Reach**: Top 20 universities for {effective_major}\n"
                "- **Target**: State flagship universities with strong programs\n"
                "- **Safety**: Universities with higher acceptance rates in your major"
            )
            return {
                "stream_content": [fallback_message],
                "recommendations": [],
            }
        
        # === HANDLE FOLLOW_UP INTENT ===
        if query_intent == QueryIntent.FOLLOW_UP:
            follow_up_response = await _generate_follow_up_response(
                user_query, recommendations, profile, is_domestic, conversation_history
            )
            return {
                "stream_content": [follow_up_response],
                "recommendations": recommendations,
            }
        
        # === HANDLE GENERATE_LIST INTENT (Default) ===
        # Build context from recommendations
        uni_summary = "\n".join([
            f"- {r.get('name')}: {r.get('label')} school, {r.get('match_score', 0):.0f}% match"
            for r in recommendations[:5]
        ])
        
        nationality = profile.get("nationality", "unknown")
        
        prompt = f"""You are a college advisor. Generate recommendations for: "{user_query}"

Student Profile:
- Major: {effective_major}
{f"- Minor: {effective_minor}" if effective_minor else ""}
- GPA: {profile.get('gpa', 3.5)}/4.0
- Type: {"Domestic" if is_domestic else f"International student from {nationality}"}

Based on analysis, here are the best matches:
{uni_summary}

Format the response as a clear college list with:
- 🎯 **Reach Schools** (competitive admissions)
- ✅ **Target Schools** (good chances)  
- 🛡️ **Safety Schools** (likely acceptance)

For each school, include match percentage and brief reasoning.
Use markdown formatting. Be conversational and encouraging."""

        # Route response generation based on synthesis_provider
        if settings.synthesis_provider == "groq":
            logger.info("[SYNTHESIS] Groq generating response...")
            final_output = await _generate_with_groq(prompt)
        elif settings.synthesis_provider == "perplexity":
            logger.info("[SYNTHESIS] Perplexity generating response...")
            final_output = await _generate_with_perplexity(prompt)
        else:  # ollama
            logger.info("[SYNTHESIS] Ollama generating response...")
            final_output = await _generate_with_ollama(prompt)
        
        if not final_output:
            final_output = format_recommendations_for_output(recommendations, state)
        
        logger.info(f"Recommender generated response for intent {query_intent.value}")
        
        return {
            "stream_content": [final_output],
            "recommendations": recommendations,
        }
        
    except Exception as e:
        logger.error(f"Recommender node error: {e}")
        
        recommendations = state.get("recommendations", [])
        fallback_output = format_recommendations_for_output(recommendations, state)
        
        return {
            "stream_content": [fallback_output],
            "recommendations": recommendations,
            "error": str(e),
        }


def _build_update_response(
    derived_major: str | None,
    derived_minor: str | None,
    effective_major: str,
    effective_minor: str | None
) -> str:
    """Build response acknowledging profile updates."""
    updates = []
    
    if derived_major:
        updates.append(f"**Major**: {derived_major}")
    if derived_minor:
        updates.append(f"**Minor**: {derived_minor}")
    
    if not updates:
        return "I didn't detect any profile updates. Could you please clarify what you'd like to change?"
    
    response = "Got it! I've noted the following updates:\n\n"
    response += "\n".join(f"- {u}" for u in updates)
    response += "\n\n"
    
    response += f"Your current profile now shows:\n"
    response += f"- **Major**: {effective_major}\n"
    if effective_minor:
        response += f"- **Minor**: {effective_minor}\n"
    
    response += "\nWould you like me to generate new college recommendations based on this updated profile?"
    
    return response


async def _generate_clarify_response(
    query: str,
    profile: Dict[str, Any],
    major: str,
    minor: str | None,
    history: List[Dict[str, str]]
) -> str:
    """Generate response for clarifying questions."""
    
    # Build context from history
    history_context = ""
    if history:
        history_context = "\n".join([
            f"{msg.get('role', 'unknown').title()}: {msg.get('content', '')[:100]}..."
            for msg in history[-3:]  # Last 3 messages
        ])
    
    prompt = f"""You are a helpful college advisor assistant. Answer this question directly:

Question: "{query}"

Student Context:
- Major: {major}
{f"- Minor: {minor}" if minor else ""}
- GPA: {profile.get('gpa', 'Not specified')}
- Citizenship: {profile.get('citizenship_status', 'Not specified')}
- Nationality: {profile.get('nationality', 'Not specified')}

{("Recent conversation:" + chr(10) + history_context) if history_context else ""}

IMPORTANT: Answer the question directly and concisely. Do NOT generate a college list unless explicitly asked.
Use markdown formatting."""

    if settings.llm_provider == "ollama":
        return await _generate_with_ollama(prompt)
    return await _generate_with_gemini(prompt)


async def _generate_chat_response(query: str, profile: Dict[str, Any]) -> str:
    """Generate conversational response for general chat."""
    prompt = f"""You are a friendly college advisor. Respond to: "{query}"

Be conversational, helpful, and brief. If the user seems to want college recommendations, 
ask them to tell you about their intended major and academic profile.

Use markdown formatting."""

    if settings.llm_provider == "ollama":
        return await _generate_with_ollama(prompt)
    return await _generate_with_gemini(prompt)


async def _generate_follow_up_response(
    query: str,
    recommendations: List[Dict[str, Any]],
    profile: Dict[str, Any],
    is_domestic: bool,
    history: List[Dict[str, str]]
) -> str:
    """Generate response for follow-up questions about recommendations."""
    
    # Build context from recommendations
    uni_summary = "\n".join([
        f"- {r.get('name')}: {r.get('label')} ({r.get('match_score', 0):.0f}% match)"
        for r in recommendations[:5]
    ])
    
    prompt = f"""You are a college advisor. The student asked a follow-up question: "{query}"

Previously recommended universities:
{uni_summary}

Student Profile:
- GPA: {profile.get('gpa', 3.5)}/4.0
- Type: {"Domestic US" if is_domestic else f"International from {profile.get('nationality', 'unknown')}"}
- Income Tier: {profile.get('household_income_tier', 'Not specified')}

Answer the specific question about these schools. If asking about:
- Scholarships/financial aid: Explain which schools offer better aid
- Chances/probability: Give realistic assessment
- Specific school: Provide detailed information

Be conversational and helpful. Use markdown formatting."""

    if settings.llm_provider == "ollama":
        return await _generate_with_ollama(prompt)
    return await _generate_with_gemini(prompt)


async def _generate_with_ollama(prompt: str) -> str:
    """Generate response using local Ollama API."""
    try:
        logger.info("Ollama is generating the response...")
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


async def _generate_with_groq(prompt: str) -> str:
    """
    Generate response using Groq API.
    
    Groq provides fast inference (~500 tokens/s) with LLaMA 3.3 70B.
    Uses OpenAI-compatible API format.
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.groq_model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
            )
            
            if response.status_code == 429:
                logger.warning("Groq rate limit hit, falling back to Ollama...")
                return await _generate_with_ollama(prompt)
            
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
    except httpx.HTTPError as e:
        logger.error(f"Groq API error: {e}, falling back to Ollama...")
        return await _generate_with_ollama(prompt)
    except (KeyError, IndexError) as e:
        logger.error(f"Groq response parsing error: {e}")
        return ""


async def _generate_with_perplexity(prompt: str) -> str:
    """
    Generate response using Perplexity Sonar API.
    
    For Production: Use same Perplexity API for search + synthesis.
    Simplifies architecture (one vendor, one API key).
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.perplexity_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.perplexity_model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
            )
            
            if response.status_code == 429:
                logger.warning("Perplexity rate limit hit, falling back to Ollama...")
                return await _generate_with_ollama(prompt)
            
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
    except httpx.HTTPError as e:
        logger.error(f"Perplexity API error: {e}, falling back to Ollama...")
        return await _generate_with_ollama(prompt)
    except (KeyError, IndexError) as e:
        logger.error(f"Perplexity response parsing error: {e}")
        return ""
