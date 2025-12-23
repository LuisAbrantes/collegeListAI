"""
Dependency Injection Providers for College List AI

Provides FastAPI dependencies for database sessions and repositories.
Follows Dependency Inversion Principle - high-level modules depend on abstractions.
"""

from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.database import get_session
from app.infrastructure.db.repositories import (
    UserProfileRepository,
    CollegeRepository,
)


# Type alias for session dependency
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_user_profile_repository(
    session: SessionDep,
) -> AsyncGenerator[UserProfileRepository, None]:
    """
    Dependency provider for UserProfileRepository.
    
    Usage:
        @router.get("/profile")
        async def get_profile(
            repo: UserProfileRepository = Depends(get_user_profile_repository)
        ):
            ...
    """
    yield UserProfileRepository(session)


async def get_college_repository(
    session: SessionDep,
) -> AsyncGenerator[CollegeRepository, None]:
    """
    Dependency provider for CollegeRepository.
    """
    yield CollegeRepository(session)


# Type aliases for repository dependencies
UserProfileRepoDep = Annotated[
    UserProfileRepository, 
    Depends(get_user_profile_repository)
]
CollegeRepoDep = Annotated[
    CollegeRepository, 
    Depends(get_college_repository)
]
