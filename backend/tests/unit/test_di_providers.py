"""
Unit tests for Dependency Injection providers.

Validates that:
- DI factory functions return singleton instances via @lru_cache
- Service classes no longer use __new__ singleton pattern
- Services can be independently instantiated for testing
"""

import pytest
import sys
from unittest.mock import patch, MagicMock


# Mock slowapi before it's imported by search.py
if "slowapi" not in sys.modules:
    _mock_slowapi = MagicMock()
    _mock_slowapi.Limiter = MagicMock(return_value=MagicMock())
    sys.modules["slowapi"] = _mock_slowapi
    sys.modules["slowapi.util"] = MagicMock()


class TestDIProviders:
    """Tests for @lru_cache DI provider functions."""



    def test_vector_service_no_singleton_pattern(self):
        """VectorService should NOT have __new__ singleton override."""
        from app.infrastructure.db.vector_service import VectorService
        
        assert VectorService.__new__ is object.__new__



    def test_vector_di_provider_is_cached(self):
        """get_vector_service should return same instance."""
        from app.api.routes.search import get_vector_service
        
        get_vector_service.cache_clear()
        
        with patch("app.infrastructure.db.vector_service.create_client") as mock_sb:
            with patch("app.infrastructure.db.vector_service.SentenceTransformer") as mock_st:
                mock_sb.return_value = MagicMock()
                
                svc1 = get_vector_service()
                svc2 = get_vector_service()
                
                assert svc1 is svc2
        
        get_vector_service.cache_clear()


class TestDIOverrides:
    """Tests validating DI override pattern for testing."""

    def test_vector_service_accepts_no_args(self):
        """VectorService constructor should take no arguments."""
        from app.infrastructure.db.vector_service import VectorService
        import inspect
        
        sig = inspect.signature(VectorService.__init__)
        params = [p for name, p in sig.parameters.items() if name != "self"]
        assert len(params) == 0, f"Expected no args, got: {[p.name for p in params]}"

    def test_profile_repo_accepts_session(self):
        """UserProfileRepository constructor should accept a session arg."""
        from app.infrastructure.db.repositories.user_profile_repository import UserProfileRepository
        import inspect
        
        sig = inspect.signature(UserProfileRepository.__init__)
        params = [name for name in sig.parameters if name != "self"]
        assert "session" in params, f"Expected 'session' arg, got: {params}"
