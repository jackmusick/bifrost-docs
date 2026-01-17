"""
Configuration Status Repository

Provides database operations for ConfigurationStatus model.
These are global statuses, not scoped to organizations.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.orm.configuration import Configuration
from src.models.orm.configuration_status import ConfigurationStatus
from src.repositories.base import BaseRepository


class ConfigurationStatusRepository(BaseRepository[ConfigurationStatus]):
    """Repository for ConfigurationStatus model operations."""

    model = ConfigurationStatus

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_name(self, name: str) -> ConfigurationStatus | None:
        """
        Get configuration status by name.

        Args:
            name: Configuration status name

        Returns:
            ConfigurationStatus or None if not found
        """
        result = await self.session.execute(
            select(ConfigurationStatus).where(ConfigurationStatus.name == name)
        )
        return result.scalar_one_or_none()

    async def get_all_ordered(
        self,
        limit: int = 100,
        offset: int = 0,
        include_inactive: bool = False,
    ) -> list[ConfigurationStatus]:
        """
        Get all configuration statuses ordered by name.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            include_inactive: If True, include inactive statuses

        Returns:
            List of configuration statuses
        """
        query = select(ConfigurationStatus)
        if not include_inactive:
            query = query.where(ConfigurationStatus.is_active == True)  # noqa: E712
        query = query.order_by(ConfigurationStatus.name).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all_active(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ConfigurationStatus]:
        """
        List only active configuration statuses ordered by name.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of active ConfigurationStatus entities
        """
        return await self.get_all_ordered(limit=limit, offset=offset, include_inactive=False)

    async def get_all_with_inactive(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ConfigurationStatus]:
        """
        List all configuration statuses including inactive ones.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of all ConfigurationStatus entities
        """
        return await self.get_all_ordered(limit=limit, offset=offset, include_inactive=True)

    async def get_configuration_count(self, status_id: UUID) -> int:
        """
        Get count of configurations using this status.

        Args:
            status_id: ConfigurationStatus UUID

        Returns:
            Count of configurations using this status
        """
        result = await self.session.execute(
            select(func.count(Configuration.id)).where(
                Configuration.configuration_status_id == status_id
            )
        )
        return result.scalar_one()

    async def can_delete(self, status_id: UUID) -> bool:
        """
        Check if status can be hard deleted (no configurations exist).

        Args:
            status_id: ConfigurationStatus UUID

        Returns:
            True if can be deleted, False if configurations exist
        """
        count = await self.get_configuration_count(status_id)
        return count == 0

    async def deactivate(self, status_id: UUID) -> ConfigurationStatus:
        """
        Soft delete (deactivate) a configuration status.

        Args:
            status_id: ConfigurationStatus UUID

        Returns:
            Updated ConfigurationStatus

        Raises:
            ValueError: If status not found
        """
        entity = await self.get_by_id(status_id)
        if not entity:
            raise ValueError(f"ConfigurationStatus {status_id} not found")
        entity.is_active = False
        await self.session.flush()
        return entity

    async def activate(self, status_id: UUID) -> ConfigurationStatus:
        """
        Reactivate a deactivated configuration status.

        Args:
            status_id: ConfigurationStatus UUID

        Returns:
            Updated ConfigurationStatus

        Raises:
            ValueError: If status not found
        """
        entity = await self.get_by_id(status_id)
        if not entity:
            raise ValueError(f"ConfigurationStatus {status_id} not found")
        entity.is_active = True
        await self.session.flush()
        return entity

    async def delete_by_id(self, id: UUID) -> bool:
        """
        Delete configuration status by ID.

        Args:
            id: Configuration status UUID

        Returns:
            True if deleted, False if not found
        """
        entity = await self.get_by_id(id)
        if entity:
            await self.delete(entity)
            return True
        return False
