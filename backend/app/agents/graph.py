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
    Router node: Determines student type and sets routing context.
    
    This is the first node in the workflow. It examines the student
    profile and sets the student_type for conditional branching.
    
    Args:
        state: Current agent state
        
    Returns:
        State updates with student_type set
    """
    profile = state["profile"]
    is_domestic = is_domestic_student(profile)
    student_type: Literal["domestic", "international"] = "domestic" if is_domestic else "international"
    
    logger.info(f"Router: Student classified as {student_type}")
    
    # Build initial stream message
    if is_domestic:
        greeting = f"👋 Hello! I'll help you find great universities as a **domestic student**"
        if profile.get("state_of_residence"):
            greeting += f" from **{profile['state_of_residence']}**"
        greeting += ".\n\n"
    else:
        nationality = profile.get("nationality", "your country")
        greeting = f"👋 Hello! I'll help you find universities that welcome **international students from {nationality}**.\n\n"
    
    return {
        "student_type": student_type,
        "stream_content": [greeting]
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
