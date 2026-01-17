"""
Entity Resolver Service

Resolves entity IDs to entity names for display purposes.
Used by the relationships system to show related entity names.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.orm.configuration import Configuration
from src.models.orm.custom_asset import CustomAsset
from src.models.orm.document import Document
from src.models.orm.location import Location
from src.models.orm.password import Password

# Valid entity types for relationships
VALID_ENTITY_TYPES = frozenset(
    {"password", "configuration", "location", "document", "custom_asset"}
)


class EntityResolver:
    """Service for resolving entity IDs to names."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_entity_name(
        self,
        organization_id: UUID,
        entity_type: str,
        entity_id: UUID,
    ) -> str | None:
        """
        Get the name of an entity.

        Args:
            organization_id: Organization UUID
            entity_type: Type of entity (password, configuration, location, document, custom_asset)
            entity_id: Entity UUID

        Returns:
            Entity name if found, None otherwise
        """
        if entity_type == "password":
            return await self._get_password_name(organization_id, entity_id)
        elif entity_type == "configuration":
            return await self._get_configuration_name(organization_id, entity_id)
        elif entity_type == "location":
            return await self._get_location_name(organization_id, entity_id)
        elif entity_type == "document":
            return await self._get_document_name(organization_id, entity_id)
        elif entity_type == "custom_asset":
            return await self._get_custom_asset_name(organization_id, entity_id)
        else:
            return None

    async def _get_password_name(
        self, organization_id: UUID, entity_id: UUID
    ) -> str | None:
        """Get password name by ID."""
        result = await self.session.execute(
            select(Password.name).where(
                Password.id == entity_id,
                Password.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_configuration_name(
        self, organization_id: UUID, entity_id: UUID
    ) -> str | None:
        """Get configuration name by ID."""
        result = await self.session.execute(
            select(Configuration.name).where(
                Configuration.id == entity_id,
                Configuration.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_location_name(
        self, organization_id: UUID, entity_id: UUID
    ) -> str | None:
        """Get location name by ID."""
        result = await self.session.execute(
            select(Location.name).where(
                Location.id == entity_id,
                Location.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_document_name(
        self, organization_id: UUID, entity_id: UUID
    ) -> str | None:
        """Get document name by ID."""
        result = await self.session.execute(
            select(Document.name).where(
                Document.id == entity_id,
                Document.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_custom_asset_name(
        self, organization_id: UUID, entity_id: UUID
    ) -> str | None:
        """Get custom asset name by ID (from values JSONB field)."""
        result = await self.session.execute(
            select(CustomAsset.values).where(
                CustomAsset.id == entity_id,
                CustomAsset.organization_id == organization_id,
            )
        )
        values = result.scalar_one_or_none()
        if values:
            # Try common name fields
            return values.get("name") or values.get("title") or values.get("domain")
        return None

    async def resolve_entities(
        self,
        organization_id: UUID,
        entities: list[tuple[str, UUID]],
    ) -> list[tuple[str, UUID, str | None]]:
        """
        Resolve multiple entities to names.

        Args:
            organization_id: Organization UUID
            entities: List of (entity_type, entity_id) tuples

        Returns:
            List of (entity_type, entity_id, name) tuples
        """
        results = []
        for entity_type, entity_id in entities:
            name = await self.get_entity_name(organization_id, entity_type, entity_id)
            results.append((entity_type, entity_id, name))
        return results
