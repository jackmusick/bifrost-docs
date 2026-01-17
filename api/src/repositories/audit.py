"""
Audit Log Repository

Provides database operations for querying audit logs.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.models.orm.audit_log import AuditLog
from src.models.orm.organization import Organization
from src.models.orm.user import User


class AuditRepository:
    """Repository for AuditLog model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_paginated(
        self,
        *,
        organization_id: UUID | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        action: str | None = None,
        actor_user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
        include_system: bool = True,
    ) -> tuple[list[AuditLog], int]:
        """
        Get paginated audit logs with filters.

        Args:
            organization_id: Filter by organization (None = include all user has access to)
            entity_type: Filter by entity type
            entity_id: Filter by specific entity
            action: Filter by action type
            actor_user_id: Filter by actor user
            start_date: Filter by date range start
            end_date: Filter by date range end
            search: Search term for organization name, actor email, entity type, action
            page: Page number (1-indexed)
            page_size: Items per page
            include_system: Include system-level events (org_id is NULL)

        Returns:
            Tuple of (audit logs, total count)
        """
        filters = []

        if organization_id is not None:
            if include_system:
                filters.append(
                    (AuditLog.organization_id == organization_id)
                    | (AuditLog.organization_id.is_(None))
                )
            else:
                filters.append(AuditLog.organization_id == organization_id)

        if entity_type is not None:
            filters.append(AuditLog.entity_type == entity_type)

        if entity_id is not None:
            filters.append(AuditLog.entity_id == entity_id)

        if action is not None:
            filters.append(AuditLog.action == action)

        if actor_user_id is not None:
            filters.append(AuditLog.actor_user_id == actor_user_id)

        if start_date is not None:
            filters.append(AuditLog.created_at >= start_date)

        if end_date is not None:
            filters.append(AuditLog.created_at <= end_date)

        # Search across multiple fields using joins
        search_filter = None
        if search:
            search_term = f"%{search.lower()}%"
            search_filter = or_(
                AuditLog.entity_type.ilike(search_term),
                AuditLog.action.ilike(search_term),
                AuditLog.actor_label.ilike(search_term),
                Organization.name.ilike(search_term),
                User.email.ilike(search_term),
                User.name.ilike(search_term),
            )

        # Build base query with joins for search
        base_query = select(AuditLog).outerjoin(
            Organization, AuditLog.organization_id == Organization.id
        ).outerjoin(
            User, AuditLog.actor_user_id == User.id
        )

        # Count query
        count_stmt = select(func.count(AuditLog.id)).select_from(
            AuditLog
        ).outerjoin(
            Organization, AuditLog.organization_id == Organization.id
        ).outerjoin(
            User, AuditLog.actor_user_id == User.id
        )
        if filters:
            count_stmt = count_stmt.where(*filters)
        if search_filter is not None:
            count_stmt = count_stmt.where(search_filter)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query with eager loading
        stmt = (
            base_query
            .options(
                joinedload(AuditLog.organization),
                joinedload(AuditLog.actor_user),
                joinedload(AuditLog.actor_api_key),
            )
            .order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        if filters:
            stmt = stmt.where(*filters)
        if search_filter is not None:
            stmt = stmt.where(search_filter)

        result = await self.session.execute(stmt)
        logs = list(result.scalars().unique().all())

        return logs, total

    async def delete_older_than(self, cutoff: datetime) -> int:
        """
        Delete audit logs older than cutoff date.

        Args:
            cutoff: Delete logs created before this datetime

        Returns:
            Number of deleted rows
        """
        stmt = delete(AuditLog).where(AuditLog.created_at < cutoff)
        result = await self.session.execute(stmt)
        return result.rowcount
