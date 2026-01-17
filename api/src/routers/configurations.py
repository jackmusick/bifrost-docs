"""
Configurations Router

Provides CRUD endpoints for configurations within organizations.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import update

from src.core.auth import CurrentActiveUser, RequireContributor
from src.core.database import DbSession
from src.models.contracts.common import BatchToggleRequest, BatchToggleResponse
from src.models.contracts.configuration import (
    ConfigurationCreate,
    ConfigurationPublic,
    ConfigurationUpdate,
)
from src.models.enums import AuditAction
from src.models.orm.configuration import Configuration
from src.repositories.configuration import ConfigurationRepository
from src.services.audit_service import get_audit_service
from src.services.search_indexing import index_entity_for_search, remove_entity_from_search


class ConfigurationListResponse(BaseModel):
    """Paginated response for configuration list."""

    items: list[ConfigurationPublic]
    total: int
    limit: int
    offset: int

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/organizations/{org_id}/configurations",
    tags=["configurations"],
)


def _configuration_to_public(config: Configuration) -> ConfigurationPublic:
    """Convert Configuration ORM model to public response."""
    return ConfigurationPublic(
        id=str(config.id),
        organization_id=str(config.organization_id),
        configuration_type_id=str(config.configuration_type_id) if config.configuration_type_id else None,
        configuration_status_id=str(config.configuration_status_id) if config.configuration_status_id else None,
        name=config.name,
        serial_number=config.serial_number,
        asset_tag=config.asset_tag,
        manufacturer=config.manufacturer,
        model=config.model,
        ip_address=config.ip_address,
        mac_address=config.mac_address,
        notes=config.notes,
        metadata=config.metadata_ if isinstance(config.metadata_, dict) else {},
        interfaces=config.interfaces if isinstance(config.interfaces, list) else [],
        is_enabled=config.is_enabled,
        created_at=config.created_at,
        updated_at=config.updated_at,
        configuration_type_name=config.configuration_type.name if config.configuration_type else None,
        configuration_status_name=config.configuration_status.name if config.configuration_status else None,
        updated_by_user_id=str(config.updated_by_user_id) if config.updated_by_user_id else None,
        updated_by_user_name=config.updated_by_user.email if config.updated_by_user else None,
    )


@router.get("", response_model=ConfigurationListResponse)
async def list_configurations(
    org_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
    type_id: UUID | None = Query(None, alias="configuration_type_id"),
    status_id: UUID | None = Query(None, alias="configuration_status_id"),
    search: str | None = Query(None, description="Search configurations"),
    sort_by: str | None = Query(None, description="Column to sort by"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    show_disabled: bool = Query(False, description="Include disabled configurations"),
) -> ConfigurationListResponse:
    """
    List configurations for an organization with pagination and search.

    Args:
        org_id: Organization UUID
        current_user: Current authenticated user
        db: Database session
        type_id: Optional filter by configuration type
        status_id: Optional filter by configuration status
        search: Optional search term
        sort_by: Column to sort by
        sort_dir: Sort direction ("asc" or "desc")
        limit: Maximum number of results
        offset: Number of results to skip
        show_disabled: Include disabled configurations

    Returns:
        Paginated list of configurations
    """
    repo = ConfigurationRepository(db)
    # Filter by is_enabled: when show_disabled=False, only show enabled (True)
    # When show_disabled=True, show all (None filter)
    is_enabled_filter = None if show_disabled else True
    configurations, total = await repo.get_paginated_by_org(
        org_id,
        configuration_type_id=type_id,
        configuration_status_id=status_id,
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
        is_enabled=is_enabled_filter,
    )

    return ConfigurationListResponse(
        items=[_configuration_to_public(c) for c in configurations],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ConfigurationPublic, status_code=status.HTTP_201_CREATED)
async def create_configuration(
    org_id: UUID,
    data: ConfigurationCreate,
    current_user: RequireContributor,
    db: DbSession,
) -> ConfigurationPublic:
    """
    Create a new configuration.

    Args:
        org_id: Organization UUID
        data: Configuration creation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created configuration
    """
    repo = ConfigurationRepository(db)
    config = Configuration(
        organization_id=org_id,
        configuration_type_id=UUID(data.configuration_type_id) if data.configuration_type_id else None,
        configuration_status_id=UUID(data.configuration_status_id) if data.configuration_status_id else None,
        name=data.name,
        serial_number=data.serial_number,
        asset_tag=data.asset_tag,
        manufacturer=data.manufacturer,
        model=data.model,
        ip_address=data.ip_address,
        mac_address=data.mac_address,
        notes=data.notes,
        metadata_=data.metadata,
        interfaces=data.interfaces,
        is_enabled=data.is_enabled if data.is_enabled is not None else True,
    )
    config = await repo.create(config)

    # Reload to get relationships
    config = await repo.get_by_id_for_org(config.id, org_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reload configuration after creation",
        )

    # Audit log
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.CREATE,
        "configuration",
        config.id,
        actor=current_user,
        organization_id=org_id,
    )

    logger.info(
        f"Configuration created: {config.name}",
        extra={
            "config_id": str(config.id),
            "org_id": str(org_id),
            "user_id": str(current_user.user_id),
        },
    )

    # Index for search (async, non-blocking on failure)
    await index_entity_for_search(db, "configuration", config.id, org_id)

    return _configuration_to_public(config)


@router.get("/{config_id}", response_model=ConfigurationPublic)
async def get_configuration(
    org_id: UUID,
    config_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> ConfigurationPublic:
    """
    Get configuration by ID.

    Args:
        org_id: Organization UUID
        config_id: Configuration UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Configuration details

    Raises:
        HTTPException: If configuration not found
    """
    repo = ConfigurationRepository(db)
    config = await repo.get_by_id_for_org(config_id, org_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found",
        )

    # Log view (with 60-second dedupe)
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.VIEW,
        "configuration",
        config.id,
        actor=current_user,
        organization_id=org_id,
        dedupe_seconds=60,
    )

    return _configuration_to_public(config)


@router.get("/{config_id}/preview")
async def get_configuration_preview(
    org_id: UUID,
    config_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> dict:
    """
    Get configuration preview for search.

    Returns formatted markdown content suitable for rendering in a preview panel.

    Args:
        org_id: Organization UUID
        config_id: Configuration UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Preview data with formatted content

    Raises:
        HTTPException: If configuration not found
    """
    repo = ConfigurationRepository(db)
    config = await repo.get_by_id_for_org(config_id, org_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found",
        )

    # Build preview content
    content_parts = [f"# {config.name}"]

    if config.configuration_type:
        content_parts.append(f"\n**Type:** {config.configuration_type.name}")
    if config.configuration_status:
        content_parts.append(f"\n**Status:** {config.configuration_status.name}")
    if config.ip_address:
        content_parts.append(f"\n**IP Address:** {config.ip_address}")
    if config.mac_address:
        content_parts.append(f"\n**MAC Address:** {config.mac_address}")
    if config.manufacturer:
        content_parts.append(f"\n**Manufacturer:** {config.manufacturer}")
    if config.model:
        content_parts.append(f"\n**Model:** {config.model}")
    if config.serial_number:
        content_parts.append(f"\n**Serial Number:** {config.serial_number}")
    if config.asset_tag:
        content_parts.append(f"\n**Asset Tag:** {config.asset_tag}")
    if config.notes:
        content_parts.append(f"\n## Notes\n{config.notes}")

    return {
        "id": str(config.id),
        "name": config.name,
        "content": "\n".join(content_parts),
        "entity_type": "configuration",
        "organization_id": str(org_id),
    }


@router.put("/{config_id}", response_model=ConfigurationPublic)
async def update_configuration(
    org_id: UUID,
    config_id: UUID,
    data: ConfigurationUpdate,
    current_user: RequireContributor,
    db: DbSession,
) -> ConfigurationPublic:
    """
    Update configuration.

    Args:
        org_id: Organization UUID
        config_id: Configuration UUID
        data: Configuration update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated configuration

    Raises:
        HTTPException: If configuration not found
    """
    repo = ConfigurationRepository(db)
    config = await repo.get_by_id_for_org(config_id, org_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found",
        )

    # Update fields if provided
    if data.name is not None:
        config.name = data.name
    if data.configuration_type_id is not None:
        config.configuration_type_id = UUID(data.configuration_type_id) if data.configuration_type_id else None
    if data.configuration_status_id is not None:
        config.configuration_status_id = UUID(data.configuration_status_id) if data.configuration_status_id else None
    if data.serial_number is not None:
        config.serial_number = data.serial_number
    if data.asset_tag is not None:
        config.asset_tag = data.asset_tag
    if data.manufacturer is not None:
        config.manufacturer = data.manufacturer
    if data.model is not None:
        config.model = data.model
    if data.ip_address is not None:
        config.ip_address = data.ip_address
    if data.mac_address is not None:
        config.mac_address = data.mac_address
    if data.notes is not None:
        config.notes = data.notes
    if data.metadata is not None:
        config.metadata_ = data.metadata
    if data.interfaces is not None:
        config.interfaces = data.interfaces
    if data.is_enabled is not None:
        config.is_enabled = data.is_enabled

    # Track who updated
    config.updated_by_user_id = current_user.user_id

    config = await repo.update(config)

    # Reload to get updated relationships
    config = await repo.get_by_id_for_org(config_id, org_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reload configuration after update",
        )

    # Audit log
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.UPDATE,
        "configuration",
        config.id,
        actor=current_user,
        organization_id=org_id,
    )

    logger.info(
        f"Configuration updated: {config.name}",
        extra={
            "config_id": str(config_id),
            "org_id": str(org_id),
            "user_id": str(current_user.user_id),
        },
    )

    # Update search index (async, non-blocking on failure)
    await index_entity_for_search(db, "configuration", config_id, org_id)

    return _configuration_to_public(config)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration(
    org_id: UUID,
    config_id: UUID,
    current_user: RequireContributor,
    db: DbSession,
) -> None:
    """
    Delete configuration.

    Args:
        org_id: Organization UUID
        config_id: Configuration UUID
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If configuration not found
    """
    repo = ConfigurationRepository(db)

    # Audit log (before delete)
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.DELETE,
        "configuration",
        config_id,
        actor=current_user,
        organization_id=org_id,
    )

    deleted = await repo.delete_for_org(config_id, org_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found",
        )

    # Remove from search index (async, non-blocking on failure)
    await remove_entity_from_search(db, "configuration", config_id)

    logger.info(
        f"Configuration deleted: {config_id}",
        extra={
            "config_id": str(config_id),
            "org_id": str(org_id),
            "user_id": str(current_user.user_id),
        },
    )


@router.patch("/batch", response_model=BatchToggleResponse)
async def batch_toggle_configurations(
    org_id: UUID,
    request: BatchToggleRequest,
    current_user: RequireContributor,
    db: DbSession,
) -> BatchToggleResponse:
    """
    Batch toggle configurations enabled/disabled status.

    Args:
        org_id: Organization UUID
        request: Batch toggle request with IDs and new is_enabled value
        current_user: Current authenticated user
        db: Database session

    Returns:
        Number of configurations updated
    """
    # Convert string IDs to UUIDs
    config_ids = [UUID(id_str) for id_str in request.ids]

    # Batch update
    result = await db.execute(
        update(Configuration)
        .where(Configuration.id.in_(config_ids))
        .where(Configuration.organization_id == org_id)
        .values(is_enabled=request.is_enabled)
    )
    await db.commit()

    logger.info(
        f"Batch toggle configurations: {result.rowcount} configs set to is_enabled={request.is_enabled}",
        extra={
            "org_id": str(org_id),
            "user_id": str(current_user.user_id),
            "updated_count": result.rowcount,
        },
    )

    return BatchToggleResponse(updated_count=result.rowcount)
