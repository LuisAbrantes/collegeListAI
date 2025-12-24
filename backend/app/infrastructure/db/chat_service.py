"""
Chat Service for College List AI

Business logic layer for chat operations.
Follows SOLID principles:
- Single Responsibility: Only handles chat business logic
- Open/Closed: Extensible without modification
- Dependency Inversion: Depends on repository abstraction
"""

from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.chat_repository import ChatRepository
from app.infrastructure.db.models.chat_thread import ChatThread
from app.infrastructure.db.models.chat_message import ChatMessage
from app.domain.chat import (
    MessageRole,
    ChatThreadCreate,
    ChatMessageCreate,
)


class ChatService:
    """
    Service for chat business logic.
    
    Implements:
    - 5-thread limit enforcement
    - Auto-generated titles from first message
    - LangGraph thread ID management
    """
    
    MAX_THREADS_PER_USER = 5
    TITLE_MAX_LENGTH = 50
    
    def __init__(self, session: AsyncSession):
        self._repository = ChatRepository(session)
        self._session = session
    
    # =========================================================================
    # Thread Operations
    # =========================================================================
    
    async def get_user_threads(
        self,
        user_id: UUID,
        limit: int = 10,
        offset: int = 0
    ) -> List[ChatThread]:
        """
        Get all threads for a user.
        
        Args:
            user_id: The user's UUID
            limit: Maximum threads to return
            offset: Number to skip
            
        Returns:
            List of threads ordered by updated_at desc
        """
        return await self._repository.get_user_threads(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
    
    async def get_thread(self, thread_id: UUID) -> Optional[ChatThread]:
        """
        Get a thread by ID.
        
        Args:
            thread_id: The thread's UUID
            
        Returns:
            ChatThread or None
        """
        return await self._repository.get_thread_by_id(thread_id)
    
    async def get_thread_with_messages(
        self,
        thread_id: UUID
    ) -> Optional[ChatThread]:
        """
        Get a thread with all messages.
        
        Args:
            thread_id: The thread's UUID
            
        Returns:
            ChatThread with messages or None
        """
        return await self._repository.get_thread_with_messages(thread_id)
    
    async def create_thread(
        self,
        user_id: UUID,
        title: Optional[str] = None
    ) -> ChatThread:
        """
        Create a new thread, enforcing the 5-thread limit.
        
        If user has >= 5 threads, the oldest is deleted.
        
        Args:
            user_id: The user's UUID
            title: Optional title (auto-generated from first message if None)
            
        Returns:
            Created ChatThread
        """
        # Enforce thread limit
        await self._enforce_thread_limit(user_id)
        
        # Generate LangGraph thread ID
        langgraph_thread_id = str(uuid4())
        
        return await self._repository.create_thread(
            user_id=user_id,
            title=title,
            langgraph_thread_id=langgraph_thread_id
        )
    
    async def delete_thread(self, thread_id: UUID) -> bool:
        """
        Delete a thread and all its messages.
        
        Args:
            thread_id: The thread's UUID
            
        Returns:
            True if deleted, False if not found
        """
        return await self._repository.delete_thread(thread_id)
    
    async def _enforce_thread_limit(self, user_id: UUID) -> None:
        """
        Enforce the maximum thread limit per user.
        
        If at limit, delete the oldest thread.
        """
        count = await self._repository.count_user_threads(user_id)
        
        if count >= self.MAX_THREADS_PER_USER:
            oldest = await self._repository.get_oldest_thread(user_id)
            if oldest:
                await self._repository.delete_thread(oldest.id)
    
    # =========================================================================
    # Message Operations
    # =========================================================================
    
    async def get_thread_messages(
        self,
        thread_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[ChatMessage]:
        """
        Get all messages in a thread.
        
        Args:
            thread_id: The thread's UUID
            limit: Maximum messages to return
            offset: Number to skip
            
        Returns:
            List of messages ordered by created_at asc
        """
        return await self._repository.get_thread_messages(
            thread_id=thread_id,
            limit=limit,
            offset=offset
        )
    
    async def add_message(
        self,
        thread_id: UUID,
        role: MessageRole,
        content: str,
        sources: Optional[List[dict]] = None
    ) -> ChatMessage:
        """
        Add a message to a thread.
        
        If this is the first user message and thread has no title,
        auto-generate the title.
        
        Args:
            thread_id: The thread's UUID
            role: Message role (user/assistant)
            content: Message content
            sources: Optional grounding sources
            
        Returns:
            Created ChatMessage
        """
        message = await self._repository.add_message(
            thread_id=thread_id,
            role=role.value,
            content=content,
            sources=sources
        )
        
        # Auto-generate title if first user message
        if role == MessageRole.USER:
            thread = await self._repository.get_thread_by_id(thread_id)
            if thread and not thread.title:
                title = self._generate_title(content)
                await self._repository.update_thread_title(thread_id, title)
        
        return message
    
    def _generate_title(self, content: str) -> str:
        """
        Generate a thread title from message content.
        
        Args:
            content: First user message content
            
        Returns:
            Truncated title (max 50 chars)
        """
        # Clean up the content
        title = content.strip()
        
        # Truncate if too long
        if len(title) > self.TITLE_MAX_LENGTH:
            title = title[:self.TITLE_MAX_LENGTH - 3] + "..."
        
        return title
