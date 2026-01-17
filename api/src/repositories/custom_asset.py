"""
Custom Asset Repository.

Provides database operations for CustomAsset model, scoped to organizations.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.orm.custom_asset import CustomAsset
from src.repositories.base import BaseRepository


class CustomAssetRepository(BaseRepository[CustomAsset]):
    """Repository for CustomAsset model operations."""

    model = CustomAsset

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_paginated_by_type_and_org(
        self,
        custom_asset_type_id: UUID,
        organization_id: UUID,
        *,
        search: str | None = None,
        search_field_key: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        limit: int = 100,
        offset: int = 0,
        is_enabled: bool | None = None,
    ) -> tuple[list[CustomAsset], int]:
        """
        Get paginated custom assets for a type within an organization with search and sorting.

        Search is performed on the JSONB values field using the specified search_field_key.

        Args:
            custom_asset_type_id: CustomAssetType UUID
            organization_id: Organization UUID
            search: Optional search term
            search_field_key: Key within values JSONB to search (e.g., "name", "title")
            sort_by: Column to sort by (or JSONB key with "values." prefix)
            sort_dir: Sort direction ("asc" or "desc")
            limit: Maximum number of results
            offset: Number of results to skip
            is_enabled: Filter by is_enabled status (None = no filter)

        Returns:
            Tuple of (list of custom assets, total count)
        """
        query = select(CustomAsset).options(selectinload(CustomAsset.updated_by_user))
        count_query = select(func.count(CustomAsset.id))

        # Base filters
        base_filter = [
            CustomAsset.custom_asset_type_id == custom_asset_type_id,
            CustomAsset.organization_id == organization_id,
        ]

        if is_enabled is not None:
            base_filter.append(CustomAsset.is_enabled == is_enabled)

        for f in base_filter:
            query = query.where(f)
            count_query = count_query.where(f)

        # Search within JSONB values field
        if search and search_field_key:
            # Use JSONB ->> operator to extract text and perform case-insensitive search
            search_condition = CustomAsset.values[search_field_key].astext.ilike(f"%{search}%")
            query = query.where(search_condition)
            count_query = count_query.where(search_condition)

        # Sort by JSONB field if sort_by starts with "values."
        if sort_by:
            if sort_by.startswith("values."):
                jsonb_key = sort_by[7:]  # Remove "values." prefix
                if sort_dir == "desc":
                    query = query.order_by(CustomAsset.values[jsonb_key].astext.desc())
                else:
                    query = query.order_by(CustomAsset.values[jsonb_key].astext.asc())
            elif hasattr(CustomAsset, sort_by):
                from sqlalchemy import asc, desc
                order_func = desc if sort_dir == "desc" else asc
                query = query.order_by(order_func(getattr(CustomAsset, sort_by)))

        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_id_and_org(
        self, id: UUID, organization_id: UUID
    ) -> CustomAsset | None:
        """
        Get custom asset by ID within an organization.

        Args:
            id: CustomAsset UUID
            organization_id: Organization UUID

        Returns:
            CustomAsset or None if not found
        """
        result = await self.session.execute(
            select(CustomAsset)
            .options(selectinload(CustomAsset.updated_by_user))
            .where(
                CustomAsset.id == id,
                CustomAsset.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_type_and_org(
        self,
        id: UUID,
        custom_asset_type_id: UUID,
        organization_id: UUID,
    ) -> CustomAsset | None:
        """
        Get custom asset by ID, type, and organization.

        Args:
            id: CustomAsset UUID
            custom_asset_type_id: CustomAssetType UUID
            organization_id: Organization UUID

        Returns:
            CustomAsset or None if not found
        """
        result = await self.session.execute(
            select(CustomAsset)
            .options(selectinload(CustomAsset.updated_by_user))
            .where(
                CustomAsset.id == id,
                CustomAsset.custom_asset_type_id == custom_asset_type_id,
                CustomAsset.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_type_and_organization(
        self,
        custom_asset_type_id: UUID,
        organization_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CustomAsset]:
        """
        List all custom assets for a type within an organization.

        Args:
            custom_asset_type_id: CustomAssetType UUID
            organization_id: Organization UUID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of CustomAsset entities
        """
        result = await self.session.execute(
            select(CustomAsset)
            .where(
                CustomAsset.custom_asset_type_id == custom_asset_type_id,
                CustomAsset.organization_id == organization_id,
            )
            .order_by(CustomAsset.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_by_organization(
        self,
        organization_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CustomAsset]:
        """
        List all custom assets for an organization.

        Args:
            organization_id: Organization UUID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of CustomAsset entities
        """
        result = await self.session.execute(
            select(CustomAsset)
            .where(CustomAsset.organization_id == organization_id)
            .order_by(CustomAsset.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_by_type_and_organization(
        self,
        custom_asset_type_id: UUID,
        organization_id: UUID,
    ) -> int:
        """
        Count custom assets for a type within an organization.

        Args:
            custom_asset_type_id: CustomAssetType UUID
            organization_id: Organization UUID

        Returns:
            Count of custom assets
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(CustomAsset.id)).where(
                CustomAsset.custom_asset_type_id == custom_asset_type_id,
                CustomAsset.organization_id == organization_id,
            )
        )
        return result.scalar_one()

    async def search_by_field(
        self,
        organization_id: UUID,
        search_term: str,
        field_key: str,
        custom_asset_type_id: UUID | None = None,
        limit: int = 100,
    ) -> list[CustomAsset]:
        """
        Search custom assets by a specific field within an organization.

        Args:
            organization_id: Organization UUID
            search_term: Search term
            field_key: Key within values JSONB to search
            custom_asset_type_id: Optional type filter
            limit: Maximum number of results

        Returns:
            List of matching CustomAsset entities
        """
        query = select(CustomAsset).where(
            CustomAsset.organization_id == organization_id,
            CustomAsset.values[field_key].astext.ilike(f"%{search_term}%"),
        )

        if custom_asset_type_id:
            query = query.where(CustomAsset.custom_asset_type_id == custom_asset_type_id)

        query = query.order_by(CustomAsset.created_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())
