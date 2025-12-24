"""
Search & Recommendations Routes

Endpoints for vector similarity search and AI recommendations.
Supports SSE streaming for real-time responses.
"""

import json
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.infrastructure.db.vector_service import VectorService
from app.infrastructure.ai.gemini_service import GeminiService
from app.infrastructure.exceptions import (
    VectorServiceError,
    AIServiceError,
    RateLimitError,
)


router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class SearchRequest(BaseModel):
    """Request for vector similarity search."""
    query: str = Field(..., min_length=1, max_length=1000)
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    limit: int = Field(default=10, ge=1, le=50)


class CollegeResult(BaseModel):
    """College search result."""
    id: str
    name: str
    content: Optional[str] = None
    similarity: float


class SearchResponse(BaseModel):
    """Search response with results."""
    results: List[CollegeResult]
    query: str
    total: int


class RecommendRequest(BaseModel):
    """
    Request for AI recommendations with full student profile.
    
    Uses LangGraph agent workflow with automatic International vs Domestic routing.
    """
    query: str = Field(..., min_length=1, max_length=2000)
    
    # Core identification
    citizenship_status: Optional[str] = Field(None, description="US_CITIZEN, PERMANENT_RESIDENT, INTERNATIONAL, DACA")
    nationality: Optional[str] = Field(None, min_length=2, max_length=100)
    
    # Academic metrics
    gpa: float = Field(..., ge=0.0, le=4.0)
    major: str = Field(..., min_length=2, max_length=100)
    sat_score: Optional[int] = Field(None, ge=400, le=1600)
    act_score: Optional[int] = Field(None, ge=1, le=36)
    
    # US-specific fields
    state_of_residence: Optional[str] = Field(None, max_length=50)
    
    # Financial info
    household_income_tier: Optional[str] = Field(None, description="LOW, MEDIUM, HIGH")
    
    # International-specific
    english_proficiency_score: Optional[int] = Field(None, ge=0, le=160, description="TOEFL (120 max), IELTS (9 max), Duolingo (160 max)")
    english_test_type: Optional[str] = Field(None, description="TOEFL, IELTS, DUOLINGO")
    
    # Fit factors
    campus_vibe: Optional[str] = Field(None, description="URBAN, SUBURBAN, RURAL")
    is_student_athlete: bool = Field(False)
    has_legacy_status: bool = Field(False)
    legacy_universities: Optional[List[str]] = None
    post_grad_goal: Optional[str] = Field(None, description="JOB_PLACEMENT, GRADUATE_SCHOOL, ENTREPRENEURSHIP, UNDECIDED")
    is_first_gen: bool = Field(False)
    ap_class_count: Optional[int] = Field(None, ge=0, le=20)
    ap_classes: Optional[List[str]] = None
    
    # Exclusions
    excluded_colleges: Optional[List[str]] = None
    
    # Chat persistence
    thread_id: Optional[str] = Field(None, description="Chat thread ID for persistence")


class ExclusionRequest(BaseModel):
    """Request to add a college exclusion."""
    college_name: str = Field(..., min_length=1, max_length=200)


class ExclusionResponse(BaseModel):
    """Exclusion response."""
    user_id: str
    college_name: str
    created_at: str


# ============================================================================
# Dependency Injection
# ============================================================================

def get_vector_service() -> VectorService:
    """Get vector service instance."""
    return VectorService()


def get_gemini_service() -> GeminiService:
    """Get Gemini service instance."""
    return GeminiService()


async def get_current_user_id(
    authorization: Optional[str] = Header(None)
) -> UUID:
    """Extract user ID from authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization scheme")
        return UUID(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization token")


# ============================================================================
# Search Endpoints
# ============================================================================

@router.post("/search", response_model=SearchResponse)
async def search_colleges(
    request: SearchRequest,
    vector_service: VectorService = Depends(get_vector_service)
):
    """
    Search for similar colleges using vector similarity.
    
    Uses the query text to find colleges with similar embeddings
    in the colleges_cache table.
    """
    try:
        results = await vector_service.search_similar_colleges(
            query_text=request.query,
            threshold=request.threshold,
            limit=request.limit,
        )
        
        return SearchResponse(
            results=[
                CollegeResult(
                    id=str(r.id),
                    name=r.name,
                    content=r.metadata.model_dump_json() if r.metadata else None,
                    similarity=r.similarity,
                )
                for r in results
            ],
            query=request.query,
            total=len(results),
        )
    except VectorServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Recommendation Endpoints (LangGraph Agent)
# ============================================================================

@router.post("/recommend")
async def get_recommendations(
    request: RecommendRequest,
):
    """
    Get AI-powered college recommendations using LangGraph agent.
    
    Features:
    - Automatic International vs Domestic routing
    - Google Search grounding for real-time data
    - Financial aid context based on student type
    
    Returns complete recommendations (non-streaming).
    """
    from app.agents.graph import generate_recommendations
    from app.agents.state import StudentProfile
    
    try:
        # Build profile from request
        profile: StudentProfile = {
            "citizenship_status": request.citizenship_status,
            "nationality": request.nationality,
            "gpa": request.gpa,
            "major": request.major,
            "sat_score": request.sat_score,
            "act_score": request.act_score,
            "state_of_residence": request.state_of_residence,
            "household_income_tier": request.household_income_tier,
            "english_proficiency_score": request.english_proficiency_score,
            "english_test_type": request.english_test_type,
            "campus_vibe": request.campus_vibe,
            "is_student_athlete": request.is_student_athlete,
            "has_legacy_status": request.has_legacy_status,
            "legacy_universities": request.legacy_universities,
            "post_grad_goal": request.post_grad_goal,
            "is_first_gen": request.is_first_gen,
            "ap_class_count": request.ap_class_count,
            "ap_classes": request.ap_classes,
        }
        
        # Run agent workflow
        result = await generate_recommendations(
            user_query=request.query,
            profile=profile,
            excluded_colleges=request.excluded_colleges,
        )
        
        # Extract content from result
        return {
            "content": "".join(result.get("stream_content", [])),
            "student_type": result.get("student_type"),
            "search_queries": result.get("search_queries", []),
            "sources": result.get("grounding_sources", []),
        }
        
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except AIServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend/debug")
async def debug_request(request_data: dict):
    """Debug endpoint to see raw request body."""
    import logging
    logging.info(f"DEBUG REQUEST BODY: {request_data}")
    return {"received": request_data}


@router.post("/recommend/stream")
async def stream_recommendations(
    request: RecommendRequest,
):
    """
    Stream AI recommendations via Server-Sent Events (SSE).
    
    Uses LangGraph agent workflow with:
    - Automatic International vs Domestic routing
    - Google Search grounding for real-time data
    - Financial aid context based on student type
    """
    from app.agents.graph import stream_recommendations as agent_stream
    from app.agents.state import StudentProfile
    
    async def event_generator():
        try:
            # Build profile from request
            profile: StudentProfile = {
                "citizenship_status": request.citizenship_status,
                "nationality": request.nationality,
                "gpa": request.gpa,
                "major": request.major,
                "sat_score": request.sat_score,
                "act_score": request.act_score,
                "state_of_residence": request.state_of_residence,
                "household_income_tier": request.household_income_tier,
                "english_proficiency_score": request.english_proficiency_score,
                "english_test_type": request.english_test_type,
                "campus_vibe": request.campus_vibe,
                "is_student_athlete": request.is_student_athlete,
                "has_legacy_status": request.has_legacy_status,
                "legacy_universities": request.legacy_universities,
                "post_grad_goal": request.post_grad_goal,
                "is_first_gen": request.is_first_gen,
                "ap_class_count": request.ap_class_count,
                "ap_classes": request.ap_classes,
            }
            
            # Stream from agent
            async for chunk in agent_stream(
                user_query=request.query,
                profile=profile,
                excluded_colleges=request.excluded_colleges,
            ):
                yield {
                    "event": "chunk",
                    "data": json.dumps({"text": chunk}),
                }
            
            yield {
                "event": "complete",
                "data": json.dumps({"status": "done"}),
            }
            
        except RateLimitError as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": "rate_limit", "message": str(e)}),
            }
        except AIServiceError as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": "ai_error", "message": str(e)}),
            }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": "unknown", "message": str(e)}),
            }
    
    return EventSourceResponse(event_generator())


# ============================================================================
# Exclusion Endpoints
# ============================================================================

@router.get("/exclusions")
async def get_exclusions(
    user_id: UUID = Depends(get_current_user_id),
    vector_service: VectorService = Depends(get_vector_service)
):
    """Get all college exclusions for the current user."""
    # Note: This would use a dedicated exclusion service in production
    # For now, we return an empty list as a placeholder
    return {"exclusions": [], "user_id": str(user_id)}


@router.post("/exclusions", response_model=ExclusionResponse, status_code=201)
async def add_exclusion(
    request: ExclusionRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """Add a college to the user's exclusion list."""
    # This would use the Supabase client directly
    from app.domain.services import UserProfileService
    
    # In a full implementation, you'd have an ExclusionService
    return ExclusionResponse(
        user_id=str(user_id),
        college_name=request.college_name,
        created_at="2024-01-01T00:00:00Z",  # Placeholder
    )


@router.delete("/exclusions/{college_name}", status_code=204)
async def remove_exclusion(
    college_name: str,
    user_id: UUID = Depends(get_current_user_id)
):
    """Remove a college from the user's exclusion list."""
    # This would use the Supabase client directly
    pass
