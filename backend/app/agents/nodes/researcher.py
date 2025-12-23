"""
Researcher Node for College List AI

Performs Google Search grounding to find real-time university data.
Uses Gemini's search capability to fetch current information.
"""

import logging
from typing import Dict, Any

from google import genai
from google.genai import types

from app.config.settings import settings
from app.agents.state import RecommendationAgentState, is_domestic_student

logger = logging.getLogger(__name__)


def build_research_query(state: RecommendationAgentState) -> str:
    """Build a focused research query based on student profile and type."""
    profile = state["profile"]
    user_query = state["user_query"]
    is_domestic = state["student_type"] == "domestic"
    
    # Base query components
    major = profile.get("major", "computer science")
    gpa = profile.get("gpa", 3.5)
    
    if is_domestic:
        # Domestic student query focuses on in-state options and FAFSA
        state_res = profile.get("state_of_residence", "")
        income_tier = profile.get("household_income_tier", "")
        
        query_parts = [
            f"Best {major} universities for students with {gpa} GPA",
            f"in-state tuition options" if state_res else "",
            f"{income_tier.lower()} income financial aid" if income_tier else "",
            "FAFSA eligible universities 2025",
            user_query,
        ]
    else:
        # International student query focuses on need-blind and visa support
        nationality = profile.get("nationality", "international")
        english_score = profile.get("english_proficiency_score")
        
        query_parts = [
            f"Best {major} universities for international students from {nationality}",
            f"with {gpa} GPA",
            f"need-blind admission for international students 2025",
            f"universities accepting TOEFL {english_score}" if english_score else "",
            "international student scholarships and financial aid",
            user_query,
        ]
    
    return " ".join([p for p in query_parts if p])


async def researcher_node(state: RecommendationAgentState) -> Dict[str, Any]:
    """
    Researcher node: Performs Google Search grounding for university data.
    
    This node:
    1. Builds a search query based on student profile
    2. Uses Gemini's Google Search tool to find current data
    3. Extracts grounding sources and content
    
    Args:
        state: Current agent state
        
    Returns:
        State updates with research results and sources
    """
    try:
        client = genai.Client(api_key=settings.google_api_key)
        
        # Build search query
        search_query = build_research_query(state)
        is_domestic = state["student_type"] == "domestic"
        
        # Create focused research prompt
        if is_domestic:
            research_prompt = f"""Research current information about universities for this domestic US student:

Query: {search_query}

Focus on:
1. In-state tuition opportunities in {state['profile'].get('state_of_residence', 'their state')}
2. FAFSA and federal financial aid eligibility
3. State grant programs
4. Merit scholarships for their GPA range
5. Current acceptance rates and requirements

Use Google Search to find the most current 2025-2026 admissions data.
Provide factual information with source references."""
        else:
            research_prompt = f"""Research current information about universities for this international student:

Query: {search_query}

Focus on:
1. Need-blind admission policies for students from {state['profile'].get('nationality', 'their country')}
2. Need-aware vs need-blind institutional policies
3. International student scholarships and financial aid
4. English proficiency requirements (TOEFL/IELTS/Duolingo)
5. Current acceptance rates for international applicants

Use Google Search to find the most current 2025-2026 admissions data.
Provide factual information with source references."""

        # Call Gemini with Google Search grounding
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=research_prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,  # Lower for factual research
                max_output_tokens=2048,
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        
        # Extract grounding metadata
        sources = []
        search_queries_used = []
        
        if response.candidates and response.candidates[0].grounding_metadata:
            metadata = response.candidates[0].grounding_metadata
            search_queries_used = list(metadata.web_search_queries or [])
            
            if metadata.grounding_chunks:
                for chunk in metadata.grounding_chunks:
                    if hasattr(chunk, 'web') and chunk.web:
                        sources.append({
                            "title": chunk.web.title or "Unknown",
                            "url": chunk.web.uri or ""
                        })
        
        research_result = {
            "query": search_query,
            "sources": sources,
            "content": response.text or ""
        }
        
        logger.info(f"Researcher found {len(sources)} sources for {state['student_type']} student")
        
        return {
            "research_results": [research_result],
            "search_queries": search_queries_used,
            "grounding_sources": sources,
            "stream_content": [f"🔍 Researching universities...\n\n"]
        }
        
    except Exception as e:
        logger.error(f"Researcher node error: {e}")
        return {
            "error": f"Research failed: {str(e)}",
            "research_results": [],
            "search_queries": [],
            "grounding_sources": [],
            "stream_content": [f"⚠️ Research encountered an issue, proceeding with cached data...\n\n"]
        }
