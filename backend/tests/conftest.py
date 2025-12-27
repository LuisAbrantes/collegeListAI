"""
Test configuration and fixtures for College List AI.

Provides shared fixtures for unit and integration tests.
"""

import pytest
from typing import AsyncGenerator
from unittest.mock import MagicMock, AsyncMock

from fastapi.testclient import TestClient
from httpx import AsyncClient


# =============================================================================
# App Fixtures
# =============================================================================

@pytest.fixture
def app():
    """Get the FastAPI application."""
    from app.main import app
    return app


@pytest.fixture
def client(app):
    """Get synchronous test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Get async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_gemini_service():
    """Mock for GeminiService."""
    mock = MagicMock()
    mock.stream_recommendations = AsyncMock()
    mock.generate_recommendations = AsyncMock()
    return mock


@pytest.fixture
def mock_vector_service():
    """Mock for VectorService."""
    mock = MagicMock()
    mock.search_similar_colleges = AsyncMock(return_value=[])
    mock.generate_embedding = AsyncMock(return_value=[0.1] * 768)
    return mock


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_domestic_profile():
    """Sample domestic student profile."""
    return {
        "citizenship_status": "US_CITIZEN",
        "nationality": "United States",
        "gpa": 3.7,
        "major": "Computer Science",
        "sat_score": 1450,
        "act_score": None,
        "state_of_residence": "California",
        "household_income_tier": "MEDIUM",
        "english_proficiency_score": None,
        "english_test_type": None,
        "campus_vibe": "URBAN",
        "is_student_athlete": False,
        "has_legacy_status": False,
        "legacy_universities": None,
        "post_grad_goal": "JOB_PLACEMENT",
        "is_first_gen": True,
        "ap_class_count": 5,
        "ap_classes": ["AP Computer Science", "AP Calculus BC"],
    }


@pytest.fixture
def sample_international_profile():
    """Sample international student profile."""
    return {
        "citizenship_status": "INTERNATIONAL",
        "nationality": "Brazil",
        "gpa": 3.8,
        "major": "Computer Science",
        "sat_score": 1480,
        "act_score": None,
        "state_of_residence": None,
        "household_income_tier": "LOW",
        "english_proficiency_score": 105,
        "english_test_type": "TOEFL",
        "campus_vibe": "SUBURBAN",
        "is_student_athlete": False,
        "has_legacy_status": False,
        "legacy_universities": None,
        "post_grad_goal": "GRADUATE_SCHOOL",
        "is_first_gen": False,
        "ap_class_count": 0,
        "ap_classes": None,
    }


@pytest.fixture
def sample_recommend_request_domestic(sample_domestic_profile):
    """Sample recommend request for domestic student."""
    return {
        "query": "Best CS schools in California with good financial aid",
        **sample_domestic_profile,
        "excluded_colleges": None,
    }


@pytest.fixture
def sample_recommend_request_international(sample_international_profile):
    """Sample recommend request for international student."""
    return {
        "query": "Universities with need-blind admission for international CS students",
        **sample_international_profile,
        "excluded_colleges": ["MIT"],
    }
