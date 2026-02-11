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
    CollegeMajorStatsRepository,
)
from app.infrastructure.db.repositories.chat_repository import (
    ChatRepository,
)
from app.infrastructure.db.repositories.user_event_repository import (
    UserEventRepository,
)
from app.infrastructure.db.repositories.application_outcome_repository import (
    ApplicationOutcomeRepository,
)
from app.infrastructure.db.repositories.subscription_repository import (
    SubscriptionRepository,
    get_subscription_repository,
)


__all__ = [
    # Base
    "BaseRepository",
    "IReadRepository",
    "IWriteRepository",
    # Repositories
    "UserProfileRepository",
    "CollegeRepository",
    "CollegeMajorStatsRepository",
    "ChatRepository",
    "UserEventRepository",
    "ApplicationOutcomeRepository",
    "SubscriptionRepository",
    "get_subscription_repository",
]
