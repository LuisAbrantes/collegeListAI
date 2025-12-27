"""
Agent State Definitions for College List AI

Defines the TypedDict state that flows through the LangGraph workflow.
State is passed between nodes and accumulated throughout execution.

Key additions:
- conversation_history: Maintains chat memory across turns
- derived_major/minor: Extracted from current prompt (overrides profile)
- query_intent: Classifies user intent for smart responses
"""

from typing import Optional, List, Dict, Any, Literal
from typing_extensions import TypedDict, Annotated
import operator
from enum import Enum


class QueryIntent(str, Enum):
    """
    User query intent classification.
    
    NOTE: Profile updates are done via Settings UI only, not chat.
    """
    GENERATE_LIST = "generate_list"     # "Generate recommendations for me"
    CLARIFY_QUESTION = "clarify"        # "Which major are you considering?"
    FOLLOW_UP = "follow_up"             # "Tell me more about MIT", "Change those"
    GENERAL_CHAT = "general_chat"       # "Hello", "Thanks"


class ChatMessage(TypedDict):
    """Single message in conversation history."""
    role: Literal["user", "assistant"]
    content: str


class StudentProfile(TypedDict, total=False):
    """Student profile subset used in agent state."""
    citizenship_status: str
    nationality: Optional[str]
    gpa: float
    major: str
    minor: Optional[str]  # NEW: Minor field
    sat_score: Optional[int]
    act_score: Optional[int]
    state_of_residence: Optional[str]
    household_income_tier: Optional[str]
    english_proficiency_score: Optional[int]
    english_test_type: Optional[str]
    campus_vibe: Optional[str]
    is_student_athlete: bool
    has_legacy_status: bool
    legacy_universities: Optional[List[str]]
    post_grad_goal: Optional[str]
    is_first_gen: bool
    ap_class_count: Optional[int]
    ap_classes: Optional[List[str]]


class CollegeRecommendation(TypedDict):
    """Single college recommendation."""
    name: str
    label: Literal["Reach", "Target", "Safety"]
    match_score: int
    reasoning: str
    financial_aid_summary: str
    official_url: Optional[str]


class ResearchResult(TypedDict):
    """Result from Google Search grounding."""
    query: str
    sources: List[Dict[str, str]]
    content: str


class RecommendationAgentState(TypedDict):
    """
    State for the recommendation agent workflow.
    
    This state flows through all nodes:
    1. Router: Determines intent, extracts derived major/minor
    2. Researcher: Performs data discovery (if needed)
    3. Analyzer: Matches profile to universities
    4. Scorer: Calculates match scores
    5. Recommender: Generates contextual response
    
    Key Features:
    - conversation_history: Full chat memory for context
    - derived_major/minor: Overrides profile when user specifies in chat
    - query_intent: Determines response type (list vs answer vs update)
    """
    # Input
    user_query: str
    profile: StudentProfile
    excluded_colleges: List[str]
    
    # NEW: Conversation memory
    conversation_history: List[ChatMessage]
    
    # NEW: Derived context from current message (overrides profile)
    derived_major: Optional[str]  # If user says "major is X" in this message
    derived_minor: Optional[str]  # If user says "minor is X" in this message
    
    # NEW: Query intent classification
    query_intent: QueryIntent
    
    # Routing
    student_type: Literal["domestic", "international"]
    is_follow_up: bool  # True if query is a follow-up question
    requested_counts: Dict[str, int]  # Custom counts e.g. {"reach": 1, "target": 2, "safety": 6}
    force_refresh: bool  # True to bypass cache and force web discovery
    
    # Research phase (accumulates via operator.add)
    research_results: Annotated[List[ResearchResult], operator.add]
    search_queries: Annotated[List[str], operator.add]
    
    # Analysis phase (accumulates via operator.add)
    matched_universities: Annotated[List[Dict[str, Any]], operator.add]
    financial_aid_context: str
    
    # Output phase (accumulates via operator.add)
    recommendations: Annotated[List[CollegeRecommendation], operator.add]
    grounding_sources: Annotated[List[Dict[str, str]], operator.add]
    
    # Streaming content
    stream_content: Annotated[List[str], operator.add]
    
    # Error handling
    error: Optional[str]


def create_initial_state(
    user_query: str,
    profile: StudentProfile,
    excluded_colleges: Optional[List[str]] = None,
    conversation_history: Optional[List[ChatMessage]] = None,
) -> RecommendationAgentState:
    """
    Create initial state for the recommendation agent.
    
    Args:
        user_query: User's natural language query
        profile: Student profile data
        excluded_colleges: List of colleges to exclude
        conversation_history: Previous messages in this conversation
        
    Returns:
        Initial RecommendationAgentState
    """
    return RecommendationAgentState(
        user_query=user_query,
        profile=profile,
        excluded_colleges=excluded_colleges or [],
        conversation_history=conversation_history or [],
        derived_major=None,  # Will be set by router if detected
        derived_minor=None,  # Will be set by router if detected
        query_intent=QueryIntent.GENERATE_LIST,  # Default, router will update
        student_type="domestic",  # Will be set by router
        is_follow_up=False,  # Will be set by router
        requested_counts={"reach": 1, "target": 2, "safety": 2},  # Default 1-2-2
        force_refresh=False,  # Will be set by router if maintenance command detected
        research_results=[],
        search_queries=[],
        matched_universities=[],
        financial_aid_context="",
        recommendations=[],
        grounding_sources=[],
        stream_content=[],
        error=None,
    )


def is_domestic_student(profile: StudentProfile) -> bool:
    """Determine if student is domestic (US-based) or international."""
    citizenship = profile.get("citizenship_status", "")
    return citizenship in ["US_CITIZEN", "PERMANENT_RESIDENT", "DACA"]


def get_effective_major(state: RecommendationAgentState) -> str:
    """
    Get the effective major for recommendations.
    
    Priority:
    1. derived_major (from current chat message)
    2. profile.major (from user profile)
    3. "Undeclared" (fallback)
    """
    if state.get("derived_major"):
        return state["derived_major"]
    return state["profile"].get("major", "Undeclared")


def get_effective_minor(state: RecommendationAgentState) -> Optional[str]:
    """
    Get the effective minor for recommendations.
    
    Priority:
    1. derived_minor (from current chat message)
    2. profile.minor (from user profile)
    """
    if state.get("derived_minor"):
        return state["derived_minor"]
    return state["profile"].get("minor")
