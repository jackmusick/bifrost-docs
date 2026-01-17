"""
Custom Asset Types Router.

Provides CRUD endpoints for global custom asset types.
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
from src.models.contracts.custom_asset import (
    CustomAssetTypeCreate,
    CustomAssetTypePublic,
    CustomAssetTypeReorder,
    CustomAssetTypeUpdate,
    FieldDefinition,
)
from src.models.orm.custom_asset_type import CustomAssetType
from src.repositories.custom_asset_type import CustomAssetTypeRepository
from src.services.custom_asset_validation import (
    CustomAssetValidationError,
    validate_field_definitions,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/custom-asset-types",
    tags=["custom-asset-types"],
)


def _to_public(asset_type: CustomAssetType, asset_count: int = 0) -> CustomAssetTypePublic:
    """Convert ORM model to public response."""
    return CustomAssetTypePublic(
        id=str(asset_type.id),
        name=asset_type.name,
        fields=[FieldDefinition(**f) for f in asset_type.fields],
        sort_order=asset_type.sort_order,
        display_field_key=asset_type.display_field_key,
        is_active=asset_type.is_active,
        created_at=asset_type.created_at,
        updated_at=asset_type.updated_at,
        asset_count=asset_count,
    )


@router.get("", response_model=list[CustomAssetTypePublic])
async def list_custom_asset_types(
    current_user: CurrentActiveUser,
    db: DbSession,
    limit: int = 100,
    offset: int = 0,
    include_inactive: bool = False,
) -> list[CustomAssetTypePublic]:
    """
    List all custom asset types.

    Any authenticated user can read custom asset types.

    Args:
        current_user: Current authenticated user
        db: Database session
        limit: Maximum number of results (default 100)
        offset: Number of results to skip (default 0)
        include_inactive: Include inactive types (default False)

    Returns:
        List of custom asset types
    """
    repo = CustomAssetTypeRepository(db)
    asset_types = await repo.get_all_ordered(
        limit=limit, offset=offset, include_inactive=include_inactive
    )

    # Get asset counts for each type
    result = []
    for at in asset_types:
        asset_count = await repo.get_asset_count(at.id)
        result.append(_to_public(at, asset_count))

    return result


@router.patch("/reorder", status_code=status.HTTP_200_OK)
async def reorder_custom_asset_types(
    data: CustomAssetTypeReorder,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> None:
    """
    Reorder custom asset types.

    Updates the sort_order for each custom asset type based on the provided order.
    Superusers only.

    Args:
        data: Reorder request with ordered list of type IDs
        current_user: Current superuser
        db: Database session

    Returns:
        200 OK on success
    """
    repo = CustomAssetTypeRepository(db)

    # Validate all IDs exist
    for type_id_str in data.ids:
        try:
            type_id = UUID(type_id_str)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid UUID format: {type_id_str}",
            ) from exc

        asset_type = await repo.get_by_id(type_id)
        if not asset_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Custom asset type not found: {type_id_str}",
            )

    # Update sort_order for each type based on array index
    for index, type_id_str in enumerate(data.ids):
        type_id = UUID(type_id_str)
        asset_type = await repo.get_by_id(type_id)
        if asset_type:
            asset_type.sort_order = index

    # Flush to persist changes
    await db.flush()

    logger.info(
        "Custom asset types reordered",
        extra={
            "user_id": str(current_user.user_id),
            "count": len(data.ids),
        },
    )


@router.post("", response_model=CustomAssetTypePublic, status_code=status.HTTP_201_CREATED)
async def create_custom_asset_type(
    data: CustomAssetTypeCreate,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> CustomAssetTypePublic:
    """
    Create a new custom asset type.

    Superusers only.

    Args:
        data: Custom asset type creation data
        current_user: Current superuser
        db: Database session

    Returns:
        Created custom asset type
    """
    # Validate field definitions
    try:
        validate_field_definitions(data.fields)
    except CustomAssetValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    # Validate display_field_key references a valid field
    if data.display_field_key:
        valid_keys = {f.key for f in data.fields}
        if data.display_field_key not in valid_keys:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"display_field_key '{data.display_field_key}' must match a field key",
            )

    repo = CustomAssetTypeRepository(db)

    # Check for duplicate name
    existing = await repo.get_by_name(data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Custom asset type with name '{data.name}' already exists",
        )

    # Create the custom asset type
    asset_type = CustomAssetType(
        name=data.name,
        fields=[f.model_dump() for f in data.fields],
        display_field_key=data.display_field_key,
    )
    asset_type = await repo.create(asset_type)

    logger.info(
        f"Custom asset type created: {asset_type.name}",
        extra={
            "asset_type_id": str(asset_type.id),
            "user_id": str(current_user.user_id),
        },
    )

    return _to_public(asset_type)


@router.get("/{type_id}", response_model=CustomAssetTypePublic)
async def get_custom_asset_type(
    type_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> CustomAssetTypePublic:
    """
    Get a custom asset type by ID.

    Any authenticated user can read custom asset types.

    Args:
        type_id: Custom asset type UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Custom asset type details
    """
    repo = CustomAssetTypeRepository(db)
    asset_type = await repo.get_by_id(type_id)

    if not asset_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom asset type not found",
        )

    asset_count = await repo.get_asset_count(type_id)
    return _to_public(asset_type, asset_count)


@router.put("/{type_id}", response_model=CustomAssetTypePublic)
async def update_custom_asset_type(
    type_id: UUID,
    data: CustomAssetTypeUpdate,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> CustomAssetTypePublic:
    """
    Update a custom asset type.

    Superusers only.

    Args:
        type_id: Custom asset type UUID
        data: Custom asset type update data
        current_user: Current superuser
        db: Database session

    Returns:
        Updated custom asset type
    """
    repo = CustomAssetTypeRepository(db)
    asset_type = await repo.get_by_id(type_id)

    if not asset_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom asset type not found",
        )

    # Validate field definitions if provided
    if data.fields is not None:
        try:
            validate_field_definitions(data.fields)
        except CustomAssetValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            ) from e

    # Validate display_field_key if provided
    if "display_field_key" in data.model_fields_set and data.display_field_key:
        # Use updated fields if provided, otherwise use existing fields
        fields_to_check = data.fields if data.fields is not None else [
            FieldDefinition(**f) for f in asset_type.fields
        ]
        valid_keys = {f.key for f in fields_to_check}
        if data.display_field_key not in valid_keys:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"display_field_key '{data.display_field_key}' must match a field key",
            )

    # Check for duplicate name if name is being updated
    if data.name is not None and data.name != asset_type.name:
        existing = await repo.get_by_name(data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Custom asset type with name '{data.name}' already exists",
            )
        asset_type.name = data.name

    if data.fields is not None:
        asset_type.fields = [f.model_dump() for f in data.fields]

    # Update display_field_key - allow setting to None explicitly
    if "display_field_key" in data.model_fields_set:
        asset_type.display_field_key = data.display_field_key

    asset_type = await repo.update(asset_type)
    asset_count = await repo.get_asset_count(type_id)

    logger.info(
        f"Custom asset type updated: {asset_type.name}",
        extra={
            "asset_type_id": str(asset_type.id),
            "user_id": str(current_user.user_id),
        },
    )

    return _to_public(asset_type, asset_count)


@router.post("/{type_id}/deactivate", response_model=CustomAssetTypePublic)
async def deactivate_custom_asset_type(
    type_id: UUID,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> CustomAssetTypePublic:
    """
    Deactivate (soft delete) a custom asset type.

    Deactivated types are hidden from normal listings but assets are preserved.
    Superusers only.

    Args:
        type_id: Custom asset type UUID
        current_user: Current superuser
        db: Database session

    Returns:
        Updated custom asset type
    """
    repo = CustomAssetTypeRepository(db)
    asset_type = await repo.get_by_id(type_id)

    if not asset_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom asset type not found",
        )

    asset_type = await repo.deactivate(type_id)
    asset_count = await repo.get_asset_count(type_id)

    logger.info(
        f"Custom asset type deactivated: {asset_type.name}",
        extra={
            "asset_type_id": str(type_id),
            "user_id": str(current_user.user_id),
        },
    )

    return _to_public(asset_type, asset_count)


@router.post("/{type_id}/activate", response_model=CustomAssetTypePublic)
async def activate_custom_asset_type(
    type_id: UUID,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> CustomAssetTypePublic:
    """
    Reactivate a deactivated custom asset type.

    Superusers only.

    Args:
        type_id: Custom asset type UUID
        current_user: Current superuser
        db: Database session

    Returns:
        Updated custom asset type
    """
    repo = CustomAssetTypeRepository(db)
    asset_type = await repo.get_by_id(type_id)

    if not asset_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom asset type not found",
        )

    asset_type = await repo.activate(type_id)
    asset_count = await repo.get_asset_count(type_id)

    logger.info(
        f"Custom asset type activated: {asset_type.name}",
        extra={
            "asset_type_id": str(type_id),
            "user_id": str(current_user.user_id),
        },
    )

    return _to_public(asset_type, asset_count)


@router.delete("/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_asset_type(
    type_id: UUID,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> None:
    """
    Delete a custom asset type.

    Only allowed if no assets exist. Use deactivate for types with existing assets.
    Superusers only.

    Args:
        type_id: Custom asset type UUID
        current_user: Current superuser
        db: Database session
    """
    repo = CustomAssetTypeRepository(db)
    asset_type = await repo.get_by_id(type_id)

    if not asset_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom asset type not found",
        )

    # Check if type can be deleted
    if not await repo.can_delete(type_id):
        asset_count = await repo.get_asset_count(type_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete - {asset_count} assets exist. Deactivate instead.",
        )

    await repo.delete(asset_type)

    logger.info(
        f"Custom asset type deleted: {asset_type.name}",
        extra={
            "asset_type_id": str(type_id),
            "user_id": str(current_user.user_id),
        },
    )


