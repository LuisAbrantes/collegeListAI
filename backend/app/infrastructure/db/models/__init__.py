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
    CollegeMetadataSchema,
)
from app.infrastructure.db.models.chat_thread import ChatThread
from app.infrastructure.db.models.chat_message import ChatMessage


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
    "CollegeMetadataSchema",
    # Chat
    "ChatThread",
    "ChatMessage",
]
