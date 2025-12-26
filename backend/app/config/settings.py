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
    
    LLM_PROVIDER controls which service handles AI tasks:
    - ollama: Local inference (default for dev, no API costs)
    - gemini: Google Gemini with Search Grounding
    - perplexity: Perplexity Sonar API (best for search, avoids 429s)
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
    
    # UNIFIED LLM Provider Configuration
    # ollama = local inference (free, no rate limits)
    # gemini = Google Gemini with Search Grounding
    # perplexity = Perplexity Sonar API (best for web search)
    llm_provider: Literal["ollama", "gemini", "perplexity"] = "ollama"
    
    # Ollama Configuration (for llm_provider=ollama)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:27b"
    
    # Perplexity Configuration (for llm_provider=perplexity)
    perplexity_api_key: Optional[str] = None
    perplexity_model: str = "sonar"  # sonar (standard), sonar-pro (better)
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    
    # Retry Configuration
    max_retries: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 10.0
    
    # Database Configuration (SQLModel/SQLAlchemy)
    supabase_password: Optional[str] = None
    database_url: Optional[str] = None
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
    def validate_api_keys(self) -> "Settings":
        """Validate API keys based on selected llm_provider."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Normalize gemini_api_key to google_api_key
        if not self.google_api_key and self.gemini_api_key:
            self.google_api_key = self.gemini_api_key
        
        # Validate based on provider
        if self.llm_provider == "gemini":
            if not self.google_api_key:
                raise ValueError(
                    "GOOGLE_API_KEY or GEMINI_API_KEY required when LLM_PROVIDER=gemini"
                )
        
        elif self.llm_provider == "perplexity":
            if not self.perplexity_api_key:
                raise ValueError(
                    "PERPLEXITY_API_KEY required when LLM_PROVIDER=perplexity"
                )
        
        # ollama doesn't require any API keys (local)
        
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
    """Get cached settings instance."""
    return Settings()


# Convenience export for direct import
settings = get_settings()
