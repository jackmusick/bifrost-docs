"""
Document Repository

Provides database operations for Document model.
All queries are scoped to organization for multi-tenancy.
"""

from uuid import UUID

from sqlalchemy import distinct, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.orm.document import Document
from src.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository for Document model operations."""

    model = Document

    # Columns to search in for text search
    SEARCH_COLUMNS = ["name", "path", "content"]

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_paginated_by_org(
        self,
        organization_id: UUID,
        *,
        path: str | None = None,
        search: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        limit: int = 100,
        offset: int = 0,
        is_enabled: bool | None = None,
    ) -> tuple[list[Document], int]:
        """
        Get paginated documents for an organization with optional path filter, search and sorting.

        Args:
            organization_id: Organization UUID
            path: Optional filter by folder path
            search: Optional search term for name, path, content
            sort_by: Column to sort by
            sort_dir: Sort direction ("asc" or "desc")
            limit: Maximum number of results
            offset: Number of results to skip
            is_enabled: Filter by is_enabled status (None = no filter)

        Returns:
            Tuple of (list of documents, total count)
        """
        filters = [Document.organization_id == organization_id]

        if path is not None:
            filters.append(Document.path == path)

        if is_enabled is not None and hasattr(Document, 'is_enabled'):
            filters.append(Document.is_enabled == is_enabled)

        return await self.get_paginated(
            filters=filters,
            search_columns=self.SEARCH_COLUMNS,
            search_term=search,
            sort_by=sort_by or "name",  # Default sort by name
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
            options=[selectinload(Document.updated_by_user)],
        )

    async def get_by_id_and_org(
        self, id: UUID, organization_id: UUID
    ) -> Document | None:
        """
        Get document by ID, scoped to organization.

        Args:
            id: Document UUID
            organization_id: Organization UUID

        Returns:
            Document or None if not found
        """
        result = await self.session.execute(
            select(Document)
            .options(selectinload(Document.updated_by_user))
            .where(
                Document.id == id,
                Document.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all_by_org(
        self,
        organization_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Document]:
        """
        Get all documents for an organization.

        Args:
            organization_id: Organization UUID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of documents
        """
        result = await self.session.execute(
            select(Document)
            .where(Document.organization_id == organization_id)
            .order_by(Document.path, Document.name)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_path(
        self,
        organization_id: UUID,
        path: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Document]:
        """
        Get all documents in a specific folder path.

        Args:
            organization_id: Organization UUID
            path: Virtual folder path
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of documents in the specified path
        """
        result = await self.session.execute(
            select(Document)
            .where(
                Document.organization_id == organization_id,
                Document.path == path,
            )
            .order_by(Document.name)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_distinct_paths(self, organization_id: UUID) -> list[str]:
        """
        Get all unique folder paths for an organization.

        Used by frontend to build folder tree.

        Args:
            organization_id: Organization UUID

        Returns:
            List of distinct folder paths, sorted alphabetically
        """
        result = await self.session.execute(
            select(distinct(Document.path))
            .where(Document.organization_id == organization_id)
            .order_by(Document.path)
        )
        return [row[0] for row in result.fetchall()]

    async def get_paths_with_counts(
        self, organization_id: UUID
    ) -> list[tuple[str, int]]:
        """
        Get all folder paths with document counts for an organization.

        Args:
            organization_id: Organization UUID

        Returns:
            List of (path, count) tuples, sorted by path
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(Document.path, func.count(Document.id))
            .where(Document.organization_id == organization_id)
            .group_by(Document.path)
            .order_by(Document.path)
        )
        return [(row[0], row[1]) for row in result.fetchall()]

    async def delete_by_id_and_org(
        self, id: UUID, organization_id: UUID
    ) -> bool:
        """
        Delete document by ID, scoped to organization.

        Args:
            id: Document UUID
            organization_id: Organization UUID

        Returns:
            True if deleted, False if not found
        """
        document = await self.get_by_id_and_org(id, organization_id)
        if document:
            await self.delete(document)
            return True
        return False

    async def count_by_organization(self, organization_id: UUID) -> int:
        """
        Count documents for an organization.

        Args:
            organization_id: Organization UUID

        Returns:
            Count of documents
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(Document.id)).where(
                Document.organization_id == organization_id
            )
        )
        return result.scalar_one()

    async def check_path_conflicts(
        self,
        organization_id: UUID,
        old_prefix: str,
        new_prefix: str,
    ) -> list[str]:
        """
        Check if renaming paths would create conflicts.

        A conflict occurs when a document being moved would have the same
        path and name as an existing document at the new location.

        Args:
            organization_id: Organization UUID
            old_prefix: Current path prefix to match
            new_prefix: New path prefix to replace with

        Returns:
            List of document names that would conflict
        """
        from sqlalchemy import and_, func, literal

        # Documents that would be moved (exact match or under the path)
        # For path "foo", we match "foo" exactly or paths starting with "foo/"
        moving_docs_subquery = (
            select(
                Document.name,
                # Calculate the new path after move
                func.concat(
                    literal(new_prefix),
                    func.substr(Document.path, len(old_prefix) + 1),
                ).label("new_path"),
            )
            .where(
                and_(
                    Document.organization_id == organization_id,
                    # Match exact path or paths that start with old_prefix/
                    (Document.path == old_prefix)
                    | (Document.path.like(f"{old_prefix}/%")),
                )
            )
            .subquery()
        )

        # Find conflicts: documents at destination with same name
        conflict_query = (
            select(Document.name)
            .where(
                and_(
                    Document.organization_id == organization_id,
                    # Match documents at the new path locations
                    (Document.path == new_prefix)
                    | (Document.path.like(f"{new_prefix}/%")),
                    # Check if there's a moving doc with same name and path
                    Document.name.in_(
                        select(moving_docs_subquery.c.name).where(
                            moving_docs_subquery.c.new_path == Document.path
                        )
                    ),
                )
            )
            .distinct()
        )

        result = await self.session.execute(conflict_query)
        return [row[0] for row in result.fetchall()]

    async def batch_update_paths(
        self,
        organization_id: UUID,
        old_prefix: str,
        new_prefix: str,
    ) -> int:
        """
        Update all document paths from old prefix to new prefix.

        For path "foo" being renamed to "bar":
        - "foo" becomes "bar"
        - "foo/subpath" becomes "bar/subpath"

        Args:
            organization_id: Organization UUID
            old_prefix: Current path prefix to match
            new_prefix: New path prefix to replace with

        Returns:
            Number of documents updated
        """
        from sqlalchemy import case, func, literal

        # Update using SQL CONCAT to replace the prefix
        # For exact match (old_prefix), replace with new_prefix
        # For paths starting with old_prefix/, replace the prefix portion
        result = await self.session.execute(
            update(Document)
            .where(
                Document.organization_id == organization_id,
                # Match exact path or paths that start with old_prefix/
                (Document.path == old_prefix) | (Document.path.like(f"{old_prefix}/%")),
            )
            .values(
                path=case(
                    (Document.path == old_prefix, literal(new_prefix)),
                    else_=func.concat(
                        literal(new_prefix),
                        func.substr(Document.path, len(old_prefix) + 1),
                    ),
                )
            )
        )

        await self.session.flush()
        return result.rowcount
