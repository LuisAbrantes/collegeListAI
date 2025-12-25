"""
Researcher Node for College List AI

Implements HYBRID SEARCH strategy via CollegeSearchService:
- Phase 1: Local cache query (fast)
- Phase 2: Gemini grounding (if cache insufficient)
- Phase 3: Auto-populate cache (Data Flywheel)
"""

import logging
from typing import Dict, Any, List

from app.config.settings import settings
from app.agents.state import RecommendationAgentState
from app.infrastructure.db.database import get_db_manager
from app.infrastructure.db.repositories.college_repository import CollegeRepository
from app.infrastructure.services.college_search_service import CollegeSearchService

logger = logging.getLogger(__name__)


async def researcher_node(state: RecommendationAgentState) -> Dict[str, Any]:
    """
    Researcher node: Implements hybrid search strategy.
    
    Uses CollegeSearchService to:
    1. Check local cache first (fast, no API cost)
    2. Trigger Gemini discovery only if needed
    3. Auto-populate cache with new discoveries
    
    Args:
        state: Current agent state
        
    Returns:
        State updates with discovered universities
    """
    try:
        profile = state["profile"]
        major = profile.get("major", "General Studies")
        student_type = state["student_type"]
        force_refresh = state.get("force_refresh", False)
        
        if force_refresh:
            logger.info(f"Researcher: MAINTENANCE MODE - Force refresh for {major}")
        else:
            logger.info(f"Researcher: Starting hybrid search for {major} ({student_type})")
        
        # Get database session and create service
        db = get_db_manager()
        async with db.session_factory() as session:
            repository = CollegeRepository(session)
            search_service = CollegeSearchService(repository)
            
            # Execute hybrid search (cache-first, then web) or force refresh
            universities = await search_service.hybrid_search(
                major=major,
                profile=profile,
                student_type=student_type,
                limit=20,
                force_refresh=force_refresh
            )
            
            # Commit any new entries added to cache
            await session.commit()
        
        # Convert to matched_universities format for scorer
        matched = []
        sources = []
        for uni in universities:
            matched.append({
                "name": uni.name,
                "acceptance_rate": uni.acceptance_rate,
                "median_gpa": uni.median_gpa,
                "sat_25th": uni.sat_25th,
                "sat_75th": uni.sat_75th,
                "need_blind_international": uni.need_blind_international,
                "data_source": uni.data_source,
            })
            if uni.data_source == "gemini":
                sources.append({
                    "title": uni.name,
                    "uri": f"https://www.google.com/search?q={uni.name.replace(' ', '+')}"
                })
        
        # Log result based on mode
        if force_refresh:
            logger.info(f"Researcher: DATABASE UPDATED - {len(universities)} universities refreshed for {major}")
        else:
            logger.info(f"Researcher: Found {len(universities)} universities ({len(sources)} from web)")
        
        return {
            "matched_universities": matched,
            "research_results": [{
                "query": f"Universities for {major}",
                "sources": sources,
                "content": f"{'Refreshed' if force_refresh else 'Found'} {len(universities)} universities via {'force refresh' if force_refresh else 'hybrid search'}"
            }],
            "search_queries": [f"best {major} programs"],
            "grounding_sources": sources,
            "stream_content": []  # Reserved for final recommendations only
        }
        
    except Exception as e:
        logger.error(f"Researcher node error: {e}")
        
        # Fallback: return empty so scorer uses KNOWN_UNIVERSITIES
        return {
            "error": f"Research failed: {str(e)}",
            "matched_universities": [],
            "research_results": [],
            "search_queries": [],
            "grounding_sources": [],
            "stream_content": []
        }

