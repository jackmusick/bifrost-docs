"""
Base Repository

Provides common database operations for all repositories.
Uses SQLAlchemy async session for all operations.
"""

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from src.models.orm.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Base repository with common CRUD operations.

    Provides a consistent interface for database access across all models.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_by_id(self, id: UUID) -> ModelT | None:
        """
        Get entity by ID.

        Args:
            id: Entity UUID

        Returns:
            Entity or None if not found
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0, is_enabled: bool | None = None) -> list[ModelT]:
        """
        Get all entities with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            is_enabled: Filter by is_enabled status (None = no filter)

        Returns:
            List of entities
        """
        query = select(self.model)

        if is_enabled is not None and hasattr(self.model, 'is_enabled'):
            query = query.where(self.model.is_enabled == is_enabled)  # type: ignore[attr-defined]

        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, entity: ModelT) -> ModelT:
        """
        Create a new entity.

        Args:
            entity: Entity to create

        Returns:
            Created entity with generated ID
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: ModelT) -> ModelT:
        """
        Update an existing entity.

        Args:
            entity: Entity with updated values

        Returns:
            Updated entity
        """
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        """
        Delete an entity.

        Args:
            entity: Entity to delete
        """
        await self.session.delete(entity)
        await self.session.flush()

    async def delete_by_id(self, id: UUID) -> bool:
        """
        Delete entity by ID.

        Args:
            id: Entity UUID

        Returns:
            True if deleted, False if not found
        """
        entity = await self.get_by_id(id)
        if entity:
            await self.delete(entity)
            return True
        return False

    async def get_paginated(
        self,
        *,
        filters: list[ColumnElement[bool]] | None = None,
        search_columns: list[str] | None = None,
        search_term: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        limit: int = 100,
        offset: int = 0,
        options: list[Any] | None = None,
    ) -> tuple[list[ModelT], int]:
        """
        Get paginated results with optional search and sorting.

        Args:
            filters: List of SQLAlchemy filter conditions
            search_columns: List of column names to search in
            search_term: Search term to match against search_columns
            sort_by: Column name to sort by
            sort_dir: Sort direction ("asc" or "desc")
            limit: Maximum number of results
            offset: Number of results to skip
            options: SQLAlchemy options (e.g., joinedload)

        Returns:
            Tuple of (list of entities, total count)
        """
        query = select(self.model)
        count_query = select(func.count(self.model.id))  # type: ignore[attr-defined]

        # Apply query options (e.g., joinedload for relationships)
        if options:
            for opt in options:
                query = query.options(opt)

        # Apply filters
        if filters:
            for f in filters:
                query = query.where(f)
                count_query = count_query.where(f)

        # Apply search across specified columns
        if search_term and search_columns:
            search_conditions = [
                getattr(self.model, col).ilike(f"%{search_term}%")
                for col in search_columns
                if hasattr(self.model, col)
            ]
            if search_conditions:
                combined = or_(*search_conditions)
                query = query.where(combined)
                count_query = count_query.where(combined)

        # Apply sorting
        if sort_by and hasattr(self.model, sort_by):
            order_func = desc if sort_dir == "desc" else asc
            query = query.order_by(order_func(getattr(self.model, sort_by)))

        # Get total count before pagination
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        items = list(result.unique().scalars().all())

        return items, total
