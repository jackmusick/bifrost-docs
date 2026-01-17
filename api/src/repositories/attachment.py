"""
Attachment Repository

Provides database operations for Attachment model.
Organization-scoped for multi-tenancy.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.enums import EntityType
from src.models.orm.attachment import Attachment
from src.repositories.base import BaseRepository


class AttachmentRepository(BaseRepository[Attachment]):
    """Repository for Attachment model operations."""

    model = Attachment

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id_and_org(
        self, id: UUID, organization_id: UUID
    ) -> Attachment | None:
        """
        Get attachment by ID, scoped to organization.

        Args:
            id: Attachment UUID
            organization_id: Organization UUID for scoping

        Returns:
            Attachment or None if not found
        """
        result = await self.session.execute(
            select(Attachment).where(
                Attachment.id == id,
                Attachment.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_entity(
        self,
        organization_id: UUID,
        entity_type: EntityType,
        entity_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Attachment]:
        """
        Get all attachments for a specific entity.

        Args:
            organization_id: Organization UUID for scoping
            entity_type: Type of entity (password, document, etc.)
            entity_id: Entity UUID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of attachments
        """
        result = await self.session.execute(
            select(Attachment)
            .where(
                Attachment.organization_id == organization_id,
                Attachment.entity_type == entity_type,
                Attachment.entity_id == entity_id,
            )
            .order_by(Attachment.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_by_entity(
        self,
        organization_id: UUID,
        entity_type: EntityType,
        entity_id: UUID,
    ) -> int:
        """
        Count attachments for a specific entity.

        Args:
            organization_id: Organization UUID for scoping
            entity_type: Type of entity
            entity_id: Entity UUID

        Returns:
            Number of attachments
        """
        result = await self.session.execute(
            select(func.count(Attachment.id)).where(
                Attachment.organization_id == organization_id,
                Attachment.entity_type == entity_type,
                Attachment.entity_id == entity_id,
            )
        )
        return result.scalar() or 0

    async def get_all_for_org(
        self,
        organization_id: UUID,
        entity_type: EntityType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Attachment]:
        """
        Get all attachments for an organization.

        Args:
            organization_id: Organization UUID
            entity_type: Optional filter by entity type
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of attachments
        """
        query = select(Attachment).where(Attachment.organization_id == organization_id)

        if entity_type is not None:
            query = query.where(Attachment.entity_type == entity_type)

        query = query.order_by(Attachment.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_s3_key(self, s3_key: str) -> Attachment | None:
        """
        Get attachment by S3 key.

        Args:
            s3_key: S3 storage key

        Returns:
            Attachment or None if not found
        """
        result = await self.session.execute(
            select(Attachment).where(Attachment.s3_key == s3_key)
        )
        return result.scalar_one_or_none()

    async def delete_by_entity(
        self,
        organization_id: UUID,
        entity_type: EntityType,
        entity_id: UUID,
    ) -> list[str]:
        """
        Delete all attachments for an entity and return their S3 keys.

        Used when deleting an entity to clean up associated files.

        Args:
            organization_id: Organization UUID
            entity_type: Type of entity
            entity_id: Entity UUID

        Returns:
            List of S3 keys that were deleted (for S3 cleanup)
        """
        # Get all attachments first to collect S3 keys
        attachments = await self.get_by_entity(
            organization_id, entity_type, entity_id, limit=10000
        )

        s3_keys = [att.s3_key for att in attachments]

        # Delete from database
        for attachment in attachments:
            await self.session.delete(attachment)

        await self.session.flush()

        return s3_keys

    async def calculate_storage_for_org(self, organization_id: UUID) -> int:
        """
        Calculate total storage used by an organization.

        Args:
            organization_id: Organization UUID

        Returns:
            Total bytes used
        """
        result = await self.session.execute(
            select(func.sum(Attachment.size_bytes)).where(
                Attachment.organization_id == organization_id
            )
        )
        return result.scalar() or 0
