"""
Application Settings for College List AI

Centralized configuration using Pydantic Settings with .env support.
All environment variables are validated at startup.
"""

import os
from functools import lru_cache
from typing import Literal, Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings are validated at startup. Missing required settings
    will cause the application to fail fast with clear error messages.
    """
    
    # Supabase Configuration
    supabase_url: str
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: str
    
    # Google AI Configuration (accepts GOOGLE_API_KEY or GEMINI_API_KEY)
    google_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash"
    embedding_model: str = "text-embedding-004"
    embedding_dimensions: int = 768
    
    # Application Settings
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    
    # CORS Configuration
    frontend_url: str = "http://localhost:5173"
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]
    
    # AI/Search Configuration
    search_grounding_enabled: bool = True
    max_recommendations: int = 10
    similarity_threshold: float = 0.7
    
    # LLM Provider Configuration
    llm_provider: Literal["gemini", "ollama"] = "ollama"  # Default to ollama in dev
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:27b"
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    
    # Retry Configuration
    max_retries: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 10.0
    
    # Database Configuration (SQLModel/SQLAlchemy)
    # Uses SUPABASE_URL + SUPABASE_PASSWORD to construct connection string
    supabase_password: Optional[str] = None
    database_url: Optional[str] = None  # Optional override
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    database_echo: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    @model_validator(mode="after")
    def validate_api_key(self) -> "Settings":
        """Ensure at least one API key is provided when using Gemini."""
        if self.llm_provider == "gemini":
            if not self.google_api_key and not self.gemini_api_key:
                raise ValueError(
                    "Either GOOGLE_API_KEY or GEMINI_API_KEY must be set when using Gemini"
                )
        # Normalize to google_api_key
        if not self.google_api_key and self.gemini_api_key:
            self.google_api_key = self.gemini_api_key
        return self
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are only loaded once,
    improving performance and ensuring consistency.
    """
    return Settings()


# Convenience export for direct import
settings = get_settings()
