"""
Integration tests for the recommendation API endpoints.

Tests the full request/response cycle.
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    def test_root_endpoint(self, client: TestClient):
        """Root endpoint should return welcome message."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    def test_health_endpoint(self, client: TestClient):
        """Health endpoint should return healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestSearchEndpoints:
    """Tests for search endpoints."""
    
    def test_search_requires_query(self, client: TestClient):
        """Search should require a query parameter."""
        response = client.post("/api/search", json={})
        assert response.status_code == 422  # Validation error


class TestRecommendEndpoints:
    """Tests for recommendation endpoints."""
    
    def test_recommend_requires_citizenship_status(self, client: TestClient):
        """Recommend should require citizenship_status."""
        response = client.post("/api/recommend", json={
            "query": "Best CS schools",
            "gpa": 3.7,
            "major": "Computer Science"
        })
        assert response.status_code == 422
    
    def test_recommend_validates_gpa_range(self, client: TestClient):
        """Recommend should validate GPA is between 0.0 and 4.0."""
        response = client.post("/api/recommend", json={
            "query": "Best CS schools",
            "citizenship_status": "US_CITIZEN",
            "gpa": 5.0,  # Invalid
            "major": "Computer Science"
        })
        assert response.status_code == 422
    
    def test_recommend_accepts_valid_domestic_request(
        self,
        client: TestClient,
        sample_recommend_request_domestic
    ):
        """Recommend should accept valid domestic student request.
        
        Note: This test may fail if API calls aren't mocked.
        For CI, you'd want to mock the agent calls.
        """
        # Skip in CI without proper mocking
        pytest.skip("Requires mocked agent calls for CI")
        
        response = client.post("/api/recommend", json=sample_recommend_request_domestic)
        assert response.status_code == 200
