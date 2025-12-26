"""
LangGraph Workflow for College List AI

Orchestrates the recommendation agent with:
- Intent classification (generate list, clarify, update profile, follow-up)
- Major/minor extraction from prompts (overrides profile)
- Conditional routing for domestic vs international students

Workflow:
    START → router → [conditional] → researcher → analyzer → scorer → recommender → END
"""

import re
import logging
from typing import Literal, AsyncGenerator, Dict, Any, Optional, Tuple

from langgraph.graph import StateGraph, START, END

from app.agents.state import (
    RecommendationAgentState,
    StudentProfile,
    QueryIntent,
    ChatMessage,
    create_initial_state,
    is_domestic_student,
)
from app.agents.nodes.researcher import researcher_node
from app.agents.nodes.analyzer import analyzer_node
from app.agents.nodes.scorer import scorer_node
from app.agents.nodes.recommender import recommender_node

logger = logging.getLogger(__name__)


# =============================================================================
# Intent Classification Patterns
# =============================================================================

# Patterns for extracting major from user message
MAJOR_PATTERNS = [
    r"(?:my |her |his )?major (?:is|será|é|will be|was) (\w+(?:\s+\w+){0,2})",
    r"(?:i'm |she's |he's )?(?:studying|majoring in) (\w+(?:\s+\w+){0,2})",
    r"(?:i |she |he )?(?:chose|chose to study|want to study) (\w+(?:\s+\w+){0,2})",
    r"(?:for |in )(\w+(?:\s+\w+){0,2}) major",
]

# Patterns for extracting minor from user message
MINOR_PATTERNS = [
    r"(?:my |her |his )?minor (?:is|será|é|will be) (\w+(?:\s+\w+){0,2})",
    r"(?:i'm |she's |he's )?minoring in (\w+(?:\s+\w+){0,2})",
    r"(?:with )?(?:a )?minor (?:in|of) (\w+(?:\s+\w+){0,2})",
]

# Keywords for intent classification
GENERATE_LIST_KEYWORDS = [
    "recommend", "recommendations", "suggest", "list", "colleges", "universities",
    "generate", "build", "create", "give me", "show me", "find",
    "reach", "target", "safety", "safeties",
]

CLARIFY_KEYWORDS = [
    "what", "which", "how", "why", "when", "where", "who",
    "explain", "tell me about", "can you",
]

UPDATE_KEYWORDS = [
    "major is", "minor is", "gpa is", "my score", "i have",
    "actually", "change", "update", "correct",
]

FOLLOW_UP_KEYWORDS = [
    "more about", "tell me more", "what about", "how about",
    "specifically", "detail", "scholarship", "financial aid",
    "cost", "tuition", "chances",
]


def _extract_major_minor(query: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract major and minor from user query.
    
    Returns:
        Tuple of (major, minor), either can be None if not found
    """
    query_lower = query.lower()
    
    # Extract major
    derived_major = None
    for pattern in MAJOR_PATTERNS:
        match = re.search(pattern, query_lower)
        if match:
            derived_major = match.group(1).strip().title()
            logger.info(f"Router: Extracted major from prompt: '{derived_major}'")
            break
    
    # Extract minor
    derived_minor = None
    for pattern in MINOR_PATTERNS:
        match = re.search(pattern, query_lower)
        if match:
            derived_minor = match.group(1).strip().title()
            logger.info(f"Router: Extracted minor from prompt: '{derived_minor}'")
            break
    
    return derived_major, derived_minor


def _classify_intent(query: str, has_history: bool) -> QueryIntent:
    """
    Classify user query intent.
    
    Priority:
    1. UPDATE_PROFILE - User is providing new information
    2. FOLLOW_UP - User is asking about previous recommendations
    3. CLARIFY_QUESTION - User is asking a question (not about recs)
    4. GENERATE_LIST - User wants recommendations
    5. GENERAL_CHAT - Default fallback
    """
    query_lower = query.lower()
    
    # Check for profile updates (highest priority - user is correcting/adding info)
    for keyword in UPDATE_KEYWORDS:
        if keyword in query_lower:
            return QueryIntent.UPDATE_PROFILE
    
    # Check for follow-up questions (needs context from history)
    if has_history:
        for keyword in FOLLOW_UP_KEYWORDS:
            if keyword in query_lower:
                return QueryIntent.FOLLOW_UP
    
    # Check for recommendation generation requests
    for keyword in GENERATE_LIST_KEYWORDS:
        if keyword in query_lower:
            return QueryIntent.GENERATE_LIST
    
    # Check for clarifying questions
    if query_lower.rstrip("?").split()[0] in ["what", "which", "how", "why", "when", "where", "who"]:
        return QueryIntent.CLARIFY_QUESTION
    
    for keyword in CLARIFY_KEYWORDS:
        if keyword in query_lower:
            return QueryIntent.CLARIFY_QUESTION
    
    # Default: If user has history, likely follow-up; otherwise generate list
    if has_history and len(query) < 100:
        return QueryIntent.FOLLOW_UP
    
    return QueryIntent.GENERATE_LIST


# =============================================================================
# Router Node
# =============================================================================

async def router_node(state: RecommendationAgentState) -> Dict[str, Any]:
    """
    Router node: Smart routing with intent classification and context extraction.
    
    This node examines the user query to:
    1. Extract major/minor overrides from the prompt
    2. Classify query intent (generate list, clarify, update, follow-up)
    3. Determine student type (domestic vs international)
    4. Parse custom recommendation counts
    5. Detect maintenance commands
    
    IMPORTANT: Data from the current prompt OVERRIDES stored profile data.
    This ensures user corrections are respected.
    """
    profile = state["profile"]
    query = state.get("user_query", "")
    query_lower = query.lower()
    conversation_history = state.get("conversation_history", [])
    
    # === 1. Extract major/minor from prompt (OVERRIDES profile) ===
    derived_major, derived_minor = _extract_major_minor(query)
    
    # === 2. Classify query intent ===
    query_intent = _classify_intent(query, len(conversation_history) > 0)
    logger.info(f"Router: Query intent classified as {query_intent.value}")
    
    # === 3. Determine student type ===
    is_domestic = is_domestic_student(profile)
    student_type: Literal["domestic", "international"] = "domestic" if is_domestic else "international"
    
    # === 4. Detect maintenance commands ===
    maintenance_keywords = [
        "atualizar banco", "atualiza banco", "atualizar dados", "atualiza dados",
        "refresh data", "refresh database", "update database", "update db",
        "buscar dados reais", "dados reais", "buscar novos dados",
        "force refresh", "forçar atualização", "limpar cache", "clear cache",
        "fetch real data", "get real data", "sync database", "sincronizar"
    ]
    force_refresh = any(keyword in query_lower for keyword in maintenance_keywords)
    
    if force_refresh:
        logger.info(f"Router: MAINTENANCE MODE - Force refresh requested")
    
    # === 5. Detect follow-up patterns ===
    follow_up_keywords = [
        "what about", "how about", "tell me more", "explain",
        "scholarship", "scholarships", "financial aid", "aid package",
        "why", "cost", "tuition", "price", "fee",
    ]
    is_follow_up = (
        query_intent == QueryIntent.FOLLOW_UP or 
        any(keyword in query_lower for keyword in follow_up_keywords)
    )
    
    # === 6. Parse requested counts from query ===
    requested_counts = {"reach": 1, "target": 2, "safety": 2}  # Default 1-2-2
    
    count_patterns = [
        (r"(\d+)\s*(?:safety|safeties)", "safety"),
        (r"(\d+)\s*(?:reach|reaches)", "reach"),
        (r"(\d+)\s*(?:target|targets)", "target"),
    ]
    
    for pattern, category in count_patterns:
        match = re.search(pattern, query_lower)
        if match:
            requested_counts[category] = min(int(match.group(1)), 10)
            logger.info(f"Router: Detected request for {requested_counts[category]} {category} schools")
    
    # === Log routing decision ===
    logger.info(f"Router: Student type = {student_type}")
    logger.info(f"Router: Counts = {requested_counts}")
    
    if derived_major:
        logger.info(f"Router: Using derived major '{derived_major}' (overrides profile)")
    if derived_minor:
        logger.info(f"Router: Using derived minor '{derived_minor}'")
    
    if is_domestic:
        state_res = profile.get("state_of_residence", "US")
        logger.info(f"Router: Domestic student from {state_res}")
    else:
        nationality = profile.get("nationality", "unknown")
        logger.info(f"Router: International student from {nationality}")
    
    return {
        "student_type": student_type,
        "is_follow_up": is_follow_up,
        "force_refresh": force_refresh,
        "requested_counts": requested_counts,
        "derived_major": derived_major,
        "derived_minor": derived_minor,
        "query_intent": query_intent,
        "stream_content": []  # Reserved for final recommendations only
    }


# =============================================================================
# Conditional Router
# =============================================================================

def should_skip_research(state: RecommendationAgentState) -> str:
    """
    Determine if we should skip research phase.
    
    Skip research for:
    - CLARIFY_QUESTION: Just answer the question
    - UPDATE_PROFILE: Just acknowledge the update
    - GENERAL_CHAT: Just respond conversationally
    """
    intent = state.get("query_intent", QueryIntent.GENERATE_LIST)
    
    if intent in [QueryIntent.CLARIFY_QUESTION, QueryIntent.UPDATE_PROFILE, QueryIntent.GENERAL_CHAT]:
        logger.info(f"Router: Skipping research for intent {intent.value}")
        return "skip_to_recommender"
    
    return "run_research"


# =============================================================================
# Graph Builder
# =============================================================================

def build_recommendation_graph() -> StateGraph:
    """
    Build the LangGraph workflow for college recommendations.
    
    Flow (conditional):
    - For GENERATE_LIST/FOLLOW_UP:
        START → router → researcher → analyzer → scorer → recommender → END
    - For CLARIFY/UPDATE/CHAT:
        START → router → recommender → END (skips research)
    """
    builder = StateGraph(RecommendationAgentState)
    
    # Add nodes
    builder.add_node("router", router_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("analyzer", analyzer_node)
    builder.add_node("scorer", scorer_node)
    builder.add_node("recommender", recommender_node)
    
    # Add edges with conditional routing
    builder.add_edge(START, "router")
    
    # Conditional: Skip research for non-recommendation queries
    builder.add_conditional_edges(
        "router",
        should_skip_research,
        {
            "run_research": "researcher",
            "skip_to_recommender": "recommender",
        }
    )
    
    # Research path continues through all nodes
    builder.add_edge("researcher", "analyzer")
    builder.add_edge("analyzer", "scorer")
    builder.add_edge("scorer", "recommender")
    builder.add_edge("recommender", END)
    
    return builder.compile()


# Create singleton graph instance
_graph = None

def get_recommendation_graph() -> StateGraph:
    """Get or create the recommendation graph singleton."""
    global _graph
    if _graph is None:
        _graph = build_recommendation_graph()
        logger.info("Recommendation graph compiled successfully with conditional routing")
    return _graph


# =============================================================================
# Public API
# =============================================================================

async def generate_recommendations(
    user_query: str,
    profile: StudentProfile,
    excluded_colleges: list[str] | None = None,
    conversation_history: list[ChatMessage] | None = None,
) -> Dict[str, Any]:
    """
    Generate college recommendations using the agent workflow.
    
    Args:
        user_query: User's natural language query
        profile: Student profile data
        excluded_colleges: Colleges to exclude from recommendations
        conversation_history: Previous messages in this conversation
        
    Returns:
        Final state with recommendations and sources
    """
    graph = get_recommendation_graph()
    
    # Create initial state with conversation history
    initial_state = create_initial_state(
        user_query=user_query,
        profile=profile,
        excluded_colleges=excluded_colleges,
        conversation_history=conversation_history,
    )
    
    # Run the graph
    result = await graph.ainvoke(initial_state)
    
    return result


async def stream_recommendations(
    user_query: str,
    profile: StudentProfile,
    excluded_colleges: list[str] | None = None,
    conversation_history: list[ChatMessage] | None = None,
) -> AsyncGenerator[str, None]:
    """
    Stream college recommendations as they're generated.
    
    Yields text chunks as each node produces output.
    """
    graph = get_recommendation_graph()
    
    # Create initial state with conversation history
    initial_state = create_initial_state(
        user_query=user_query,
        profile=profile,
        excluded_colleges=excluded_colleges,
        conversation_history=conversation_history,
    )
    
    # Stream with updates mode to get node outputs
    async for event in graph.astream(initial_state, stream_mode="updates"):
        for node_name, update in event.items():
            stream_content = update.get("stream_content", [])
            for chunk in stream_content:
                if chunk:
                    yield chunk
            
            if update.get("error"):
                logger.error(f"Node {node_name} error: {update['error']}")
