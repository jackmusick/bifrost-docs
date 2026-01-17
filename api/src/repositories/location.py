"""
Location Repository

Provides database operations for Location model.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.orm.location import Location
from src.repositories.base import BaseRepository


class LocationRepository(BaseRepository[Location]):
    """Repository for Location model operations."""

    model = Location

    # Columns to search in for text search
    SEARCH_COLUMNS = ["name", "notes"]

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_paginated_by_org(
        self,
        organization_id: UUID,
        *,
        search: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        limit: int = 100,
        offset: int = 0,
        is_enabled: bool | None = None,
    ) -> tuple[list[Location], int]:
        """
        Get paginated locations for an organization with optional search and sorting.

        Args:
            organization_id: Organization UUID
            search: Optional search term for name, notes
            sort_by: Column to sort by
            sort_dir: Sort direction ("asc" or "desc")
            limit: Maximum number of results
            offset: Number of results to skip
            is_enabled: Filter by is_enabled status (None = no filter)

        Returns:
            Tuple of (list of locations, total count)
        """
        filters = [Location.organization_id == organization_id]

        if is_enabled is not None and hasattr(Location, 'is_enabled'):
            filters.append(Location.is_enabled == is_enabled)

        return await self.get_paginated(
            filters=filters,
            search_columns=self.SEARCH_COLUMNS,
            search_term=search,
            sort_by=sort_by or "name",  # Default sort by name
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
            options=[selectinload(Location.updated_by_user)],
        )

    async def get_by_organization(
        self, organization_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[Location]:
        """
        Get all locations for an organization.

        Args:
            organization_id: Organization UUID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of locations
        """
        result = await self.session.execute(
            select(Location)
            .where(Location.organization_id == organization_id)
            .order_by(Location.name)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_id_and_organization(
        self, location_id: UUID, organization_id: UUID
    ) -> Location | None:
        """
        Get a location by ID within an organization.

        Args:
            location_id: Location UUID
            organization_id: Organization UUID

        Returns:
            Location or None if not found
        """
        result = await self.session.execute(
            select(Location)
            .options(selectinload(Location.updated_by_user))
            .where(
                Location.id == location_id,
                Location.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_name_and_organization(
        self, name: str, organization_id: UUID
    ) -> Location | None:
        """
        Get a location by name within an organization.

        Args:
            name: Location name
            organization_id: Organization UUID

        Returns:
            Location or None if not found
        """
        result = await self.session.execute(
            select(Location).where(
                Location.name == name,
                Location.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_by_organization(self, organization_id: UUID) -> int:
        """
        Count locations for an organization.

        Args:
            organization_id: Organization UUID

        Returns:
            Count of locations
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(Location.id)).where(
                Location.organization_id == organization_id
            )
        )
        return result.scalar_one()
