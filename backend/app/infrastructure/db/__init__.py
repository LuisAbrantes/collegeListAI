"""
Database Infrastructure Package for College List AI

Exports database utilities, models, and repositories.
"""

from app.infrastructure.db.database import (
    DatabaseManager,
    get_db_manager,
    get_session,
    get_session_context,
    init_db,
    close_db,
)

from app.infrastructure.db.dependencies import (
    SessionDep,
    get_user_profile_repository,
    get_college_repository,
    UserProfileRepoDep,
    CollegeRepoDep,
)


__all__ = [
    # Database management
    "DatabaseManager",
    "get_db_manager",
    "get_session",
    "get_session_context",
    "init_db",
    "close_db",
    # Dependencies
    "SessionDep",
    "get_user_profile_repository",
    "get_college_repository",
    "UserProfileRepoDep",
    "CollegeRepoDep",
]
