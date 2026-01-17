"""
Password Repository

Provides database operations for Password model.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.orm.password import Password
from src.repositories.base import BaseRepository


class PasswordRepository(BaseRepository[Password]):
    """Repository for Password model operations."""

    model = Password

    # Columns to search in for text search
    SEARCH_COLUMNS = ["name", "username", "url", "notes"]

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
    ) -> tuple[list[Password], int]:
        """
        Get paginated passwords for an organization with optional search and sorting.

        Args:
            organization_id: Organization UUID
            search: Optional search term for name, username, url, notes
            sort_by: Column to sort by
            sort_dir: Sort direction ("asc" or "desc")
            limit: Maximum number of results
            offset: Number of results to skip
            is_enabled: Filter by is_enabled status (None = no filter)

        Returns:
            Tuple of (list of passwords, total count)
        """
        filters = [Password.organization_id == organization_id]

        if is_enabled is not None and hasattr(Password, 'is_enabled'):
            filters.append(Password.is_enabled == is_enabled)

        return await self.get_paginated(
            filters=filters,
            search_columns=self.SEARCH_COLUMNS,
            search_term=search,
            sort_by=sort_by or "name",  # Default sort by name
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
            options=[selectinload(Password.updated_by_user)],
        )

    async def get_by_org(
        self, organization_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[Password]:
        """
        Get all passwords for an organization.

        Args:
            organization_id: Organization UUID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of passwords for the organization
        """
        result = await self.session.execute(
            select(Password)
            .where(Password.organization_id == organization_id)
            .order_by(Password.name)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_id_and_org(
        self, id: UUID, organization_id: UUID
    ) -> Password | None:
        """
        Get a password by ID within an organization scope.

        Args:
            id: Password UUID
            organization_id: Organization UUID

        Returns:
            Password if found and belongs to organization, None otherwise
        """
        result = await self.session.execute(
            select(Password)
            .options(selectinload(Password.updated_by_user))
            .where(
                Password.id == id,
                Password.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_by_organization(self, organization_id: UUID) -> int:
        """
        Count passwords for an organization.

        Args:
            organization_id: Organization UUID

        Returns:
            Count of passwords
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(Password.id)).where(
                Password.organization_id == organization_id
            )
        )
        return result.scalar_one()
