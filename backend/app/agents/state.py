"""
Agent State Definitions for College List AI

Defines the TypedDict state that flows through the LangGraph workflow.
State is passed between nodes and accumulated throughout execution.
"""

from typing import Optional, List, Dict, Any, Literal
from typing_extensions import TypedDict, Annotated
import operator


class StudentProfile(TypedDict, total=False):
    """Student profile subset used in agent state."""
    citizenship_status: str
    nationality: Optional[str]
    gpa: float
    major: str
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
    1. Router: Determines International vs Domestic path
    2. Researcher: Performs Google Search grounding
    3. Analyzer: Matches profile to universities
    4. Recommender: Generates final recommendations
    """
    # Input
    user_query: str
    profile: StudentProfile
    excluded_colleges: List[str]
    
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
    excluded_colleges: Optional[List[str]] = None
) -> RecommendationAgentState:
    """
    Create initial state for the recommendation agent.
    
    Args:
        user_query: User's natural language query
        profile: Student profile data
        excluded_colleges: List of colleges to exclude
        
    Returns:
        Initial RecommendationAgentState
    """
    return RecommendationAgentState(
        user_query=user_query,
        profile=profile,
        excluded_colleges=excluded_colleges or [],
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
