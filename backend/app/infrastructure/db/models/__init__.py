"""
SQLModel ORM Models for College List AI

Exports all database models for Alembic autogenerate and application use.
Import models here to register them with SQLModel.metadata.
"""

from app.infrastructure.db.models.base import (
    BaseModel,
    TimestampMixin,
    UUIDMixin,
)
from app.infrastructure.db.models.user_profile import (
    UserProfile,
    UserProfileBase,
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileRead,
)
from app.infrastructure.db.models.college import (
    College,
    CollegeBase,
    CollegeCreate,
    CollegeRead,
)
from app.infrastructure.db.models.chat_thread import ChatThread
from app.infrastructure.db.models.chat_message import ChatMessage
from app.infrastructure.db.models.user_event import (
    UserEvent,
    UserEventCreate,
    UserEventType,
)
from app.infrastructure.db.models.application_outcome import (
    ApplicationOutcome,
    ApplicationOutcomeCreate,
    ApplicationOutcomeUpdate,
    OutcomeStatus,
)
from app.infrastructure.db.models.subscription import SubscriptionModel


__all__ = [
    # Base
    "BaseModel",
    "TimestampMixin",
    "UUIDMixin",
    # UserProfile
    "UserProfile",
    "UserProfileBase",
    "UserProfileCreate",
    "UserProfileUpdate",
    "UserProfileRead",
    # College
    "College",
    "CollegeBase",
    "CollegeCreate",
    "CollegeRead",
    # Chat
    "ChatThread",
    "ChatMessage",
    # Analytics
    "UserEvent",
    "UserEventCreate",
    "UserEventType",
    "ApplicationOutcome",
    "ApplicationOutcomeCreate",
    "ApplicationOutcomeUpdate",
    "OutcomeStatus",
    # Subscription
    "SubscriptionModel",
]

