"""
Export Repository

Provides database operations for Export model.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.orm.export import Export, ExportStatus
from src.repositories.base import BaseRepository


class ExportRepository(BaseRepository[Export]):
    """Repository for Export model operations."""

    model = Export

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_user(
        self, user_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[Export]:
        """
        Get all exports for a user, ordered by creation date descending.

        Args:
            user_id: User UUID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of exports for the user
        """
        result = await self.session.execute(
            select(Export)
            .where(Export.user_id == user_id)
            .order_by(Export.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_id_and_user(
        self, id: UUID, user_id: UUID
    ) -> Export | None:
        """
        Get an export by ID within a user scope.

        Args:
            id: Export UUID
            user_id: User UUID

        Returns:
            Export if found and belongs to user, None otherwise
        """
        result = await self.session.execute(
            select(Export).where(
                Export.id == id,
                Export.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_pending_exports(self) -> list[Export]:
        """
        Get all pending exports that need processing.

        Returns:
            List of pending exports
        """
        result = await self.session.execute(
            select(Export)
            .where(Export.status == ExportStatus.PENDING)
            .order_by(Export.created_at)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        export: Export,
        status: ExportStatus,
        s3_key: str | None = None,
        file_size_bytes: int | None = None,
        error_message: str | None = None,
    ) -> Export:
        """
        Update export status and related fields.

        Args:
            export: Export to update
            status: New status
            s3_key: S3 key if completed
            file_size_bytes: File size if completed
            error_message: Error message if failed

        Returns:
            Updated export
        """
        export.status = status
        if s3_key is not None:
            export.s3_key = s3_key
        if file_size_bytes is not None:
            export.file_size_bytes = file_size_bytes
        if error_message is not None:
            export.error_message = error_message
        export.updated_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(export)
        return export

    async def revoke(self, export: Export) -> Export:
        """
        Revoke an export.

        Args:
            export: Export to revoke

        Returns:
            Updated export with revoked_at set
        """
        export.revoked_at = datetime.now(UTC)
        export.updated_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(export)
        return export

    async def count_by_user(self, user_id: UUID) -> int:
        """
        Count exports for a user.

        Args:
            user_id: User UUID

        Returns:
            Count of exports
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(Export.id)).where(Export.user_id == user_id)
        )
        return result.scalar_one()
