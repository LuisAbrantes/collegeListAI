"""
Researcher Node for College List AI

Implements HYBRID SEARCH strategy:
- Step A: Vector search for universities in our database
- Step B: Gemini grounding to discover hidden gems and verify data
"""

import logging
from typing import Dict, Any, List

from google import genai
from google.genai import types

from app.config.settings import settings
from app.agents.state import RecommendationAgentState

logger = logging.getLogger(__name__)


def build_search_queries(state: RecommendationAgentState) -> List[str]:
    """
    Build multiple focused search queries for comprehensive coverage.
    
    Returns queries for:
    1. Major-specific rankings (universal major support)
    2. Hidden gems / non-traditional schools
    3. Financial aid for student type
    """
    profile = state["profile"]
    major = profile.get("major", "general studies")
    gpa = profile.get("gpa", 3.5)
    is_domestic = state["student_type"] == "domestic"
    
    queries = []
    
    # Query 1: Major-specific rankings (universal major support)
    queries.append(
        f"top universities {major} program rankings 2025 "
        f"undergraduate best departments"
    )
    
    # Query 2: Hidden gems / non-traditional
    queries.append(
        f"underrated universities excellent {major} program "
        f"hidden gems lesser known colleges 2025"
    )
    
    if is_domestic:
        state_res = profile.get("state_of_residence", "")
        income_tier = profile.get("household_income_tier", "MEDIUM")
        
        # Query 3: State-specific options
        if state_res:
            queries.append(
                f"best public universities {major} {state_res} "
                f"in-state tuition 2025 acceptance rate"
            )
        
        # Query 4: Financial aid based on income
        if income_tier == "LOW":
            queries.append(
                "universities full financial aid low income students "
                "meet 100% need Pell Grant eligible 2025"
            )
        elif income_tier == "MEDIUM":
            queries.append(
                "best merit scholarships middle income students "
                "universities generous financial aid 2025"
            )
    else:
        nationality = profile.get("nationality", "international")
        income_tier = profile.get("household_income_tier", "MEDIUM")
        
        # Query 3: Need-blind for internationals
        if income_tier in ["LOW", "MEDIUM"]:
            queries.append(
                "need-blind universities international students 2025 "
                "full financial aid foreign students admission"
            )
        
        # Query 4: Country-specific scholarships
        queries.append(
            f"universities scholarships {nationality} students "
            f"{major} international financial aid 2025"
        )
    
    return queries


async def researcher_node(state: RecommendationAgentState) -> Dict[str, Any]:
    """
    Researcher node: Implements hybrid search strategy.
    
    Step A: Would query universities_master for verified data (DB)
    Step B: Uses Gemini Search for hidden gems and verification
    
    Args:
        state: Current agent state
        
    Returns:
        State updates with research results and sources
    """
    try:
        client = genai.Client(api_key=settings.google_api_key)
        
        is_domestic = state["student_type"] == "domestic"
        profile = state["profile"]
        major = profile.get("major", "Computer Science")
        
        # Build comprehensive search prompt
        search_queries = build_search_queries(state)
        
        # Create hybrid research prompt
        research_prompt = f"""You are a college admissions research expert. Research universities for a student with this profile:

## Student Profile
- **Major:** {major}
- **GPA:** {profile.get('gpa', 3.5)}/4.0
- **Student Type:** {"Domestic US" if is_domestic else "International"} student
{f"- **Home State:** {profile.get('state_of_residence')}" if is_domestic and profile.get('state_of_residence') else ""}
{f"- **Nationality:** {profile.get('nationality')}" if not is_domestic else ""}
- **Financial Need:** {profile.get('household_income_tier', 'MEDIUM')}

## Research Tasks

1. **Major-Specific Rankings**: Find current {major} program rankings for 2025-2026.

2. **Hidden Gems**: Identify 3-5 excellent but lesser-known universities with strong {major} programs that are NOT the typical famous schools. Focus on:
   - Regional universities with exceptional departments
   - Schools with high job placement rates
   - Universities with strong research opportunities

3. **Financial Aid**: 
{'''   - In-state public universities in their state
   - FAFSA and state grant eligibility''' if is_domestic else '''   - Need-blind admission policies for international students
   - Scholarships available for students from their country'''}

4. **Acceptance Rates & Stats**: For each university, provide:
   - Approximate acceptance rate
   - Typical GPA range (25th-75th percentile)
   - SAT/ACT ranges if available

## Important
- Include BOTH famous and non-traditional universities
- The goal is finding the BEST FIT, not just the most famous
- Prioritize schools where this student has real admission chances
- Use current 2025-2026 data

Search Queries Used: {', '.join(search_queries[:2])}

Return structured information with sources."""

        # Call Gemini with Google Search grounding
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=research_prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=3000,
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        
        # Extract grounding sources
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
                            "uri": chunk.web.uri or ""
                        })
        
        research_result = {
            "query": " | ".join(search_queries[:2]),
            "sources": sources,
            "content": response.text or ""
        }
        
        logger.info(
            f"Researcher: {len(sources)} sources, "
            f"{len(search_queries_used)} queries for {state['student_type']} student"
        )
        
        stream_msg = (
            f"🔍 Researching {major} programs for you...\n"
            f"📚 Checking major rankings, hidden gems, and financial aid options\n\n"
        )
        
        return {
            "research_results": [research_result],
            "search_queries": search_queries_used,
            "grounding_sources": sources,
            "stream_content": [stream_msg]
        }
        
    except Exception as e:
        logger.error(f"Researcher node error: {e}")
        return {
            "error": f"Research failed: {str(e)}",
            "research_results": [],
            "search_queries": [],
            "grounding_sources": [],
            "stream_content": ["⚠️ Research encountered an issue...\n\n"]
        }

