"""
User Profile Service

Handles CRUD operations for student profiles (nationality, GPA, major).
Uses Supabase as the persistence layer with proper error handling.
"""

import os
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

from app.domain.models import (
    UserProfile,
    UserProfileCreate,
    UserProfileUpdate,
)
from app.infrastructure.exceptions import (
    DatabaseError,
    NotFoundError,
    DuplicateError,
    ConfigurationError,
)


class UserProfileService:
    """
    Service for managing user profiles with CRUD operations.
    
    Handles:
    - Profile creation with validation
    - Profile retrieval by user_id
    - Profile updates (partial)
    - Profile deletion
    """
    
    _instance: Optional["UserProfileService"] = None
    _client: Optional[Client] = None
    
    def __new__(cls) -> "UserProfileService":
        """Singleton pattern for connection pooling."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Supabase client with connection pooling."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ConfigurationError(
                "Missing Supabase configuration",
                missing_keys=["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
            )
        
        # Configure client with connection pooling options
        options = ClientOptions(
            postgrest_client_timeout=10,
            storage_client_timeout=30,
        )
        
        self._client = create_client(supabase_url, supabase_key, options)
    
    @property
    def client(self) -> Client:
        """Get the Supabase client instance."""
        if self._client is None:
            self._initialize_client()
        return self._client
    
    async def create_profile(
        self, 
        user_id: UUID, 
        data: UserProfileCreate
    ) -> UserProfile:
        """
        Create a new user profile.
        
        Args:
            user_id: The authenticated user's UUID
            data: Profile creation data (nationality, GPA, major)
            
        Returns:
            The created UserProfile
            
        Raises:
            DuplicateError: If a profile already exists for this user
            DatabaseError: If the database operation fails
        """
        try:
            # Check for existing profile
            existing = self.client.table("profiles").select("id").eq(
                "user_id", str(user_id)
            ).maybe_single().execute()
            
            if existing.data:
                raise DuplicateError(
                    f"Profile already exists for user {user_id}",
                    operation="create",
                    table="profiles"
                )
            
            now = datetime.now(timezone.utc).isoformat()
            
            result = self.client.table("profiles").insert({
                "user_id": str(user_id),
                "nationality": data.nationality,
                "gpa": data.gpa,
                "major": data.major,
                "created_at": now,
                "updated_at": now,
            }).execute()
            
            if not result.data:
                raise DatabaseError(
                    "Failed to create profile",
                    operation="insert",
                    table="profiles"
                )
            
            return UserProfile(**result.data[0])
            
        except (DuplicateError, DatabaseError):
            raise
        except Exception as e:
            raise DatabaseError(
                f"Unexpected error creating profile: {str(e)}",
                operation="insert",
                table="profiles",
                original_error=e
            )
    
    async def get_profile(self, user_id: UUID) -> UserProfile:
        """
        Retrieve a user's profile.
        
        Args:
            user_id: The user's UUID
            
        Returns:
            The user's profile
            
        Raises:
            NotFoundError: If no profile exists for this user
            DatabaseError: If the database operation fails
        """
        try:
            result = self.client.table("profiles").select("*").eq(
                "user_id", str(user_id)
            ).maybe_single().execute()
            
            if not result.data:
                raise NotFoundError(
                    f"No profile found for user {user_id}",
                    operation="select",
                    table="profiles"
                )
            
            return UserProfile(**result.data)
            
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(
                f"Error retrieving profile: {str(e)}",
                operation="select",
                table="profiles",
                original_error=e
            )
    
    async def update_profile(
        self, 
        user_id: UUID, 
        data: UserProfileUpdate
    ) -> UserProfile:
        """
        Update a user's profile (partial update).
        
        Args:
            user_id: The user's UUID
            data: Fields to update (only non-None values are updated)
            
        Returns:
            The updated UserProfile
            
        Raises:
            NotFoundError: If no profile exists for this user
            DatabaseError: If the database operation fails
        """
        try:
            # Build update dict with only provided fields
            update_data = data.model_dump(exclude_none=True)
            
            if not update_data:
                # No fields to update, just return existing profile
                return await self.get_profile(user_id)
            
            update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            result = self.client.table("profiles").update(update_data).eq(
                "user_id", str(user_id)
            ).execute()
            
            if not result.data:
                raise NotFoundError(
                    f"No profile found for user {user_id}",
                    operation="update",
                    table="profiles"
                )
            
            return UserProfile(**result.data[0])
            
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(
                f"Error updating profile: {str(e)}",
                operation="update",
                table="profiles",
                original_error=e
            )
    
    async def delete_profile(self, user_id: UUID) -> bool:
        """
        Delete a user's profile.
        
        Args:
            user_id: The user's UUID
            
        Returns:
            True if deletion was successful
            
        Raises:
            NotFoundError: If no profile exists for this user
            DatabaseError: If the database operation fails
        """
        try:
            result = self.client.table("profiles").delete().eq(
                "user_id", str(user_id)
            ).execute()
            
            if not result.data:
                raise NotFoundError(
                    f"No profile found for user {user_id}",
                    operation="delete",
                    table="profiles"
                )
            
            return True
            
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(
                f"Error deleting profile: {str(e)}",
                operation="delete",
                table="profiles",
                original_error=e
            )
    
    async def get_or_create_profile(
        self, 
        user_id: UUID, 
        default_data: UserProfileCreate
    ) -> tuple[UserProfile, bool]:
        """
        Get an existing profile or create a new one.
        
        Args:
            user_id: The user's UUID
            default_data: Data to use if creating a new profile
            
        Returns:
            Tuple of (UserProfile, was_created)
        """
        try:
            profile = await self.get_profile(user_id)
            return profile, False
        except NotFoundError:
            profile = await self.create_profile(user_id, default_data)
            return profile, True
