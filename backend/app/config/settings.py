"""
Application Settings for College List AI

Centralized configuration using Pydantic Settings with .env support.
All environment variables are validated at startup.

PROVIDER ARCHITECTURE:
======================
- SEARCH_PROVIDER: Perplexity Sonar API (web search for college data)
- SYNTHESIS_PROVIDER: Who structures JSON and generates responses
  - groq: Groq Cloud API (fast, LLaMA 3.3) — default
  - perplexity: Perplexity Sonar (use same API for search + synthesis)
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
    - SEARCH_PROVIDER: Web search (perplexity)
    - SYNTHESIS_PROVIDER: JSON structuring + response generation (groq, perplexity)
    """
    
    # Supabase Configuration
    supabase_url: str
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: str
    supabase_jwt_secret: Optional[str] = None  # Settings > API > JWT Secret (HS256 fallback)
    

    
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
    max_recommendations: int = 10
    similarity_threshold: float = 0.7
    
    # ============================================================
    # PROVIDER CONFIGURATION
    # ============================================================
    
    # SEARCH_PROVIDER: Perplexity Sonar API for web search
    search_provider: Literal["perplexity"] = "perplexity"
    
    # SYNTHESIS_PROVIDER: Who structures JSON and generates responses
    # - groq: Groq Cloud API (fast inference, LLaMA 3.3)
    # - perplexity: Perplexity Sonar (same API for search + synthesis)
    synthesis_provider: Literal["groq", "perplexity"] = "groq"
    
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
    
    # ============================================================
    # STRIPE CONFIGURATION
    # ============================================================
    
    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    
    # Free tier limits
    free_tier_conversations_limit: int = 3
    free_tier_schools_limit: int = 10
    launch_promo_active: bool = True
    
    # Stripe Price IDs - matches .env naming convention
    # Launch prices (promotional)
    stripe_price_id_launch_usd: Optional[str] = None
    stripe_price_id_launch_brl: Optional[str] = None
    # Regular prices (post-launch)
    stripe_price_id_regular_usd: Optional[str] = None
    stripe_price_id_regular_brl: Optional[str] = None
    # Annual prices
    stripe_price_id_annual_usd: Optional[str] = None
    stripe_price_id_annual_brl: Optional[str] = None
    
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
        
        # Perplexity is always required (search provider)
        if not self.perplexity_api_key:
            raise ValueError("PERPLEXITY_API_KEY is required")
        
        # Validate SYNTHESIS_PROVIDER
        if self.synthesis_provider == "groq":
            if not self.groq_api_key:
                raise ValueError("GROQ_API_KEY required when SYNTHESIS_PROVIDER=groq")
        # perplexity key already validated above
        
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
