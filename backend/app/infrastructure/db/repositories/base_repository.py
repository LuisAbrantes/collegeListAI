"""
Base Repository for College List AI

Generic async repository implementing CRUD operations.
Follows SOLID principles:
- Single Responsibility: Only handles data access logic
- Open/Closed: Extensible via inheritance
- Liskov Substitution: Concrete repos can replace base
- Interface Segregation: Separate interfaces for read/write
- Dependency Inversion: Depends on SQLModel abstractions
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Type
from uuid import UUID

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel


# Type variables for generic repository
ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=SQLModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=SQLModel)


class IReadRepository(ABC, Generic[ModelType]):
    """
    Interface for read operations (Interface Segregation Principle).
    
    Separates read concerns from write concerns.
    """
    
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[ModelType]:
        """Get a single record by ID."""
        pass
    
    @abstractmethod
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Get all records with pagination."""
        pass
    
    @abstractmethod
    async def exists(self, id: UUID) -> bool:
        """Check if a record exists."""
        pass


class IWriteRepository(ABC, Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Interface for write operations (Interface Segregation Principle).
    
    Separates write concerns from read concerns.
    """
    
    @abstractmethod
    async def create(self, data: CreateSchemaType) -> ModelType:
        """Create a new record."""
        pass
    
    @abstractmethod
    async def update(
        self,
        id: UUID,
        data: UpdateSchemaType
    ) -> Optional[ModelType]:
        """Update an existing record."""
        pass
    
    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete a record by ID."""
        pass


class BaseRepository(
    IReadRepository[ModelType],
    IWriteRepository[ModelType, CreateSchemaType, UpdateSchemaType],
    Generic[ModelType, CreateSchemaType, UpdateSchemaType]
):
    """
    Generic async repository with CRUD operations.
    
    Follows Dependency Inversion - depends on abstract session interface.
    Implements both read and write interfaces for full CRUD.
    
    Args:
        model: The SQLModel class to operate on
        session: Async database session
    """
    
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self._model = model
        self._session = session
    
    @property
    def session(self) -> AsyncSession:
        """Get the current session."""
        return self._session
    
    async def get_by_id(self, id: UUID) -> Optional[ModelType]:
        """
        Get a single record by its primary key.
        
        Args:
            id: UUID primary key
            
        Returns:
            Model instance or None if not found
        """
        result = await self._session.get(self._model, id)
        return result
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        Get all records with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            
        Returns:
            List of model instances
        """
        stmt = select(self._model).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def exists(self, id: UUID) -> bool:
        """
        Check if a record exists.
        
        Args:
            id: UUID primary key
            
        Returns:
            True if exists, False otherwise
        """
        result = await self.get_by_id(id)
        return result is not None
    
    async def create(self, data: CreateSchemaType) -> ModelType:
        """
        Create a new record.
        
        Args:
            data: Create schema with field values
            
        Returns:
            Created model instance
        """
        db_obj = self._model.model_validate(data)
        self._session.add(db_obj)
        await self._session.flush()
        await self._session.refresh(db_obj)
        return db_obj
    
    async def update(
        self,
        id: UUID,
        data: UpdateSchemaType
    ) -> Optional[ModelType]:
        """
        Update an existing record.
        
        Args:
            id: UUID primary key
            data: Update schema with fields to modify
            
        Returns:
            Updated model instance or None if not found
        """
        db_obj = await self.get_by_id(id)
        if not db_obj:
            return None
        
        # Get update data, excluding unset fields
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        self._session.add(db_obj)
        await self._session.flush()
        await self._session.refresh(db_obj)
        return db_obj
    
    async def delete(self, id: UUID) -> bool:
        """
        Delete a record by ID.
        
        Args:
            id: UUID primary key
            
        Returns:
            True if deleted, False if not found
        """
        db_obj = await self.get_by_id(id)
        if not db_obj:
            return False
        
        await self._session.delete(db_obj)
        await self._session.flush()
        return True
    
    async def create_many(self, data_list: List[CreateSchemaType]) -> List[ModelType]:
        """
        Bulk create multiple records.
        
        Args:
            data_list: List of create schemas
            
        Returns:
            List of created model instances
        """
        db_objects = [self._model.model_validate(data) for data in data_list]
        self._session.add_all(db_objects)
        await self._session.flush()
        for obj in db_objects:
            await self._session.refresh(obj)
        return db_objects
    
    async def count(self) -> int:
        """
        Get total count of records.
        
        Returns:
            Total number of records
        """
        from sqlalchemy import func
        stmt = select(func.count()).select_from(self._model)
        result = await self._session.execute(stmt)
        return result.scalar_one()
