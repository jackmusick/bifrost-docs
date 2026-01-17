"""
Configuration Type Repository

Provides database operations for ConfigurationType model.
These are global types, not scoped to organizations.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.orm.configuration import Configuration
from src.models.orm.configuration_type import ConfigurationType
from src.repositories.base import BaseRepository


class ConfigurationTypeRepository(BaseRepository[ConfigurationType]):
    """Repository for ConfigurationType model operations."""

    model = ConfigurationType

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_name(self, name: str) -> ConfigurationType | None:
        """
        Get configuration type by name.

        Args:
            name: Configuration type name

        Returns:
            ConfigurationType or None if not found
        """
        result = await self.session.execute(
            select(ConfigurationType).where(ConfigurationType.name == name)
        )
        return result.scalar_one_or_none()

    async def get_all_ordered(
        self,
        limit: int = 100,
        offset: int = 0,
        include_inactive: bool = False,
    ) -> list[ConfigurationType]:
        """
        Get all configuration types ordered by name.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            include_inactive: If True, include inactive types

        Returns:
            List of configuration types
        """
        query = select(ConfigurationType)
        if not include_inactive:
            query = query.where(ConfigurationType.is_active == True)  # noqa: E712
        query = query.order_by(ConfigurationType.name).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all_active(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ConfigurationType]:
        """
        List only active configuration types ordered by name.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of active ConfigurationType entities
        """
        return await self.get_all_ordered(limit=limit, offset=offset, include_inactive=False)

    async def get_all_with_inactive(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ConfigurationType]:
        """
        List all configuration types including inactive ones.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of all ConfigurationType entities
        """
        return await self.get_all_ordered(limit=limit, offset=offset, include_inactive=True)

    async def get_configuration_count(self, type_id: UUID) -> int:
        """
        Get count of configurations using this type.

        Args:
            type_id: ConfigurationType UUID

        Returns:
            Count of configurations using this type
        """
        result = await self.session.execute(
            select(func.count(Configuration.id)).where(
                Configuration.configuration_type_id == type_id
            )
        )
        return result.scalar_one()

    async def can_delete(self, type_id: UUID) -> bool:
        """
        Check if type can be hard deleted (no configurations exist).

        Args:
            type_id: ConfigurationType UUID

        Returns:
            True if can be deleted, False if configurations exist
        """
        count = await self.get_configuration_count(type_id)
        return count == 0

    async def deactivate(self, type_id: UUID) -> ConfigurationType:
        """
        Soft delete (deactivate) a configuration type.

        Args:
            type_id: ConfigurationType UUID

        Returns:
            Updated ConfigurationType

        Raises:
            ValueError: If type not found
        """
        entity = await self.get_by_id(type_id)
        if not entity:
            raise ValueError(f"ConfigurationType {type_id} not found")
        entity.is_active = False
        await self.session.flush()
        return entity

    async def activate(self, type_id: UUID) -> ConfigurationType:
        """
        Reactivate a deactivated configuration type.

        Args:
            type_id: ConfigurationType UUID

        Returns:
            Updated ConfigurationType

        Raises:
            ValueError: If type not found
        """
        entity = await self.get_by_id(type_id)
        if not entity:
            raise ValueError(f"ConfigurationType {type_id} not found")
        entity.is_active = True
        await self.session.flush()
        return entity

    async def delete_by_id(self, id: UUID) -> bool:
        """
        Delete configuration type by ID.

        Args:
            id: Configuration type UUID

        Returns:
            True if deleted, False if not found
        """
        entity = await self.get_by_id(id)
        if entity:
            await self.delete(entity)
            return True
        return False
