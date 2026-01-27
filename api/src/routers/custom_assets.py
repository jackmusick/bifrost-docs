"""
Custom Assets Router.

Provides CRUD endpoints for custom asset instances within organizations.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import update

from src.core.auth import CurrentActiveUser, RequireContributor
from src.core.database import DbSession
from src.models.contracts.common import BatchToggleRequest, BatchToggleResponse
from src.models.contracts.custom_asset import (
    CustomAssetCreate,
    CustomAssetPublic,
    CustomAssetReveal,
    CustomAssetUpdate,
    FieldDefinition,
)
from src.models.enums import AuditAction
from src.models.orm.custom_asset import CustomAsset
from src.models.orm.custom_asset_type import CustomAssetType
from src.repositories.custom_asset import CustomAssetRepository
from src.repositories.custom_asset_type import CustomAssetTypeRepository
from src.services.audit_service import get_audit_service
from src.services.custom_asset_validation import (
    CustomAssetValidationError,
    apply_default_values,
    decrypt_password_fields,
    encrypt_password_fields,
    filter_password_fields,
    validate_values,
)
from src.services.search_indexing import index_entity_for_search, remove_entity_from_search


class CustomAssetListResponse(BaseModel):
    """Paginated response for custom asset list."""

    items: list[CustomAssetPublic]
    total: int
    limit: int
    offset: int

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/organizations/{org_id}/custom-asset-types/{type_id}/assets",
    tags=["custom-assets"],
)


async def _verify_org_access(
    org_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> None:
    """Verify user has access to the organization."""
    # Organization access is now handled by RLS policies
    pass


async def _get_asset_type(
    type_id: UUID,
    db: DbSession,
) -> CustomAssetType:
    """Get and verify custom asset type exists (types are global)."""
    type_repo = CustomAssetTypeRepository(db)
    asset_type = await type_repo.get_by_id(type_id)
    if not asset_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom asset type not found",
        )
    return asset_type


def _get_field_definitions(asset_type: CustomAssetType) -> list[FieldDefinition]:
    """Convert asset type fields to FieldDefinition objects."""
    return [FieldDefinition(**f) for f in asset_type.fields]


def _get_display_field_key(asset_type: CustomAssetType) -> str | None:
    """
    Get the display field key for an asset type.

    Priority:
    1. Use explicit display_field_key if set
    2. Fall back to first text/textbox field
    3. Fall back to first non-header field
    4. Return None if no fields

    Args:
        asset_type: CustomAssetType entity

    Returns:
        Field key to use for display, or None if no suitable field
    """
    if asset_type.display_field_key:
        return asset_type.display_field_key

    fields = _get_field_definitions(asset_type)
    non_header_fields = [f for f in fields if f.type != "header"]

    # Try to find first text/textbox field
    for field in non_header_fields:
        if field.type in ("text", "textbox"):
            return field.key

    # Fall back to first non-header field
    if non_header_fields:
        return non_header_fields[0].key

    return None


def _to_public(
    asset: CustomAsset,
    type_fields: list[FieldDefinition],
) -> CustomAssetPublic:
    """Convert ORM model to public response (password fields filtered)."""
    filtered_values = filter_password_fields(type_fields, asset.values)
    return CustomAssetPublic(
        id=str(asset.id),
        organization_id=str(asset.organization_id),
        custom_asset_type_id=str(asset.custom_asset_type_id),
        values=filtered_values,
        metadata=asset.metadata_ if isinstance(asset.metadata_, dict) else {},
        is_enabled=asset.is_enabled,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        updated_by_user_id=str(asset.updated_by_user_id) if asset.updated_by_user_id else None,
        updated_by_user_name=asset.updated_by_user.email if asset.updated_by_user else None,
    )


def _to_reveal(
    asset: CustomAsset,
    type_fields: list[FieldDefinition],
) -> CustomAssetReveal:
    """Convert ORM model to reveal response (password fields decrypted)."""
    decrypted_values = decrypt_password_fields(type_fields, asset.values)
    return CustomAssetReveal(
        id=str(asset.id),
        organization_id=str(asset.organization_id),
        custom_asset_type_id=str(asset.custom_asset_type_id),
        values=decrypted_values,
        metadata=asset.metadata_ if isinstance(asset.metadata_, dict) else {},
        is_enabled=asset.is_enabled,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        updated_by_user_id=str(asset.updated_by_user_id) if asset.updated_by_user_id else None,
        updated_by_user_name=asset.updated_by_user.email if asset.updated_by_user else None,
    )


@router.get("", response_model=CustomAssetListResponse)
async def list_custom_assets(
    org_id: UUID,
    type_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
    search: str | None = Query(None, description="Search by display field"),
    sort_by: str | None = Query(None, description="Column to sort by"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    show_disabled: bool = Query(False, description="Include disabled custom assets"),
) -> CustomAssetListResponse:
    """
    List all custom assets for a type within an organization with pagination and search.

    Search is performed on the display_field_key field (or first text field if not set).

    Args:
        org_id: Organization UUID
        type_id: Custom asset type UUID
        current_user: Current authenticated user
        db: Database session
        search: Optional search term for display field
        sort_by: Column to sort by (use "values.fieldkey" for JSONB fields)
        sort_dir: Sort direction ("asc" or "desc")
        limit: Maximum number of results
        offset: Number of results to skip
        show_disabled: Include disabled custom assets

    Returns:
        Paginated list of custom assets (password fields filtered)
    """
    await _verify_org_access(org_id, current_user, db)
    asset_type = await _get_asset_type(type_id, db)
    type_fields = _get_field_definitions(asset_type)

    # Get the display field key for searching
    display_field_key = _get_display_field_key(asset_type)

    repo = CustomAssetRepository(db)
    # Filter by is_enabled: when show_disabled=False, only show enabled (True)
    # When show_disabled=True, show all (None filter)
    is_enabled_filter = None if show_disabled else True
    assets, total = await repo.get_paginated_by_type_and_org(
        type_id,
        org_id,
        search=search,
        search_field_key=display_field_key,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
        is_enabled=is_enabled_filter,
    )

    return CustomAssetListResponse(
        items=[_to_public(a, type_fields) for a in assets],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=CustomAssetPublic, status_code=status.HTTP_201_CREATED)
async def create_custom_asset(
    org_id: UUID,
    type_id: UUID,
    data: CustomAssetCreate,
    current_user: RequireContributor,
    db: DbSession,
) -> CustomAssetPublic:
    """
    Create a new custom asset.

    Args:
        org_id: Organization UUID
        type_id: Custom asset type UUID
        data: Custom asset creation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created custom asset (password fields filtered)
    """
    await _verify_org_access(org_id, current_user, db)
    asset_type = await _get_asset_type(type_id, db)
    type_fields = _get_field_definitions(asset_type)

    # Apply defaults and validate values
    values = apply_default_values(type_fields, data.values)

    try:
        validate_values(type_fields, values, partial=False)
    except CustomAssetValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    # Encrypt password fields
    encrypted_values = encrypt_password_fields(type_fields, values)

    # Create the custom asset
    repo = CustomAssetRepository(db)
    asset = CustomAsset(
        organization_id=org_id,
        custom_asset_type_id=type_id,
        values=encrypted_values,
        metadata_=data.metadata,
        is_enabled=data.is_enabled if data.is_enabled is not None else True,
    )
    asset = await repo.create(asset)

    # Audit log
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.CREATE,
        "custom_asset",
        asset.id,
        actor=current_user,
        organization_id=org_id,
    )

    # Get display name for logging
    display_field_key = _get_display_field_key(asset_type)
    display_name = values.get(display_field_key, str(asset.id)) if display_field_key else str(asset.id)

    logger.info(
        f"Custom asset created: {display_name}",
        extra={
            "org_id": str(org_id),
            "asset_type_id": str(type_id),
            "asset_id": str(asset.id),
            "user_id": str(current_user.user_id),
        },
    )

    # Index for search (async, non-blocking on failure)
    await index_entity_for_search(db, "custom_asset", asset.id, org_id)

    return _to_public(asset, type_fields)


@router.get("/{asset_id}", response_model=CustomAssetPublic)
async def get_custom_asset(
    org_id: UUID,
    type_id: UUID,
    asset_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> CustomAssetPublic:
    """
    Get a custom asset by ID.

    Password field values are excluded from the response.

    Args:
        org_id: Organization UUID
        type_id: Custom asset type UUID
        asset_id: Custom asset UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Custom asset details (password fields filtered)
    """
    await _verify_org_access(org_id, current_user, db)
    asset_type = await _get_asset_type(type_id, db)
    type_fields = _get_field_definitions(asset_type)

    repo = CustomAssetRepository(db)
    asset = await repo.get_by_id_type_and_org(asset_id, type_id, org_id)

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom asset not found",
        )

    # Log view (with 60-second dedupe)
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.VIEW,
        "custom_asset",
        asset.id,
        actor=current_user,
        organization_id=org_id,
        dedupe_seconds=60,
    )

    return _to_public(asset, type_fields)


@router.get("/{asset_id}/preview")
async def get_custom_asset_preview(
    org_id: UUID,
    type_id: UUID,
    asset_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> dict:
    """
    Get custom asset preview for search (password fields filtered).

    Returns formatted markdown content suitable for rendering in a preview panel.

    Args:
        org_id: Organization UUID
        type_id: Custom asset type UUID
        asset_id: Custom asset UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Preview data with formatted content (password fields excluded)

    Raises:
        HTTPException: If custom asset not found
    """
    await _verify_org_access(org_id, current_user, db)
    asset_type = await _get_asset_type(type_id, db)
    type_fields = _get_field_definitions(asset_type)

    repo = CustomAssetRepository(db)
    asset = await repo.get_by_id_type_and_org(asset_id, type_id, org_id)

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom asset not found",
        )

    # Get display name
    display_field_key = _get_display_field_key(asset_type)
    display_name = (
        asset.values.get(display_field_key, asset_type.name)
        if display_field_key
        else asset_type.name
    )

    # Build preview content
    content_parts = [f"# {display_name}"]
    content_parts.append(f"\n**Type:** {asset_type.name}")

    # Filter password fields and add visible values
    filtered_values = filter_password_fields(type_fields, asset.values)
    for field in type_fields:
        if field.type == "header":
            continue
        if field.type == "password":
            continue
        value = filtered_values.get(field.key)
        if value is not None and str(value).strip():
            content_parts.append(f"\n**{field.name}:** {value}")

    return {
        "id": str(asset.id),
        "name": display_name,
        "content": "\n".join(content_parts),
        "entity_type": "custom_asset",
        "organization_id": str(org_id),
        "custom_asset_type_id": str(type_id),
    }


@router.get("/{asset_id}/reveal", response_model=CustomAssetReveal)
async def reveal_custom_asset(
    org_id: UUID,
    type_id: UUID,
    asset_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> CustomAssetReveal:
    """
    Get a custom asset with decrypted password fields.

    This endpoint reveals sensitive password field values.

    Args:
        org_id: Organization UUID
        type_id: Custom asset type UUID
        asset_id: Custom asset UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Custom asset details with decrypted password fields
    """
    await _verify_org_access(org_id, current_user, db)
    asset_type = await _get_asset_type(type_id, db)
    type_fields = _get_field_definitions(asset_type)

    repo = CustomAssetRepository(db)
    asset = await repo.get_by_id_type_and_org(asset_id, type_id, org_id)

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom asset not found",
        )

    # Get display name for logging
    display_field_key = _get_display_field_key(asset_type)
    display_name = asset.values.get(display_field_key, str(asset.id)) if display_field_key else str(asset.id)

    logger.info(
        f"Custom asset revealed: {display_name}",
        extra={
            "org_id": str(org_id),
            "asset_type_id": str(type_id),
            "asset_id": str(asset_id),
            "user_id": str(current_user.user_id),
        },
    )

    return _to_reveal(asset, type_fields)


@router.put("/{asset_id}", response_model=CustomAssetPublic)
async def update_custom_asset(
    org_id: UUID,
    type_id: UUID,
    asset_id: UUID,
    data: CustomAssetUpdate,
    current_user: RequireContributor,
    db: DbSession,
) -> CustomAssetPublic:
    """
    Update a custom asset.

    Args:
        org_id: Organization UUID
        type_id: Custom asset type UUID
        asset_id: Custom asset UUID
        data: Custom asset update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated custom asset (password fields filtered)
    """
    await _verify_org_access(org_id, current_user, db)
    asset_type = await _get_asset_type(type_id, db)
    type_fields = _get_field_definitions(asset_type)

    repo = CustomAssetRepository(db)
    asset = await repo.get_by_id_type_and_org(asset_id, type_id, org_id)

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom asset not found",
        )

    # Update metadata if provided
    if data.metadata is not None:
        asset.metadata_ = data.metadata

    # Update is_enabled if provided
    if data.is_enabled is not None:
        asset.is_enabled = data.is_enabled

    # Update values if provided
    if data.values is not None:
        try:
            validate_values(type_fields, data.values, partial=True)
        except CustomAssetValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            ) from e

        # Merge with existing values
        current_values = dict(asset.values)

        # Decrypt existing password fields for merging
        decrypted_current = decrypt_password_fields(type_fields, current_values)

        # Update with new values
        decrypted_current.update(data.values)

        # Re-encrypt password fields
        encrypted_values = encrypt_password_fields(type_fields, decrypted_current)
        asset.values = encrypted_values

    # Track who updated
    asset.updated_by_user_id = current_user.user_id

    asset = await repo.update(asset)

    # Audit log
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.UPDATE,
        "custom_asset",
        asset.id,
        actor=current_user,
        organization_id=org_id,
    )

    # Get display name for logging
    display_field_key = _get_display_field_key(asset_type)
    display_name = asset.values.get(display_field_key, str(asset.id)) if display_field_key else str(asset.id)

    logger.info(
        f"Custom asset updated: {display_name}",
        extra={
            "org_id": str(org_id),
            "asset_type_id": str(type_id),
            "asset_id": str(asset_id),
            "user_id": str(current_user.user_id),
        },
    )

    # Update search index (async, non-blocking on failure)
    await index_entity_for_search(db, "custom_asset", asset_id, org_id)

    return _to_public(asset, type_fields)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_asset(
    org_id: UUID,
    type_id: UUID,
    asset_id: UUID,
    current_user: RequireContributor,
    db: DbSession,
) -> None:
    """
    Delete a custom asset.

    Args:
        org_id: Organization UUID
        type_id: Custom asset type UUID
        asset_id: Custom asset UUID
        current_user: Current authenticated user
        db: Database session
    """
    await _verify_org_access(org_id, current_user, db)
    await _get_asset_type(type_id, db)

    repo = CustomAssetRepository(db)
    asset = await repo.get_by_id_type_and_org(asset_id, type_id, org_id)

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom asset not found",
        )

    # Audit log (before delete)
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.DELETE,
        "custom_asset",
        asset_id,
        actor=current_user,
        organization_id=org_id,
    )

    # Get display name for logging before deletion
    asset_type = await _get_asset_type(type_id, db)
    display_field_key = _get_display_field_key(asset_type)
    display_name = asset.values.get(display_field_key, str(asset.id)) if display_field_key else str(asset.id)

    await repo.delete(asset)

    # Remove from search index (async, non-blocking on failure)
    await remove_entity_from_search(db, "custom_asset", asset_id)

    logger.info(
        f"Custom asset deleted: {display_name}",
        extra={
            "org_id": str(org_id),
            "asset_type_id": str(type_id),
            "asset_id": str(asset_id),
            "user_id": str(current_user.user_id),
        },
    )


@router.patch("/batch/toggle", response_model=BatchToggleResponse)
async def batch_toggle_custom_assets(
    org_id: UUID,
    type_id: UUID,
    request: BatchToggleRequest,
    current_user: RequireContributor,
    db: DbSession,
) -> BatchToggleResponse:
    """
    Batch activate/deactivate custom assets.

    Args:
        org_id: Organization UUID
        type_id: Custom asset type UUID
        request: Batch toggle request with IDs and new is_enabled value
        current_user: Current authenticated user
        db: Database session

    Returns:
        Number of custom assets updated
    """
    await _verify_org_access(org_id, current_user, db)
    await _get_asset_type(type_id, db)

    # Convert string IDs to UUIDs
    asset_ids = [UUID(id_str) for id_str in request.ids]

    # Batch update
    result = await db.execute(
        update(CustomAsset)
        .where(CustomAsset.id.in_(asset_ids))
        .where(CustomAsset.custom_asset_type_id == type_id)
        .where(CustomAsset.organization_id == org_id)
        .values(is_enabled=request.is_enabled)
    )
    await db.commit()

    logger.info(
        f"Batch toggle custom assets: {result.rowcount} assets set to is_enabled={request.is_enabled}",
        extra={
            "org_id": str(org_id),
            "asset_type_id": str(type_id),
            "user_id": str(current_user.user_id),
            "updated_count": result.rowcount,
        },
    )

    # Update search index for each affected custom asset
    # The worker will index if enabled, remove from index if disabled
    for asset_id in asset_ids:
        await index_entity_for_search(db, "custom_asset", asset_id, org_id)

    return BatchToggleResponse(updated_count=result.rowcount)
