"""
LangGraph Workflow for College List AI

Orchestrates the recommendation agent with conditional branching
for domestic vs international students.

Workflow:
    START → router → researcher → analyzer → scorer → recommender → END

The router determines the student type and sets context for
subsequent nodes to apply appropriate logic.
"""

import logging
from typing import Literal, AsyncGenerator, Dict, Any

from langgraph.graph import StateGraph, START, END

from app.agents.state import (
    RecommendationAgentState,
    StudentProfile,
    create_initial_state,
    is_domestic_student,
)
from app.agents.nodes.researcher import researcher_node
from app.agents.nodes.analyzer import analyzer_node
from app.agents.nodes.scorer import scorer_node
from app.agents.nodes.recommender import recommender_node

logger = logging.getLogger(__name__)


# =============================================================================
# Router Node
# =============================================================================

async def router_node(state: RecommendationAgentState) -> Dict[str, Any]:
    """
    Router node: Determines student type, detects follow-up questions, and maintenance commands.
    
    This is the first node in the workflow. It examines the student
    profile and user query to determine:
    1. Student type (domestic vs international)
    2. Whether this is a follow-up question (scholarship details, etc.)
    3. Maintenance commands (force refresh/update database)
    
    Note: We intentionally don't add greeting to stream_content here.
    The stream_content is reserved for the final recommendation output only.
    This prevents "thinking" text from appearing in the response.
    
    Args:
        state: Current agent state
        
    Returns:
        State updates with student_type, follow-up flag, and force_refresh flag
    """
    profile = state["profile"]
    query = state.get("user_query", "").lower()
    is_domestic = is_domestic_student(profile)
    student_type: Literal["domestic", "international"] = "domestic" if is_domestic else "international"
    
    # Detect MAINTENANCE COMMANDS (force refresh / update database)
    # Pattern: User wants to bypass cache and fetch fresh data from web
    maintenance_keywords = [
        "atualizar banco", "atualiza banco", "atualizar dados", "atualiza dados",
        "refresh data", "refresh database", "update database", "update db",
        "buscar dados reais", "dados reais", "buscar novos dados",
        "force refresh", "forçar atualização", "limpar cache", "clear cache",
        "fetch real data", "get real data", "sync database", "sincronizar"
    ]
    force_refresh = any(keyword in query for keyword in maintenance_keywords)
    
    if force_refresh:
        logger.info(f"Router: MAINTENANCE MODE - Force refresh requested for query: '{query}'")
    
    # Detect follow-up question patterns
    follow_up_keywords = [
        "what about", "how about", "tell me more", "explain",
        "scholarship", "scholarships", "financial aid", "aid package",
        "why", "cost", "tuition", "price", "fee",
    ]
    is_follow_up = any(keyword in query for keyword in follow_up_keywords) and len(query) < 100
    
    # Parse requested counts from query (e.g., "6 safeties", "3 reach schools")
    import re
    requested_counts = {"reach": 1, "target": 2, "safety": 2}  # Default 1-2-2
    
    # Pattern: "N safety/safeties/reach/target"
    count_patterns = [
        (r"(\d+)\s*(?:safety|safeties)", "safety"),
        (r"(\d+)\s*(?:reach|reaches)", "reach"),
        (r"(\d+)\s*(?:target|targets)", "target"),
    ]
    
    for pattern, category in count_patterns:
        match = re.search(pattern, query)
        if match:
            requested_counts[category] = min(int(match.group(1)), 10)  # Cap at 10
            logger.info(f"Router: Detected request for {requested_counts[category]} {category} schools")
    
    logger.info(f"Router: Student classified as {student_type}")
    logger.info(f"Router: Requested counts = {requested_counts}")
    if is_follow_up:
        logger.info(f"Router: Detected follow-up question: '{query}'")
    
    # Log context for debugging (not streamed to user)
    if is_domestic:
        state_res = profile.get("state_of_residence", "US")
        logger.info(f"Router: Domestic student from {state_res}")
    else:
        nationality = profile.get("nationality", "unknown")
        logger.info(f"Router: International student from {nationality}")
    
    # Return routing decision, follow-up flag, force_refresh, and requested counts
    return {
        "student_type": student_type,
        "is_follow_up": is_follow_up,
        "force_refresh": force_refresh,
        "requested_counts": requested_counts,
        "stream_content": []  # Reserved for final recommendations only
    }


# =============================================================================
# Graph Builder
# =============================================================================

def build_recommendation_graph() -> StateGraph:
    """
    Build the LangGraph workflow for college recommendations.
    
    Flow: START → router → researcher → analyzer → scorer → recommender → END
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the graph with our state type
    builder = StateGraph(RecommendationAgentState)
    
    # Add nodes
    builder.add_node("router", router_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("analyzer", analyzer_node)
    builder.add_node("scorer", scorer_node)
    builder.add_node("recommender", recommender_node)
    
    # Add edges - now includes scorer between analyzer and recommender
    builder.add_edge(START, "router")
    builder.add_edge("router", "researcher")
    builder.add_edge("researcher", "analyzer")
    builder.add_edge("analyzer", "scorer")
    builder.add_edge("scorer", "recommender")
    builder.add_edge("recommender", END)
    
    # Compile and return
    return builder.compile()


# Create singleton graph instance
_graph = None

def get_recommendation_graph() -> StateGraph:
    """Get or create the recommendation graph singleton."""
    global _graph
    if _graph is None:
        _graph = build_recommendation_graph()
        logger.info("Recommendation graph compiled successfully")
    return _graph


# =============================================================================
# Public API
# =============================================================================

async def generate_recommendations(
    user_query: str,
    profile: StudentProfile,
    excluded_colleges: list[str] | None = None,
) -> Dict[str, Any]:
    """
    Generate college recommendations using the agent workflow.
    
    Args:
        user_query: User's natural language query
        profile: Student profile data
        excluded_colleges: Colleges to exclude from recommendations
        
    Returns:
        Final state with recommendations and sources
    """
    graph = get_recommendation_graph()
    
    # Create initial state
    initial_state = create_initial_state(
        user_query=user_query,
        profile=profile,
        excluded_colleges=excluded_colleges
    )
    
    # Run the graph
    result = await graph.ainvoke(initial_state)
    
    return result


async def stream_recommendations(
    user_query: str,
    profile: StudentProfile,
    excluded_colleges: list[str] | None = None,
) -> AsyncGenerator[str, None]:
    """
    Stream college recommendations as they're generated.
    
    Yields text chunks as each node produces output.
    
    Args:
        user_query: User's natural language query
        profile: Student profile data
        excluded_colleges: Colleges to exclude
        
    Yields:
        Text chunks for SSE streaming
    """
    graph = get_recommendation_graph()
    
    # Create initial state
    initial_state = create_initial_state(
        user_query=user_query,
        profile=profile,
        excluded_colleges=excluded_colleges
    )
    
    # Stream with updates mode to get node outputs
    async for event in graph.astream(initial_state, stream_mode="updates"):
        # Each event is {node_name: state_update}
        for node_name, update in event.items():
            # Yield any stream content from this node
            stream_content = update.get("stream_content", [])
            for chunk in stream_content:
                if chunk:
                    yield chunk
            
            # Check for errors
            if update.get("error"):
                logger.error(f"Node {node_name} error: {update['error']}")
