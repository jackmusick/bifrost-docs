"""
User Preferences Repository

Provides database operations for UserPreferences model.
Supports upsert operations for storing user-specific UI preferences.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.orm.user_preferences import UserPreferences
from src.repositories.base import BaseRepository


class UserPreferencesRepository(BaseRepository[UserPreferences]):
    """Repository for UserPreferences model operations."""

    model = UserPreferences

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_user_and_entity(
        self,
        user_id: UUID,
        entity_type: str,
    ) -> UserPreferences | None:
        """
        Get preferences for a specific user and entity type.

        Args:
            user_id: User UUID
            entity_type: Entity type identifier (e.g., "passwords", "configurations")

        Returns:
            UserPreferences if found, None otherwise
        """
        result = await self.session.execute(
            select(UserPreferences).where(
                UserPreferences.user_id == user_id,
                UserPreferences.entity_type == entity_type,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: UUID,
        entity_type: str,
        preferences: dict[str, Any],
    ) -> UserPreferences:
        """
        Insert or update preferences for a user and entity type.

        Uses PostgreSQL's ON CONFLICT DO UPDATE for atomic upsert.

        Args:
            user_id: User UUID
            entity_type: Entity type identifier
            preferences: Preferences data to store

        Returns:
            Created or updated UserPreferences
        """
        stmt = insert(UserPreferences).values(
            user_id=user_id,
            entity_type=entity_type,
            preferences=preferences,
        )

        # On conflict, update preferences and updated_at
        stmt = stmt.on_conflict_do_update(
            constraint="uq_user_preferences_user_entity",
            set_={
                "preferences": preferences,
                "updated_at": stmt.excluded.updated_at,
            },
        )

        stmt = stmt.returning(UserPreferences)

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def delete_by_user_and_entity(
        self,
        user_id: UUID,
        entity_type: str,
    ) -> bool:
        """
        Delete preferences for a specific user and entity type.

        Args:
            user_id: User UUID
            entity_type: Entity type identifier

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(
            delete(UserPreferences).where(
                UserPreferences.user_id == user_id,
                UserPreferences.entity_type == entity_type,
            )
        )
        return result.rowcount > 0

    async def get_all_for_user(
        self,
        user_id: UUID,
    ) -> list[UserPreferences]:
        """
        Get all preferences for a user.

        Args:
            user_id: User UUID

        Returns:
            List of all UserPreferences for the user
        """
        result = await self.session.execute(
            select(UserPreferences).where(UserPreferences.user_id == user_id)
        )
        return list(result.scalars().all())
