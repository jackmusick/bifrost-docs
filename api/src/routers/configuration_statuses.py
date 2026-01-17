"""
Configuration Statuses Router

Provides CRUD endpoints for global configuration statuses.
Read: any authenticated user
Write: superusers only
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import update

from src.core.auth import CurrentActiveUser, CurrentSuperuser
from src.core.database import DbSession
from src.models.contracts.common import BatchToggleRequest, BatchToggleResponse
from src.models.contracts.configuration import (
    ConfigurationStatusCreate,
    ConfigurationStatusPublic,
)
from src.models.orm.configuration_status import ConfigurationStatus
from src.repositories.configuration_status import ConfigurationStatusRepository

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/configuration-statuses",
    tags=["configuration-statuses"],
)


@router.get("", response_model=list[ConfigurationStatusPublic])
async def list_configuration_statuses(
    current_user: CurrentActiveUser,
    db: DbSession,
    limit: int = 100,
    offset: int = 0,
    include_inactive: bool = False,
) -> list[ConfigurationStatusPublic]:
    """
    List all configuration statuses.

    Any authenticated user can read configuration statuses.

    Args:
        current_user: Current authenticated user
        db: Database session
        limit: Maximum number of results
        offset: Number of results to skip
        include_inactive: Include inactive statuses (default False)

    Returns:
        List of configuration statuses
    """
    repo = ConfigurationStatusRepository(db)
    statuses = await repo.get_all_ordered(
        limit=limit, offset=offset, include_inactive=include_inactive
    )

    result = []
    for s in statuses:
        config_count = await repo.get_configuration_count(s.id)
        result.append(
            ConfigurationStatusPublic(
                id=str(s.id),
                name=s.name,
                is_active=s.is_active,
                created_at=s.created_at,
                configuration_count=config_count,
            )
        )
    return result


@router.post("", response_model=ConfigurationStatusPublic, status_code=status.HTTP_201_CREATED)
async def create_configuration_status(
    data: ConfigurationStatusCreate,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> ConfigurationStatusPublic:
    """
    Create a new configuration status.

    Superusers only.

    Args:
        data: Configuration status creation data
        current_user: Current superuser
        db: Database session

    Returns:
        Created configuration status
    """
    repo = ConfigurationStatusRepository(db)

    # Check for duplicate name
    existing = await repo.get_by_name(data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Configuration status with name '{data.name}' already exists",
        )

    config_status = ConfigurationStatus(name=data.name)
    config_status = await repo.create(config_status)

    logger.info(
        f"Configuration status created: {config_status.name}",
        extra={
            "config_status_id": str(config_status.id),
            "user_id": str(current_user.user_id),
        },
    )

    return ConfigurationStatusPublic(
        id=str(config_status.id),
        name=config_status.name,
        is_active=config_status.is_active,
        created_at=config_status.created_at,
        configuration_count=0,
    )


@router.get("/{status_id}", response_model=ConfigurationStatusPublic)
async def get_configuration_status(
    status_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> ConfigurationStatusPublic:
    """
    Get configuration status by ID.

    Any authenticated user can read configuration statuses.

    Args:
        status_id: Configuration status UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Configuration status details

    Raises:
        HTTPException: If configuration status not found
    """
    repo = ConfigurationStatusRepository(db)
    config_status = await repo.get_by_id(status_id)

    if not config_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration status not found",
        )

    config_count = await repo.get_configuration_count(status_id)
    return ConfigurationStatusPublic(
        id=str(config_status.id),
        name=config_status.name,
        is_active=config_status.is_active,
        created_at=config_status.created_at,
        configuration_count=config_count,
    )


@router.post("/{status_id}/deactivate", response_model=ConfigurationStatusPublic)
async def deactivate_configuration_status(
    status_id: UUID,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> ConfigurationStatusPublic:
    """
    Deactivate (soft delete) a configuration status.

    Deactivated statuses are hidden from normal listings but configurations are preserved.
    Superusers only.

    Args:
        status_id: Configuration status UUID
        current_user: Current superuser
        db: Database session

    Returns:
        Updated configuration status
    """
    repo = ConfigurationStatusRepository(db)
    config_status = await repo.get_by_id(status_id)

    if not config_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration status not found",
        )

    config_status = await repo.deactivate(status_id)
    config_count = await repo.get_configuration_count(status_id)

    logger.info(
        f"Configuration status deactivated: {config_status.name}",
        extra={
            "config_status_id": str(status_id),
            "user_id": str(current_user.user_id),
        },
    )

    return ConfigurationStatusPublic(
        id=str(config_status.id),
        name=config_status.name,
        is_active=config_status.is_active,
        created_at=config_status.created_at,
        configuration_count=config_count,
    )


@router.post("/{status_id}/activate", response_model=ConfigurationStatusPublic)
async def activate_configuration_status(
    status_id: UUID,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> ConfigurationStatusPublic:
    """
    Reactivate a deactivated configuration status.

    Superusers only.

    Args:
        status_id: Configuration status UUID
        current_user: Current superuser
        db: Database session

    Returns:
        Updated configuration status
    """
    repo = ConfigurationStatusRepository(db)
    config_status = await repo.get_by_id(status_id)

    if not config_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration status not found",
        )

    config_status = await repo.activate(status_id)
    config_count = await repo.get_configuration_count(status_id)

    logger.info(
        f"Configuration status activated: {config_status.name}",
        extra={
            "config_status_id": str(status_id),
            "user_id": str(current_user.user_id),
        },
    )

    return ConfigurationStatusPublic(
        id=str(config_status.id),
        name=config_status.name,
        is_active=config_status.is_active,
        created_at=config_status.created_at,
        configuration_count=config_count,
    )


@router.delete("/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration_status(
    status_id: UUID,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> None:
    """
    Delete configuration status.

    Only allowed if no configurations exist. Use deactivate for statuses with existing configurations.
    Superusers only.

    Args:
        status_id: Configuration status UUID
        current_user: Current superuser
        db: Database session

    Raises:
        HTTPException: If configuration status not found or has configurations
    """
    repo = ConfigurationStatusRepository(db)
    config_status = await repo.get_by_id(status_id)

    if not config_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration status not found",
        )

    # Check if status can be deleted
    if not await repo.can_delete(status_id):
        config_count = await repo.get_configuration_count(status_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete - {config_count} configurations exist. Deactivate instead.",
        )

    await repo.delete_by_id(status_id)

    logger.info(
        f"Configuration status deleted: {status_id}",
        extra={
            "config_status_id": str(status_id),
            "user_id": str(current_user.user_id),
        },
    )


