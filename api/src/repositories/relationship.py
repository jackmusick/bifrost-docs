"""
Relationship Repository

Provides database operations for Relationship model.
Handles bidirectional queries and normalized storage to prevent duplicates.
"""

from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.orm.relationship import Relationship
from src.repositories.base import BaseRepository


class RelationshipRepository(BaseRepository[Relationship]):
    """Repository for Relationship model operations."""

    model = Relationship

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    @staticmethod
    def normalize_relationship(
        source_type: str,
        source_id: UUID,
        target_type: str,
        target_id: UUID,
    ) -> tuple[str, UUID, str, UUID]:
        """
        Normalize relationship to prevent A->B and B->A duplicates.

        Always store with:
        - source_type < target_type alphabetically, OR
        - if same type, source_id < target_id

        Args:
            source_type: Source entity type
            source_id: Source entity UUID
            target_type: Target entity type
            target_id: Target entity UUID

        Returns:
            Normalized tuple of (source_type, source_id, target_type, target_id)
        """
        if source_type < target_type:
            return source_type, source_id, target_type, target_id
        elif source_type > target_type:
            return target_type, target_id, source_type, source_id
        else:
            # Same type - sort by ID
            if str(source_id) < str(target_id):
                return source_type, source_id, target_type, target_id
            else:
                return target_type, target_id, source_type, source_id

    async def get_for_entity(
        self,
        organization_id: UUID,
        entity_type: str,
        entity_id: UUID,
    ) -> list[Relationship]:
        """
        Get all relationships for an entity (bidirectional).

        Queries where the entity is either source or target.

        Args:
            organization_id: Organization UUID
            entity_type: Entity type
            entity_id: Entity UUID

        Returns:
            List of relationships involving this entity
        """
        result = await self.session.execute(
            select(Relationship)
            .where(
                Relationship.organization_id == organization_id,
                or_(
                    (Relationship.source_type == entity_type)
                    & (Relationship.source_id == entity_id),
                    (Relationship.target_type == entity_type)
                    & (Relationship.target_id == entity_id),
                ),
            )
            .order_by(Relationship.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id_and_org(
        self, id: UUID, organization_id: UUID
    ) -> Relationship | None:
        """
        Get a relationship by ID within an organization scope.

        Args:
            id: Relationship UUID
            organization_id: Organization UUID

        Returns:
            Relationship if found and belongs to organization, None otherwise
        """
        result = await self.session.execute(
            select(Relationship).where(
                Relationship.id == id,
                Relationship.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_relationship(
        self,
        organization_id: UUID,
        source_type: str,
        source_id: UUID,
        target_type: str,
        target_id: UUID,
    ) -> Relationship:
        """
        Create a relationship with normalization.

        Normalizes the relationship to prevent A->B and B->A duplicates.

        Args:
            organization_id: Organization UUID
            source_type: Source entity type
            source_id: Source entity UUID
            target_type: Target entity type
            target_id: Target entity UUID

        Returns:
            Created relationship
        """
        # Normalize to prevent duplicates
        norm_source_type, norm_source_id, norm_target_type, norm_target_id = (
            self.normalize_relationship(source_type, source_id, target_type, target_id)
        )

        relationship = Relationship(
            organization_id=organization_id,
            source_type=norm_source_type,
            source_id=norm_source_id,
            target_type=norm_target_type,
            target_id=norm_target_id,
        )
        return await self.create(relationship)

    async def find_existing(
        self,
        organization_id: UUID,
        source_type: str,
        source_id: UUID,
        target_type: str,
        target_id: UUID,
    ) -> Relationship | None:
        """
        Find an existing relationship between two entities.

        Handles normalization to find regardless of which is source/target.

        Args:
            organization_id: Organization UUID
            source_type: First entity type
            source_id: First entity UUID
            target_type: Second entity type
            target_id: Second entity UUID

        Returns:
            Relationship if exists, None otherwise
        """
        # Normalize to find the relationship
        norm_source_type, norm_source_id, norm_target_type, norm_target_id = (
            self.normalize_relationship(source_type, source_id, target_type, target_id)
        )

        result = await self.session.execute(
            select(Relationship).where(
                Relationship.organization_id == organization_id,
                Relationship.source_type == norm_source_type,
                Relationship.source_id == norm_source_id,
                Relationship.target_type == norm_target_type,
                Relationship.target_id == norm_target_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete_for_entity(
        self,
        organization_id: UUID,
        entity_type: str,
        entity_id: UUID,
    ) -> int:
        """
        Delete all relationships involving an entity.

        Used when deleting an entity to clean up its relationships.

        Args:
            organization_id: Organization UUID
            entity_type: Entity type
            entity_id: Entity UUID

        Returns:
            Number of deleted relationships
        """
        result = await self.session.execute(
            delete(Relationship)
            .where(
                Relationship.organization_id == organization_id,
                or_(
                    (Relationship.source_type == entity_type)
                    & (Relationship.source_id == entity_id),
                    (Relationship.target_type == entity_type)
                    & (Relationship.target_id == entity_id),
                ),
            )
            .returning(Relationship.id)
        )
        deleted_ids = result.scalars().all()
        await self.session.flush()
        return len(list(deleted_ids))
