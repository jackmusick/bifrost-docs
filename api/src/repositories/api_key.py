"""
API Key Repository

Provides database operations for APIKey model.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.orm.api_key import APIKey
from src.repositories.base import BaseRepository


class ApiKeyRepository(BaseRepository[APIKey]):
    """Repository for APIKey model operations."""

    model = APIKey

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_user(
        self, user_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[APIKey]:
        """
        Get all API keys for a user.

        Args:
            user_id: User UUID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of API keys for the user
        """
        result = await self.session.execute(
            select(APIKey)
            .where(APIKey.user_id == user_id)
            .order_by(APIKey.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_id_and_user(self, id: UUID, user_id: UUID) -> APIKey | None:
        """
        Get an API key by ID within user scope.

        Args:
            id: API key UUID
            user_id: User UUID

        Returns:
            APIKey if found and belongs to user, None otherwise
        """
        result = await self.session.execute(
            select(APIKey).where(
                APIKey.id == id,
                APIKey.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_key_hash(self, key_hash: str) -> APIKey | None:
        """
        Get an API key by its hash.

        Args:
            key_hash: SHA-256 hash of the API key

        Returns:
            APIKey if found, None otherwise
        """
        result = await self.session.execute(
            select(APIKey).where(APIKey.key_hash == key_hash)
        )
        return result.scalar_one_or_none()
