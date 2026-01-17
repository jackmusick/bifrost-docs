"""
Configuration Repository

Provides database operations for Configuration model.
All operations are scoped to an organization.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.models.orm.configuration import Configuration
from src.repositories.base import BaseRepository


class ConfigurationRepository(BaseRepository[Configuration]):
    """Repository for Configuration model operations."""

    model = Configuration

    # Columns to search in for text search
    SEARCH_COLUMNS = [
        "name",
        "serial_number",
        "asset_tag",
        "manufacturer",
        "model",
        "ip_address",
        "notes",
    ]

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_paginated_by_org(
        self,
        organization_id: UUID,
        *,
        configuration_type_id: UUID | None = None,
        configuration_status_id: UUID | None = None,
        search: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        limit: int = 100,
        offset: int = 0,
        is_enabled: bool | None = None,
    ) -> tuple[list[Configuration], int]:
        """
        Get paginated configurations for an organization with filtering, search and sorting.

        Args:
            organization_id: Organization UUID
            configuration_type_id: Optional filter by type
            configuration_status_id: Optional filter by status
            search: Optional search term
            sort_by: Column to sort by
            sort_dir: Sort direction ("asc" or "desc")
            limit: Maximum number of results
            offset: Number of results to skip
            is_enabled: Filter by is_enabled status (None = no filter)

        Returns:
            Tuple of (list of configurations, total count)
        """
        filters = [Configuration.organization_id == organization_id]

        if configuration_type_id is not None:
            filters.append(Configuration.configuration_type_id == configuration_type_id)

        if configuration_status_id is not None:
            filters.append(Configuration.configuration_status_id == configuration_status_id)

        if is_enabled is not None and hasattr(Configuration, 'is_enabled'):
            filters.append(Configuration.is_enabled == is_enabled)

        return await self.get_paginated(
            filters=filters,
            search_columns=self.SEARCH_COLUMNS,
            search_term=search,
            sort_by=sort_by or "name",  # Default sort by name
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
            options=[
                joinedload(Configuration.configuration_type),
                joinedload(Configuration.configuration_status),
                selectinload(Configuration.updated_by_user),
            ],
        )

    async def get_by_id_for_org(
        self, id: UUID, organization_id: UUID
    ) -> Configuration | None:
        """
        Get configuration by ID within an organization.

        Args:
            id: Configuration UUID
            organization_id: Organization UUID

        Returns:
            Configuration or None if not found
        """
        result = await self.session.execute(
            select(Configuration)
            .options(
                joinedload(Configuration.configuration_type),
                joinedload(Configuration.configuration_status),
                selectinload(Configuration.updated_by_user),
            )
            .where(
                Configuration.id == id,
                Configuration.organization_id == organization_id,
            )
        )
        return result.unique().scalar_one_or_none()

    async def get_all_for_org(
        self,
        organization_id: UUID,
        limit: int = 100,
        offset: int = 0,
        configuration_type_id: UUID | None = None,
        configuration_status_id: UUID | None = None,
    ) -> list[Configuration]:
        """
        Get all configurations for an organization with optional filtering.

        Args:
            organization_id: Organization UUID
            limit: Maximum number of results
            offset: Number of results to skip
            configuration_type_id: Optional filter by type
            configuration_status_id: Optional filter by status

        Returns:
            List of configurations
        """
        query = (
            select(Configuration)
            .options(
                joinedload(Configuration.configuration_type),
                joinedload(Configuration.configuration_status),
                selectinload(Configuration.updated_by_user),
            )
            .where(Configuration.organization_id == organization_id)
        )

        if configuration_type_id is not None:
            query = query.where(Configuration.configuration_type_id == configuration_type_id)

        if configuration_status_id is not None:
            query = query.where(Configuration.configuration_status_id == configuration_status_id)

        query = query.order_by(Configuration.name).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.unique().scalars().all())

    async def get_by_name_for_org(
        self, name: str, organization_id: UUID
    ) -> Configuration | None:
        """
        Get configuration by name within an organization.

        Args:
            name: Configuration name
            organization_id: Organization UUID

        Returns:
            Configuration or None if not found
        """
        result = await self.session.execute(
            select(Configuration)
            .options(
                joinedload(Configuration.configuration_type),
                joinedload(Configuration.configuration_status),
                selectinload(Configuration.updated_by_user),
            )
            .where(
                Configuration.name == name,
                Configuration.organization_id == organization_id,
            )
        )
        return result.unique().scalar_one_or_none()

    async def delete_for_org(self, id: UUID, organization_id: UUID) -> bool:
        """
        Delete configuration by ID within an organization.

        Args:
            id: Configuration UUID
            organization_id: Organization UUID

        Returns:
            True if deleted, False if not found
        """
        entity = await self.get_by_id_for_org(id, organization_id)
        if entity:
            await self.delete(entity)
            return True
        return False

    async def count_by_type_and_organization(
        self,
        configuration_type_id: UUID,
        organization_id: UUID,
    ) -> int:
        """
        Count configurations for a type within an organization.

        Args:
            configuration_type_id: ConfigurationType UUID
            organization_id: Organization UUID

        Returns:
            Count of configurations
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(Configuration.id)).where(
                Configuration.configuration_type_id == configuration_type_id,
                Configuration.organization_id == organization_id,
            )
        )
        return result.scalar_one()
