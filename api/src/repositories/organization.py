"""
Organization Repository

Provides database operations for Organization model.
"""


from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.orm.organization import Organization
from src.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    """Repository for Organization model operations."""

    model = Organization

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, id: UUID) -> Organization | None:
        """
        Get organization by ID with eager loading of relationships.

        Args:
            id: Organization UUID

        Returns:
            Organization or None if not found
        """
        result = await self.session.execute(
            select(Organization)
            .options(selectinload(Organization.updated_by_user))
            .where(Organization.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0, is_enabled: bool | None = None) -> list[Organization]:
        """
        Get all organizations with eager loading of relationships.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            is_enabled: Filter by is_enabled status (None = no filter)

        Returns:
            List of organizations
        """
        query = select(Organization).options(selectinload(Organization.updated_by_user))

        if is_enabled is not None and hasattr(Organization, 'is_enabled'):
            query = query.where(Organization.is_enabled == is_enabled)

        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> Organization | None:
        """
        Get organization by name.

        Args:
            name: Organization name

        Returns:
            Organization or None if not found
        """
        result = await self.session.execute(
            select(Organization)
            .options(selectinload(Organization.updated_by_user))
            .where(Organization.name == name)
        )
        return result.scalar_one_or_none()
