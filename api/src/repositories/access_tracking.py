"""
Access Tracking Repository.

Provides queries for recently and frequently accessed entities from the audit log.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.contracts.access_tracking import FrequentItem, RecentItem
from src.models.orm.audit_log import AuditLog
from src.models.orm.configuration import Configuration
from src.models.orm.custom_asset import CustomAsset
from src.models.orm.custom_asset_type import CustomAssetType
from src.models.orm.document import Document
from src.models.orm.location import Location
from src.models.orm.organization import Organization
from src.models.orm.password import Password

# Mapping of entity types to their ORM models and name fields
ENTITY_TYPE_CONFIG: dict[str, tuple[type, str]] = {
    "password": (Password, "name"),
    "configuration": (Configuration, "name"),
    "location": (Location, "name"),
    "document": (Document, "name"),
    "custom_asset": (CustomAsset, "values"),  # Special handling for custom assets
    "organization": (Organization, "name"),
}


class AccessTrackingRepository:
    """Repository for querying access tracking data from audit logs."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def get_recent_for_user(
        self, user_id: UUID, limit: int = 10
    ) -> list[RecentItem]:
        """
        Get recently viewed entities for a user.

        Queries the audit log for 'view' actions by this user, deduplicates
        to the most recent view per entity, and joins to entity tables to
        get current names (filtering out deleted entities).

        Args:
            user_id: The user's UUID
            limit: Maximum number of recent items to return

        Returns:
            List of RecentItem objects sorted by viewed_at descending
        """
        # Step 1: Get recent views from audit log, grouped by entity
        # Use a subquery to get the latest view per (entity_type, entity_id)
        latest_views_subq = (
            select(
                AuditLog.entity_type,
                AuditLog.entity_id,
                AuditLog.organization_id,
                func.max(AuditLog.created_at).label("viewed_at"),
            )
            .where(
                AuditLog.actor_user_id == user_id,
                AuditLog.action == "view",
            )
            .group_by(
                AuditLog.entity_type,
                AuditLog.entity_id,
                AuditLog.organization_id,
            )
            .order_by(func.max(AuditLog.created_at).desc())
            .limit(limit * 3)  # Fetch more to account for deleted entities
            .subquery()
        )

        # Execute to get the audit log entries
        result = await self.session.execute(
            select(
                latest_views_subq.c.entity_type,
                latest_views_subq.c.entity_id,
                latest_views_subq.c.organization_id,
                latest_views_subq.c.viewed_at,
            ).order_by(latest_views_subq.c.viewed_at.desc())
        )
        recent_views = result.all()

        # Step 2: For each entity, look up its current name
        recent_items: list[RecentItem] = []

        for row in recent_views:
            if len(recent_items) >= limit:
                break

            entity_type = row.entity_type
            entity_id = row.entity_id
            organization_id = row.organization_id
            viewed_at = row.viewed_at

            # Get entity name based on type
            name = await self._get_entity_name(entity_type, entity_id)
            if name is None:
                # Entity was deleted, skip it
                continue

            # Get organization name if we have an org_id
            org_name: str | None = None
            if organization_id:
                org_result = await self.session.execute(
                    select(Organization.name).where(Organization.id == organization_id)
                )
                org_name = org_result.scalar_one_or_none()

            recent_items.append(
                RecentItem(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    organization_id=organization_id,
                    org_name=org_name,
                    name=name,
                    viewed_at=viewed_at,
                )
            )

        return recent_items

    async def get_frequently_accessed(
        self, org_id: UUID, limit: int = 6, days: int = 30
    ) -> list[FrequentItem]:
        """
        Get frequently accessed entities within an organization.

        Queries the audit log for 'view' actions within the specified time window,
        groups by entity, and counts views.

        Args:
            org_id: The organization UUID
            limit: Maximum number of frequent items to return
            days: Number of days to look back

        Returns:
            List of FrequentItem objects sorted by view_count descending
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)

        # Query audit log for views in this org within the time window
        # Group by (entity_type, entity_id) and count
        freq_query = (
            select(
                AuditLog.entity_type,
                AuditLog.entity_id,
                func.count().label("view_count"),
            )
            .where(
                AuditLog.organization_id == org_id,
                AuditLog.action == "view",
                AuditLog.created_at >= cutoff,
            )
            .group_by(AuditLog.entity_type, AuditLog.entity_id)
            .order_by(func.count().desc())
            .limit(limit * 2)  # Fetch more to account for deleted entities
        )

        result = await self.session.execute(freq_query)
        frequent_views = result.all()

        # Look up names for each entity
        frequent_items: list[FrequentItem] = []

        for row in frequent_views:
            if len(frequent_items) >= limit:
                break

            entity_type = row.entity_type
            entity_id = row.entity_id
            view_count = row.view_count

            # Get entity name
            name = await self._get_entity_name(entity_type, entity_id)
            if name is None:
                # Entity was deleted, skip it
                continue

            frequent_items.append(
                FrequentItem(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    name=name,
                    view_count=view_count,
                )
            )

        return frequent_items

    async def _get_entity_name(
        self, entity_type: str, entity_id: UUID
    ) -> str | None:
        """
        Get the display name for an entity.

        Returns None if the entity no longer exists.
        """
        if entity_type not in ENTITY_TYPE_CONFIG:
            # Unknown entity type, return the type and ID as name
            return f"{entity_type}:{entity_id}"

        model, name_field = ENTITY_TYPE_CONFIG[entity_type]

        # Special handling for custom_asset - need to get display value
        if entity_type == "custom_asset":
            return await self._get_custom_asset_name(entity_id)

        # Standard handling - just select the name field
        query = select(getattr(model, name_field)).where(model.id == entity_id)  # type: ignore[attr-defined]
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _get_custom_asset_name(self, entity_id: UUID) -> str | None:
        """
        Get the display name for a custom asset.

        Custom assets store values in a JSONB column. The display field
        is determined by the custom_asset_type's display_field_key.
        """
        # Join custom_asset with custom_asset_type to get the display field
        query = (
            select(CustomAsset.values, CustomAssetType.display_field_key, CustomAssetType.name)
            .join(CustomAssetType, CustomAsset.custom_asset_type_id == CustomAssetType.id)
            .where(CustomAsset.id == entity_id)
        )
        result = await self.session.execute(query)
        row = result.one_or_none()

        if row is None:
            return None

        values, display_field_key, type_name = row

        # If there's a display field and it has a value, use it
        if display_field_key and values and display_field_key in values:
            display_value = values[display_field_key]
            if display_value:
                return str(display_value)

        # Fallback to type name with ID suffix
        return f"{type_name} ({str(entity_id)[:8]})"
