"""
Repository Layer for College List AI

Exports all repository classes for dependency injection.
"""

from app.infrastructure.db.repositories.base_repository import (
    BaseRepository,
    IReadRepository,
    IWriteRepository,
)
from app.infrastructure.db.repositories.user_profile_repository import (
    UserProfileRepository,
)
from app.infrastructure.db.repositories.college_repository import (
    CollegeRepository,
)


__all__ = [
    # Base
    "BaseRepository",
    "IReadRepository",
    "IWriteRepository",
    # Repositories
    "UserProfileRepository",
    "CollegeRepository",
]
