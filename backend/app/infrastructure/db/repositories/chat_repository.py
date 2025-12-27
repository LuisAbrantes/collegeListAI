"""
Chat Repository for College List AI

Repository for ChatThread and ChatMessage CRUD operations.
Follows SOLID principles:
- Single Responsibility: Only handles chat data access
- Open/Closed: Extensible via inheritance
- Dependency Inversion: Depends on abstract session interface
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.db.models.chat_thread import ChatThread
from app.infrastructure.db.models.chat_message import ChatMessage


class ChatRepository:
    """
    Repository for chat-related database operations.
    
    Manages both ChatThread and ChatMessage entities.
    """
    
    def __init__(self, session: AsyncSession):
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
        Get all threads for a user, ordered by most recently updated.
        
        Args:
            user_id: The user's UUID
            limit: Maximum threads to return
            offset: Number of threads to skip
            
        Returns:
            List of ChatThread instances
        """
        stmt = (
            select(ChatThread)
            .where(ChatThread.user_id == user_id)
            .order_by(ChatThread.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_thread_by_id(self, thread_id: UUID) -> Optional[ChatThread]:
        """
        Get a thread by its ID.
        
        Args:
            thread_id: The thread's UUID
            
        Returns:
            ChatThread instance or None
        """
        return await self._session.get(ChatThread, thread_id)
    
    async def get_thread_with_messages(
        self,
        thread_id: UUID
    ) -> Optional[ChatThread]:
        """
        Get a thread with all its messages eagerly loaded.
        
        Args:
            thread_id: The thread's UUID
            
        Returns:
            ChatThread with messages or None
        """
        stmt = (
            select(ChatThread)
            .where(ChatThread.id == thread_id)
            .options(selectinload(ChatThread.messages))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_thread(
        self,
        user_id: UUID,
        title: Optional[str] = None,
        langgraph_thread_id: Optional[str] = None
    ) -> ChatThread:
        """
        Create a new chat thread.
        
        Args:
            user_id: The user's UUID
            title: Optional thread title
            langgraph_thread_id: Optional LangGraph thread ID
            
        Returns:
            Created ChatThread instance
        """
        thread = ChatThread(
            user_id=user_id,
            title=title,
            langgraph_thread_id=langgraph_thread_id
        )
        self._session.add(thread)
        await self._session.flush()
        await self._session.refresh(thread)
        return thread
    
    async def update_thread_title(
        self,
        thread_id: UUID,
        title: str
    ) -> Optional[ChatThread]:
        """
        Update a thread's title.
        
        Args:
            thread_id: The thread's UUID
            title: New title
            
        Returns:
            Updated ChatThread or None if not found
        """
        thread = await self.get_thread_by_id(thread_id)
        if not thread:
            return None
        
        thread.title = title
        thread.updated_at = datetime.utcnow()
        self._session.add(thread)
        await self._session.flush()
        await self._session.refresh(thread)
        return thread
    
    async def update_thread_timestamp(self, thread_id: UUID) -> None:
        """
        Update a thread's updated_at timestamp.
        
        Args:
            thread_id: The thread's UUID
        """
        thread = await self.get_thread_by_id(thread_id)
        if thread:
            thread.updated_at = datetime.utcnow()
            self._session.add(thread)
            await self._session.flush()
    
    async def delete_thread(self, thread_id: UUID) -> bool:
        """
        Delete a thread and all its messages (CASCADE).
        
        Args:
            thread_id: The thread's UUID
            
        Returns:
            True if deleted, False if not found
        """
        thread = await self.get_thread_by_id(thread_id)
        if not thread:
            return False
        
        await self._session.delete(thread)
        await self._session.flush()
        return True
    
    async def count_user_threads(self, user_id: UUID) -> int:
        """
        Count total threads for a user.
        
        Args:
            user_id: The user's UUID
            
        Returns:
            Number of threads
        """
        stmt = (
            select(func.count())
            .select_from(ChatThread)
            .where(ChatThread.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
    
    async def get_oldest_thread(self, user_id: UUID) -> Optional[ChatThread]:
        """
        Get the oldest thread for a user (by updated_at).
        
        Args:
            user_id: The user's UUID
            
        Returns:
            Oldest ChatThread or None
        """
        stmt = (
            select(ChatThread)
            .where(ChatThread.user_id == user_id)
            .order_by(ChatThread.updated_at.asc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
    
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
        Get all messages in a thread, ordered by creation time.
        
        Args:
            thread_id: The thread's UUID
            limit: Maximum messages to return
            offset: Number of messages to skip
            
        Returns:
            List of ChatMessage instances
        """
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread_id)
            .order_by(ChatMessage.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def add_message(
        self,
        thread_id: UUID,
        role: str,
        content: str,
        sources: Optional[List[dict]] = None
    ) -> ChatMessage:
        """
        Add a new message to a thread.
        
        Args:
            thread_id: The thread's UUID
            role: Message role ('user' or 'assistant')
            content: Message content
            sources: Optional grounding sources
            
        Returns:
            Created ChatMessage instance
        """
        message = ChatMessage(
            thread_id=thread_id,
            role=role,
            content=content,
            sources=sources
        )
        self._session.add(message)
        await self._session.flush()
        await self._session.refresh(message)
        
        # Update thread timestamp
        await self.update_thread_timestamp(thread_id)
        
        return message
    
    async def get_first_user_message(
        self,
        thread_id: UUID
    ) -> Optional[ChatMessage]:
        """
        Get the first user message in a thread (for title generation).
        
        Args:
            thread_id: The thread's UUID
            
        Returns:
            First user ChatMessage or None
        """
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread_id)
            .where(ChatMessage.role == "user")
            .order_by(ChatMessage.created_at.asc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
