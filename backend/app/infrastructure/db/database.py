"""
Database Configuration for College List AI

Async SQLAlchemy engine and session management following SOLID principles:
- Single Responsibility: Only handles database connection and session lifecycle
- Open/Closed: Configurable via Settings without code changes
- Liskov Substitution: Session interface is consistent
- Interface Segregation: Minimal interface exposed
- Dependency Inversion: Depends on abstractions (Settings), not concretions
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from sqlmodel import SQLModel

from app.config.settings import settings


class DatabaseManager:
    """
    Manages async database connections and sessions.
    
    Implements Singleton pattern for connection pooling efficiency.
    Follows Interface Segregation by exposing only necessary methods.
    """
    
    _instance: Optional["DatabaseManager"] = None
    _engine: Optional[AsyncEngine] = None
    _session_factory: Optional[async_sessionmaker[AsyncSession]] = None
    
    def __new__(cls) -> "DatabaseManager":
        """Singleton pattern ensures single connection pool."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def engine(self) -> AsyncEngine:
        """Get or create async engine with connection pooling."""
        if self._engine is None:
            self._initialize_engine()
        return self._engine
    
    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get or create session factory."""
        if self._session_factory is None:
            self._initialize_engine()
        return self._session_factory
    
    def _initialize_engine(self) -> None:
        """
        Initialize async engine with optimal pooling configuration.
        
        Derives PostgreSQL connection URL from SUPABASE_URL.
        Format: https://[project-ref].supabase.co -> postgresql+asyncpg://...
        """
        # Derive database URL from Supabase URL
        database_url = self._get_database_url_from_supabase()
        
        self._engine = create_async_engine(
            database_url,
            echo=settings.database_echo,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            pool_pre_ping=True,  # Verify connections before use
        )
        
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    
    def _get_database_url_from_supabase(self) -> str:
        """
        Get PostgreSQL connection URL for SQLModel.
        
        Derives from SUPABASE_URL + SUPABASE_PASSWORD, or uses DATABASE_URL if provided.
        """
        import re
        from urllib.parse import quote_plus
        
        # Use explicit DATABASE_URL if provided
        if settings.database_url:
            database_url = settings.database_url
            if database_url.startswith("postgresql://"):
                database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
            return database_url
        
        # Derive from SUPABASE_URL + SUPABASE_PASSWORD
        if not settings.supabase_url or not settings.supabase_password:
            raise ValueError(
                "Either DATABASE_URL or (SUPABASE_URL + SUPABASE_PASSWORD) is required. "
                "Add SUPABASE_PASSWORD to your .env file."
            )
        
        # Extract project reference from Supabase URL
        match = re.match(r'https?://([^.]+)\.supabase\.co', settings.supabase_url)
        if not match:
            raise ValueError(f"Invalid SUPABASE_URL format: {settings.supabase_url}")
        
        project_ref = match.group(1)
        password = quote_plus(settings.supabase_password)
        
        # Use direct database connection (not pooler) for migrations
        # Format: postgres://postgres.[ref]:[password]@db.[ref].supabase.co:5432/postgres
        database_url = (
            f"postgresql+asyncpg://postgres:{password}"
            f"@db.{project_ref}.supabase.co:5432/postgres"
        )
        
        return database_url
    
    async def create_tables(self) -> None:
        """Create all tables from SQLModel metadata."""
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
    
    async def drop_tables(self) -> None:
        """Drop all tables (use with caution, mainly for testing)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
    
    async def close(self) -> None:
        """Close engine and dispose of connection pool."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None


# Global instance (lazy initialization)
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get or create the database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection for async database sessions.
    
    Usage in FastAPI:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session)):
            ...
    
    Yields:
        AsyncSession: Database session that auto-closes after use
    """
    db = get_db_manager()
    async with db.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions outside FastAPI requests.
    
    Usage:
        async with get_session_context() as session:
            result = await session.execute(query)
    """
    db = get_db_manager()
    async with db.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize database connection pool (called on app startup)."""
    db = get_db_manager()
    # Verify connection works
    async with db.session_factory() as session:
        await session.execute(text("SELECT 1"))


async def close_db() -> None:
    """Close database connection pool (called on app shutdown)."""
    db = get_db_manager()
    await db.close()
