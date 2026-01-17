"""
Custom Asset Type Repository.

Provides database operations for CustomAssetType model.
These are global types, not scoped to organizations.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.orm.custom_asset import CustomAsset
from src.models.orm.custom_asset_type import CustomAssetType
from src.repositories.base import BaseRepository


class CustomAssetTypeRepository(BaseRepository[CustomAssetType]):
    """Repository for CustomAssetType model operations."""

    model = CustomAssetType

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_name(self, name: str) -> CustomAssetType | None:
        """
        Get custom asset type by name.

        Args:
            name: CustomAssetType name

        Returns:
            CustomAssetType or None if not found
        """
        result = await self.session.execute(
            select(CustomAssetType).where(CustomAssetType.name == name)
        )
        return result.scalar_one_or_none()

    async def get_all_ordered(
        self,
        limit: int = 100,
        offset: int = 0,
        include_inactive: bool = False,
    ) -> list[CustomAssetType]:
        """
        List all custom asset types ordered by sort_order, then name.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            include_inactive: If True, include inactive types

        Returns:
            List of CustomAssetType entities
        """
        query = select(CustomAssetType)
        if not include_inactive:
            query = query.where(CustomAssetType.is_active == True)  # noqa: E712
        query = query.order_by(CustomAssetType.sort_order, CustomAssetType.name).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all_active(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CustomAssetType]:
        """
        List only active custom asset types ordered by name.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of active CustomAssetType entities
        """
        return await self.get_all_ordered(limit=limit, offset=offset, include_inactive=False)

    async def get_all_with_inactive(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CustomAssetType]:
        """
        List all custom asset types including inactive ones.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of all CustomAssetType entities
        """
        return await self.get_all_ordered(limit=limit, offset=offset, include_inactive=True)

    async def count_all(self) -> int:
        """
        Count all custom asset types.

        Returns:
            Count of custom asset types
        """
        result = await self.session.execute(select(func.count(CustomAssetType.id)))
        return result.scalar_one()

    async def get_asset_count(self, type_id: UUID) -> int:
        """
        Get count of custom assets using this type.

        Args:
            type_id: CustomAssetType UUID

        Returns:
            Count of assets using this type
        """
        result = await self.session.execute(
            select(func.count(CustomAsset.id)).where(
                CustomAsset.custom_asset_type_id == type_id
            )
        )
        return result.scalar_one()

    async def can_delete(self, type_id: UUID) -> bool:
        """
        Check if type can be hard deleted (no assets exist).

        Args:
            type_id: CustomAssetType UUID

        Returns:
            True if can be deleted, False if assets exist
        """
        count = await self.get_asset_count(type_id)
        return count == 0

    async def deactivate(self, type_id: UUID) -> CustomAssetType:
        """
        Soft delete (deactivate) a custom asset type.

        Args:
            type_id: CustomAssetType UUID

        Returns:
            Updated CustomAssetType

        Raises:
            ValueError: If type not found
        """
        entity = await self.get_by_id(type_id)
        if not entity:
            raise ValueError(f"CustomAssetType {type_id} not found")
        entity.is_active = False
        await self.session.flush()
        return entity

    async def activate(self, type_id: UUID) -> CustomAssetType:
        """
        Reactivate a deactivated custom asset type.

        Args:
            type_id: CustomAssetType UUID

        Returns:
            Updated CustomAssetType

        Raises:
            ValueError: If type not found
        """
        entity = await self.get_by_id(type_id)
        if not entity:
            raise ValueError(f"CustomAssetType {type_id} not found")
        entity.is_active = True
        await self.session.flush()
        return entity

    async def delete_by_id(self, id: UUID) -> bool:
        """
        Delete custom asset type by ID.

        Args:
            id: CustomAssetType UUID

        Returns:
            True if deleted, False if not found
        """
        entity = await self.get_by_id(id)
        if entity:
            await self.delete(entity)
            return True
        return False
