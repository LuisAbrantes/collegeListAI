"""
Integration Tests for Authentication

Verifies that the main application correctly integrates:
- JWT verification dependency
- Protected route denial (401)
- Protected route access (200) w/ valid token
"""

import pytest
from unittest.mock import AsyncMock
from app.infrastructure.db.dependencies import UserProfileRepoDep

class TestAuthIntegration:
    
    def test_protected_route_no_auth(self, client):
        """Accessing a protected route without auth should return 401."""
        response = client.get("/api/profiles/me")
        assert response.status_code == 401
        assert response.json()["detail"] == "Missing authorization token"

    def test_protected_route_invalid_token(self, client):
        """Accessing with invalid token should return 401."""
        response = client.get(
            "/api/profiles/me", 
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert response.status_code == 401

    def test_protected_route_valid_auth(self, client, auth_headers, app, mock_user_id):
        """Accessing with valid token should reach the route logic (mocked repo)."""
        
        from app.infrastructure.db.dependencies import get_user_profile_repository
        
        # Mock the repo dependency to return a profile or 404
        mock_repo = AsyncMock()
        mock_repo.get_by_user_id.return_value = None  # Simulate no profile yet
        
        # Override the dependency FUNCTION, not the type alias
        app.dependency_overrides[get_user_profile_repository] = lambda: mock_repo
        
        response = client.get("/api/profiles/me", headers=auth_headers)
        
        # Should be 404 because repo returned None
        assert response.status_code == 404
        assert f"No profile found for user {mock_user_id}" in response.json()["detail"]
        
        # Verify repo was called
        assert mock_repo.get_by_user_id.called
