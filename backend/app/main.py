"""
College List AI - FastAPI Application

Main entry point for the backend API.
Provides endpoints for profiles, search, and AI recommendations.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.infrastructure.exceptions import (
    CollegeListAIError,
    ValidationError,
    NotFoundError,
    RateLimitError,
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info(f"College List AI Backend starting in {settings.environment} mode...")
    
    # Initialize SQLModel database if URL is configured
    if settings.database_url:
        try:
            from app.infrastructure.db.database import init_db, close_db
            await init_db()
            logger.info("SQLModel database connection pool initialized")
        except Exception as e:
            logger.warning(f"SQLModel database initialization skipped: {e}")
    
    yield
    
    # Shutdown
    if settings.database_url:
        try:
            from app.infrastructure.db.database import close_db
            await close_db()
            logger.info("SQLModel database connection pool closed")
        except Exception as e:
            logger.warning(f"SQLModel database shutdown error: {e}")
    
    logger.info("College List AI Backend shutting down...")


app = FastAPI(
    title="College List AI",
    description="AI-powered college advisor for international students",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.debug,
)

# CORS configuration from Settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
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
