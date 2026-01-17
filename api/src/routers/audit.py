"""
Audit Log Router

Provides endpoints for querying audit logs.
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query

from src.core.auth import CurrentActiveUser
from src.core.database import DbSession
from src.models.contracts.audit import AuditLogEntry, AuditLogListResponse
from src.repositories.audit import AuditRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    current_user: CurrentActiveUser,
    db: DbSession,
    organization_id: UUID | None = Query(None, description="Filter by organization"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: UUID | None = Query(None, description="Filter by entity ID"),
    action: str | None = Query(None, description="Filter by action"),
    actor_user_id: UUID | None = Query(None, description="Filter by actor user"),
    start_date: datetime | None = Query(None, description="Filter by start date"),
    end_date: datetime | None = Query(None, description="Filter by end date"),
    search: str | None = Query(None, description="Search by org name, actor, entity type, or action"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> AuditLogListResponse:
    """
    List audit logs with filtering and pagination.

    Global view showing all audit logs the user has access to.
    Filter by organization_id to scope to a specific org.
    """
    audit_repo = AuditRepository(db)
    logs, total = await audit_repo.get_paginated(
        organization_id=organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_user_id=actor_user_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
        page=page,
        page_size=page_size,
    )

    items = [
        AuditLogEntry(
            id=str(log.id),
            organization_id=str(log.organization_id) if log.organization_id else None,
            organization_name=log.organization.name if log.organization else None,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=str(log.entity_id),
            entity_name=None,  # TODO: Resolve entity names in future iteration
            actor_type=log.actor_type,
            actor_user_id=str(log.actor_user_id) if log.actor_user_id else None,
            actor_display_name=(
                log.actor_user.email if log.actor_user
                else log.actor_api_key.name if log.actor_api_key
                else log.actor_label
            ),
            actor_label=log.actor_label,
            created_at=log.created_at,
        )
        for log in logs
    ]

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# Organization-scoped endpoint
org_router = APIRouter(prefix="/api/organizations/{org_id}/audit-logs", tags=["audit"])


@org_router.get("", response_model=AuditLogListResponse)
async def list_org_audit_logs(
    org_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: UUID | None = Query(None, description="Filter by entity ID"),
    action: str | None = Query(None, description="Filter by action"),
    actor_user_id: UUID | None = Query(None, description="Filter by actor user"),
    start_date: datetime | None = Query(None, description="Filter by start date"),
    end_date: datetime | None = Query(None, description="Filter by end date"),
    search: str | None = Query(None, description="Search by actor, entity type, or action"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> AuditLogListResponse:
    """
    List audit logs for a specific organization.

    Includes both org-scoped events and system-level events.
    """
    audit_repo = AuditRepository(db)
    logs, total = await audit_repo.get_paginated(
        organization_id=org_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_user_id=actor_user_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
        page=page,
        page_size=page_size,
        include_system=False,  # Org view doesn't include system events
    )

    items = [
        AuditLogEntry(
            id=str(log.id),
            organization_id=str(log.organization_id) if log.organization_id else None,
            organization_name=log.organization.name if log.organization else None,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=str(log.entity_id),
            entity_name=None,
            actor_type=log.actor_type,
            actor_user_id=str(log.actor_user_id) if log.actor_user_id else None,
            actor_display_name=(
                log.actor_user.email if log.actor_user
                else log.actor_api_key.name if log.actor_api_key
                else log.actor_label
            ),
            actor_label=log.actor_label,
            created_at=log.created_at,
        )
        for log in logs
    ]

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
