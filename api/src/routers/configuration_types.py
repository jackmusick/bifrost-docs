"""
Configuration Types Router

Provides CRUD endpoints for global configuration types.
Read: any authenticated user
Write: superusers only
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.core.auth import CurrentActiveUser, CurrentSuperuser
from src.core.database import DbSession
from src.models.contracts.configuration import (
    ConfigurationTypeCreate,
    ConfigurationTypePublic,
)
from src.models.orm.configuration_type import ConfigurationType
from src.repositories.configuration_type import ConfigurationTypeRepository

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/configuration-types",
    tags=["configuration-types"],
)


@router.get("", response_model=list[ConfigurationTypePublic])
async def list_configuration_types(
    current_user: CurrentActiveUser,
    db: DbSession,
    limit: int = 100,
    offset: int = 0,
    include_inactive: bool = False,
) -> list[ConfigurationTypePublic]:
    """
    List all configuration types.

    Any authenticated user can read configuration types.

    Args:
        current_user: Current authenticated user
        db: Database session
        limit: Maximum number of results
        offset: Number of results to skip
        include_inactive: Include inactive types (default False)

    Returns:
        List of configuration types
    """
    repo = ConfigurationTypeRepository(db)
    config_types = await repo.get_all_ordered(
        limit=limit, offset=offset, include_inactive=include_inactive
    )

    result = []
    for ct in config_types:
        config_count = await repo.get_configuration_count(ct.id)
        result.append(
            ConfigurationTypePublic(
                id=str(ct.id),
                name=ct.name,
                is_active=ct.is_active,
                created_at=ct.created_at,
                configuration_count=config_count,
            )
        )
    return result


@router.post("", response_model=ConfigurationTypePublic, status_code=status.HTTP_201_CREATED)
async def create_configuration_type(
    data: ConfigurationTypeCreate,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> ConfigurationTypePublic:
    """
    Create a new configuration type.

    Superusers only.

    Args:
        data: Configuration type creation data
        current_user: Current superuser
        db: Database session

    Returns:
        Created configuration type
    """
    repo = ConfigurationTypeRepository(db)

    # Check for duplicate name
    existing = await repo.get_by_name(data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Configuration type with name '{data.name}' already exists",
        )

    config_type = ConfigurationType(name=data.name)
    config_type = await repo.create(config_type)

    logger.info(
        f"Configuration type created: {config_type.name}",
        extra={
            "config_type_id": str(config_type.id),
            "user_id": str(current_user.user_id),
        },
    )

    return ConfigurationTypePublic(
        id=str(config_type.id),
        name=config_type.name,
        is_active=config_type.is_active,
        created_at=config_type.created_at,
        configuration_count=0,
    )


@router.get("/{type_id}", response_model=ConfigurationTypePublic)
async def get_configuration_type(
    type_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> ConfigurationTypePublic:
    """
    Get configuration type by ID.

    Any authenticated user can read configuration types.

    Args:
        type_id: Configuration type UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Configuration type details

    Raises:
        HTTPException: If configuration type not found
    """
    repo = ConfigurationTypeRepository(db)
    config_type = await repo.get_by_id(type_id)

    if not config_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration type not found",
        )

    config_count = await repo.get_configuration_count(type_id)
    return ConfigurationTypePublic(
        id=str(config_type.id),
        name=config_type.name,
        is_active=config_type.is_active,
        created_at=config_type.created_at,
        configuration_count=config_count,
    )


@router.post("/{type_id}/deactivate", response_model=ConfigurationTypePublic)
async def deactivate_configuration_type(
    type_id: UUID,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> ConfigurationTypePublic:
    """
    Deactivate (soft delete) a configuration type.

    Deactivated types are hidden from normal listings but configurations are preserved.
    Superusers only.

    Args:
        type_id: Configuration type UUID
        current_user: Current superuser
        db: Database session

    Returns:
        Updated configuration type
    """
    repo = ConfigurationTypeRepository(db)
    config_type = await repo.get_by_id(type_id)

    if not config_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration type not found",
        )

    config_type = await repo.deactivate(type_id)
    config_count = await repo.get_configuration_count(type_id)

    logger.info(
        f"Configuration type deactivated: {config_type.name}",
        extra={
            "config_type_id": str(type_id),
            "user_id": str(current_user.user_id),
        },
    )

    return ConfigurationTypePublic(
        id=str(config_type.id),
        name=config_type.name,
        is_active=config_type.is_active,
        created_at=config_type.created_at,
        configuration_count=config_count,
    )


@router.post("/{type_id}/activate", response_model=ConfigurationTypePublic)
async def activate_configuration_type(
    type_id: UUID,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> ConfigurationTypePublic:
    """
    Reactivate a deactivated configuration type.

    Superusers only.

    Args:
        type_id: Configuration type UUID
        current_user: Current superuser
        db: Database session

    Returns:
        Updated configuration type
    """
    repo = ConfigurationTypeRepository(db)
    config_type = await repo.get_by_id(type_id)

    if not config_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration type not found",
        )

    config_type = await repo.activate(type_id)
    config_count = await repo.get_configuration_count(type_id)

    logger.info(
        f"Configuration type activated: {config_type.name}",
        extra={
            "config_type_id": str(type_id),
            "user_id": str(current_user.user_id),
        },
    )

    return ConfigurationTypePublic(
        id=str(config_type.id),
        name=config_type.name,
        is_active=config_type.is_active,
        created_at=config_type.created_at,
        configuration_count=config_count,
    )


@router.delete("/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration_type(
    type_id: UUID,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> None:
    """
    Delete configuration type.

    Only allowed if no configurations exist. Use deactivate for types with existing configurations.
    Superusers only.

    Args:
        type_id: Configuration type UUID
        current_user: Current superuser
        db: Database session

    Raises:
        HTTPException: If configuration type not found or has configurations
    """
    repo = ConfigurationTypeRepository(db)
    config_type = await repo.get_by_id(type_id)

    if not config_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration type not found",
        )

    # Check if type can be deleted
    if not await repo.can_delete(type_id):
        config_count = await repo.get_configuration_count(type_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete - {config_count} configurations exist. Deactivate instead.",
        )

    await repo.delete_by_id(type_id)

    logger.info(
        f"Configuration type deleted: {type_id}",
        extra={
            "config_type_id": str(type_id),
            "user_id": str(current_user.user_id),
        },
    )
