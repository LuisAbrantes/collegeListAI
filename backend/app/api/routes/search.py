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
    """Request for AI recommendations."""
    query: str = Field(..., min_length=1, max_length=2000)
    nationality: str = Field(..., min_length=2, max_length=100)
    gpa: float = Field(..., ge=0.0, le=4.0)
    major: str = Field(..., min_length=2, max_length=100)
    excluded_colleges: Optional[List[str]] = None


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
# Recommendation Endpoints
# ============================================================================

@router.post("/recommend")
async def get_recommendations(
    request: RecommendRequest,
    vector_service: VectorService = Depends(get_vector_service),
    gemini_service: GeminiService = Depends(get_gemini_service)
):
    """
    Get AI-powered college recommendations.
    
    1. Searches for similar colleges using vector similarity
    2. Passes results to Gemini for personalized recommendations
    3. Returns recommendations with Reach/Target/Safety labels
    """
    try:
        # First, get similar colleges from vector search
        similar_colleges = await vector_service.search_similar_colleges(
            query_text=request.query,
            threshold=0.6,
            limit=20,
            exclude_ids=None,
        )
        
        # Convert to dict format for Gemini
        colleges_data = [
            {
                "name": c.name,
                "metadata": c.metadata.model_dump() if c.metadata else {},
                "similarity": c.similarity,
            }
            for c in similar_colleges
        ]
        
        # Get AI recommendations
        response = await gemini_service.generate_recommendations(
            user_query=request.query,
            nationality=request.nationality,
            gpa=request.gpa,
            major=request.major,
            excluded_colleges=request.excluded_colleges,
            similar_colleges=colleges_data,
        )
        
        return response
        
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except (VectorServiceError, AIServiceError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend/stream")
async def stream_recommendations(
    request: RecommendRequest,
    gemini_service: GeminiService = Depends(get_gemini_service)
):
    """
    Stream AI recommendations via Server-Sent Events (SSE).
    
    Provides real-time streaming of the AI response for better UX.
    """
    async def event_generator():
        try:
            async for chunk in gemini_service.stream_recommendations(
                user_query=request.query,
                nationality=request.nationality,
                gpa=request.gpa,
                major=request.major,
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
