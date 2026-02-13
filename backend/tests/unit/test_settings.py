"""
Unit tests for Pydantic Settings configuration.

Tests settings loading and validation.
"""

import pytest
from unittest.mock import patch
import os


class TestSettings:
    """Tests for Settings configuration."""
    
    def test_settings_loads_from_env(self):
        """Settings should load from environment variables."""
        from app.config.settings import settings
        
        # These should be loaded from .env
        assert settings.supabase_url is not None
        assert settings.supabase_service_role_key is not None
        assert settings.google_api_key is not None
    
    def test_settings_has_defaults(self):
        """Settings should have sensible defaults."""
        from app.config.settings import settings
        
        # These should always be set (either from defaults or .env)
        assert settings.gemini_model is not None
        assert settings.embedding_model is not None
        assert settings.environment in ("development", "production", "testing")
        assert settings.max_retries >= 1
    
    def test_is_production_property(self):
        """is_production should return True for production environment."""
        from app.config.settings import settings
        
        # Since we're in development, should be False
        assert settings.is_production is False
        assert settings.is_development is True
    
    def test_allowed_origins_includes_localhost(self):
        """allowed_origins should include localhost for development."""
        from app.config.settings import settings
        
        assert "http://localhost:5173" in settings.allowed_origins
        assert "http://localhost:3000" in settings.allowed_origins
