"""
UserProfile Repository for College List AI

Specialized repository for user profile operations.
Extends base repository with profile-specific queries.
"""

from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.user_profile import (
    UserProfile,
    UserProfileCreate,
    UserProfileUpdate,
)
from app.infrastructure.db.repositories.base_repository import BaseRepository


class UserProfileRepository(
    BaseRepository[UserProfile, UserProfileCreate, UserProfileUpdate]
):
    """
    Repository for UserProfile CRUD and specialized queries.
    
    Extends base repository with profile-specific operations:
    - get_by_user_id: Find profile by authenticated user
    - get_or_create: Upsert pattern for profile management
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(UserProfile, session)
    
    async def get_by_user_id(self, user_id: UUID) -> Optional[UserProfile]:
        """
        Get a profile by the authenticated user's ID.
        
        Args:
            user_id: The auth user's UUID (not profile ID)
            
        Returns:
            UserProfile or None if not found
        """
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def exists_for_user(self, user_id: UUID) -> bool:
        """
        Check if a profile exists for a user.
        
        Args:
            user_id: The auth user's UUID
            
        Returns:
            True if profile exists
        """
        profile = await self.get_by_user_id(user_id)
        return profile is not None
    
    async def create_for_user(
        self,
        user_id: UUID,
        data: UserProfileCreate
    ) -> UserProfile:
        """
        Create a new profile for a user.
        
        Args:
            user_id: The auth user's UUID
            data: Profile creation data
            
        Returns:
            Created UserProfile
        """
        now = datetime.now(timezone.utc)
        
        profile = UserProfile(
            user_id=user_id,
            created_at=now,
            updated_at=now,
            **data.model_dump()
        )
        
        self.session.add(profile)
        await self.session.flush()
        await self.session.refresh(profile)
        return profile
    
    async def update_by_user_id(
        self,
        user_id: UUID,
        data: UserProfileUpdate
    ) -> Optional[UserProfile]:
        """
        Update a profile by user ID.
        
        Args:
            user_id: The auth user's UUID
            data: Fields to update
            
        Returns:
            Updated UserProfile or None if not found
        """
        profile = await self.get_by_user_id(user_id)
        if not profile:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now(timezone.utc)
        
        for field, value in update_data.items():
            setattr(profile, field, value)
        
        self.session.add(profile)
        await self.session.flush()
        await self.session.refresh(profile)
        return profile
    
    async def delete_by_user_id(self, user_id: UUID) -> bool:
        """
        Delete a profile by user ID.
        
        Args:
            user_id: The auth user's UUID
            
        Returns:
            True if deleted, False if not found
        """
        profile = await self.get_by_user_id(user_id)
        if not profile:
            return False
        
        await self.session.delete(profile)
        await self.session.flush()
        return True
    
    async def get_or_create(
        self,
        user_id: UUID,
        default_data: UserProfileCreate
    ) -> Tuple[UserProfile, bool]:
        """
        Get existing profile or create a new one.
        
        Args:
            user_id: The auth user's UUID
            default_data: Data to use if creating
            
        Returns:
            Tuple of (UserProfile, was_created)
        """
        existing = await self.get_by_user_id(user_id)
        if existing:
            return existing, False
        
        created = await self.create_for_user(user_id, default_data)
        return created, True
