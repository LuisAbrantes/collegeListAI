"""
Application Settings for College List AI

Centralized configuration using Pydantic Settings with .env support.
All environment variables are validated at startup.

PROVIDER ARCHITECTURE:
======================
- SEARCH_PROVIDER: Who performs web search for college data
  - perplexity: Perplexity Sonar API (recommended)
  - gemini: Google Gemini with Search Grounding
  
- SYNTHESIS_PROVIDER: Who structures JSON and generates responses
  - groq: Groq Cloud API (fast, LLaMA 3.3)
  - perplexity: Perplexity Sonar (use same API for everything)
  - ollama: Local Ollama (free, no rate limits)
"""

import os
from functools import lru_cache
from typing import Literal, Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Two-provider architecture:
    - SEARCH_PROVIDER: Web search (perplexity or gemini)
    - SYNTHESIS_PROVIDER: JSON structuring + response generation (groq, perplexity, ollama)
    """
    
    # Supabase Configuration
    supabase_url: str
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: str
    
    # Google AI Configuration
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
        # Add your production URL here:
        # "https://your-app.vercel.app",
    ]
    
    # Admin API Key (for protected admin endpoints)
    admin_api_key: Optional[str] = None
    
    # AI/Search Configuration
    search_grounding_enabled: bool = True
    max_recommendations: int = 10
    similarity_threshold: float = 0.7
    
    # ============================================================
    # PROVIDER CONFIGURATION
    # ============================================================
    
    # SEARCH_PROVIDER: Who performs web search for college data
    # - perplexity: Perplexity Sonar API (recommended, best for search)
    # - gemini: Google Gemini with Search Grounding
    search_provider: Literal["perplexity", "gemini"] = "perplexity"
    
    # SYNTHESIS_PROVIDER: Who structures JSON and generates responses
    # - groq: Groq Cloud API (fast inference, LLaMA 3.3)
    # - perplexity: Perplexity Sonar (same API for search + synthesis)
    # - ollama: Local Ollama (free, no rate limits, but slow)
    synthesis_provider: Literal["groq", "perplexity", "ollama"] = "groq"
    
    # ============================================================
    # PROVIDER-SPECIFIC CONFIGURATION
    # ============================================================
    
    # Perplexity Configuration (for search and/or synthesis)
    perplexity_api_key: Optional[str] = None
    perplexity_model: str = "sonar"  # sonar, sonar-pro
    
    # College Scorecard API (official IPEDS data)
    college_scorecard_api_key: Optional[str] = None
    
    # Groq Configuration (for synthesis)
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.3-70b-versatile"  # or mixtral-8x7b-32768
    
    # Ollama Configuration (for synthesis, fully local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:27b"
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    
    # Retry Configuration
    max_retries: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 10.0
    
    # Database Configuration
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
        """Validate API keys based on selected providers."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Normalize gemini_api_key to google_api_key
        if not self.google_api_key and self.gemini_api_key:
            self.google_api_key = self.gemini_api_key
        
        # Validate SEARCH_PROVIDER
        if self.search_provider == "perplexity":
            if not self.perplexity_api_key:
                raise ValueError("PERPLEXITY_API_KEY required when SEARCH_PROVIDER=perplexity")
        elif self.search_provider == "gemini":
            if not self.google_api_key:
                raise ValueError("GOOGLE_API_KEY required when SEARCH_PROVIDER=gemini")
        
        # Validate SYNTHESIS_PROVIDER
        if self.synthesis_provider == "groq":
            if not self.groq_api_key:
                raise ValueError("GROQ_API_KEY required when SYNTHESIS_PROVIDER=groq")
        elif self.synthesis_provider == "perplexity":
            if not self.perplexity_api_key:
                raise ValueError("PERPLEXITY_API_KEY required when SYNTHESIS_PROVIDER=perplexity")
        # ollama doesn't require API keys (local)
        
        logger.info(f"Providers configured: search={self.search_provider}, synthesis={self.synthesis_provider}")
        
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
