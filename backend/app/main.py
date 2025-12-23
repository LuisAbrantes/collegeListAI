"""
College List AI - FastAPI Application

Main entry point for the backend API.
Provides endpoints for profiles, search, and AI recommendations.
"""

import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.infrastructure.exceptions import (
    CollegeListAIError,
    ValidationError,
    NotFoundError,
    RateLimitError,
)

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    print("🚀 College List AI Backend starting...")
    yield
    # Shutdown
    print("👋 College List AI Backend shutting down...")


app = FastAPI(
    title="College List AI",
    description="AI-powered college advisor for international students",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
origins = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    os.getenv("FRONTEND_URL", ""),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in origins if o],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=400,
        content=exc.to_dict(),
    )


@app.exception_handler(NotFoundError)
async def not_found_error_handler(request: Request, exc: NotFoundError):
    """Handle not found errors."""
    return JSONResponse(
        status_code=404,
        content=exc.to_dict(),
    )


@app.exception_handler(RateLimitError)
async def rate_limit_error_handler(request: Request, exc: RateLimitError):
    """Handle rate limit errors."""
    return JSONResponse(
        status_code=429,
        content=exc.to_dict(),
    )


@app.exception_handler(CollegeListAIError)
async def general_error_handler(request: Request, exc: CollegeListAIError):
    """Handle all other application errors."""
    return JSONResponse(
        status_code=500,
        content=exc.to_dict(),
    )


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "college-list-ai"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "College List AI API",
        "version": "1.0.0",
        "docs": "/docs",
    }


# ============================================================================
# Import and register routers
# ============================================================================

from app.api.routes import profiles, search

app.include_router(profiles.router, prefix="/api", tags=["Profiles"])
app.include_router(search.router, prefix="/api", tags=["Search & Recommendations"])
