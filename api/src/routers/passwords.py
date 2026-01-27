"""
Passwords Router

Provides CRUD endpoints for organization passwords.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import update

from src.core.auth import CurrentActiveUser, RequireContributor
from src.core.database import DbSession
from src.core.security import decrypt_secret, encrypt_secret
from src.models.contracts.common import BatchToggleRequest, BatchToggleResponse
from src.models.contracts.password import (
    PasswordCreate,
    PasswordPublic,
    PasswordReveal,
    PasswordUpdate,
)
from src.models.enums import AuditAction
from src.models.orm.password import Password
from src.repositories.password import PasswordRepository
from src.services.audit_service import get_audit_service
from src.services.search_indexing import index_entity_for_search, remove_entity_from_search


class PasswordListResponse(BaseModel):
    """Paginated response for password list."""

    items: list[PasswordPublic]
    total: int
    limit: int
    offset: int

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/organizations/{org_id}/passwords", tags=["passwords"])


@router.get("", response_model=PasswordListResponse)
async def list_passwords(
    org_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
    search: str | None = Query(None, description="Search by name, username, url, or notes"),
    sort_by: str | None = Query(None, description="Column to sort by"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    show_disabled: bool = Query(False, description="Include disabled passwords"),
) -> PasswordListResponse:
    """
    List all passwords for an organization with pagination and search.

    Args:
        org_id: Organization UUID
        current_user: Current authenticated user
        db: Database session
        search: Optional search term
        sort_by: Column to sort by
        sort_dir: Sort direction ("asc" or "desc")
        limit: Maximum number of results
        offset: Number of results to skip
        show_disabled: Include disabled passwords

    Returns:
        Paginated list of passwords (without password values)
    """
    password_repo = PasswordRepository(db)
    # Filter by is_enabled: when show_disabled=False, only show enabled (True)
    # When show_disabled=True, show all (None filter)
    is_enabled_filter = None if show_disabled else True
    passwords, total = await password_repo.get_paginated_by_org(
        org_id,
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
        is_enabled=is_enabled_filter,
    )

    items = [
        PasswordPublic(
            id=str(p.id),
            organization_id=str(p.organization_id),
            name=p.name,
            username=p.username,
            url=p.url,
            notes=p.notes,
            has_totp=bool(p.totp_secret_encrypted),
            metadata=p.metadata_ if isinstance(p.metadata_, dict) else {},
            is_enabled=p.is_enabled,
            created_at=p.created_at,
            updated_at=p.updated_at,
            updated_by_user_id=str(p.updated_by_user_id) if p.updated_by_user_id else None,
            updated_by_user_name=p.updated_by_user.email if p.updated_by_user else None,
        )
        for p in passwords
    ]

    return PasswordListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=PasswordPublic, status_code=status.HTTP_201_CREATED)
async def create_password(
    org_id: UUID,
    password_data: PasswordCreate,
    current_user: RequireContributor,
    db: DbSession,
) -> PasswordPublic:
    """
    Create a new password entry.

    Args:
        org_id: Organization UUID
        password_data: Password creation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created password (without password value)
    """
    # Encrypt the password before storage
    encrypted_password = encrypt_secret(password_data.password)

    # Encrypt TOTP secret if provided
    encrypted_totp = None
    if password_data.totp_secret:
        encrypted_totp = encrypt_secret(password_data.totp_secret)

    password_repo = PasswordRepository(db)
    password = Password(
        organization_id=org_id,
        name=password_data.name,
        username=password_data.username,
        password_encrypted=encrypted_password,
        totp_secret_encrypted=encrypted_totp,
        url=password_data.url,
        notes=password_data.notes,
        metadata_=password_data.metadata,
        is_enabled=password_data.is_enabled if password_data.is_enabled is not None else True,
    )
    password = await password_repo.create(password)

    # Audit log
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.CREATE,
        "password",
        password.id,
        actor=current_user,
        organization_id=org_id,
    )

    logger.info(
        f"Password created: {password.name}",
        extra={"password_id": str(password.id), "org_id": str(org_id), "user_id": str(current_user.user_id)},
    )

    # Index for search (async, non-blocking on failure)
    await index_entity_for_search(db, "password", password.id, org_id)

    return PasswordPublic(
        id=str(password.id),
        organization_id=str(password.organization_id),
        name=password.name,
        username=password.username,
        url=password.url,
        notes=password.notes,
        has_totp=bool(password.totp_secret_encrypted),
        metadata=password.metadata_ if isinstance(password.metadata_, dict) else {},
        is_enabled=password.is_enabled,
        created_at=password.created_at,
        updated_at=password.updated_at,
        updated_by_user_id=str(password.updated_by_user_id) if password.updated_by_user_id else None,
        updated_by_user_name=password.updated_by_user.email if password.updated_by_user else None,
    )


@router.get("/{password_id}", response_model=PasswordPublic)
async def get_password(
    org_id: UUID,
    password_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> PasswordPublic:
    """
    Get a password by ID (without revealing the password value).

    Args:
        org_id: Organization UUID
        password_id: Password UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Password details (without password value)

    Raises:
        HTTPException: If password not found
    """
    password_repo = PasswordRepository(db)
    password = await password_repo.get_by_id_and_org(password_id, org_id)

    if not password:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Password not found",
        )

    # Log view (with 60-second dedupe)
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.VIEW,
        "password",
        password.id,
        actor=current_user,
        organization_id=org_id,
        dedupe_seconds=60,
    )

    return PasswordPublic(
        id=str(password.id),
        organization_id=str(password.organization_id),
        name=password.name,
        username=password.username,
        url=password.url,
        notes=password.notes,
        has_totp=bool(password.totp_secret_encrypted),
        metadata=password.metadata_ if isinstance(password.metadata_, dict) else {},
        is_enabled=password.is_enabled,
        created_at=password.created_at,
        updated_at=password.updated_at,
        updated_by_user_id=str(password.updated_by_user_id) if password.updated_by_user_id else None,
        updated_by_user_name=password.updated_by_user.email if password.updated_by_user else None,
    )


@router.get("/{password_id}/preview")
async def get_password_preview(
    org_id: UUID,
    password_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> dict:
    """
    Get password preview for search (no actual password value).

    Returns formatted markdown content suitable for rendering in a preview panel.

    Args:
        org_id: Organization UUID
        password_id: Password UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Preview data with formatted content

    Raises:
        HTTPException: If password not found
    """
    password_repo = PasswordRepository(db)
    password = await password_repo.get_by_id_and_org(password_id, org_id)

    if not password:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Password not found",
        )

    # Build preview content without actual password
    content_parts = [f"# {password.name}"]
    if password.username:
        content_parts.append(f"\n**Username:** {password.username}")
    if password.url:
        content_parts.append(f"\n**URL:** {password.url}")
    if password.notes:
        content_parts.append(f"\n## Notes\n{password.notes}")

    return {
        "id": str(password.id),
        "name": password.name,
        "content": "\n".join(content_parts),
        "entity_type": "password",
        "organization_id": str(org_id),
    }


@router.get("/{password_id}/reveal", response_model=PasswordReveal)
async def reveal_password(
    org_id: UUID,
    password_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> PasswordReveal:
    """
    Get a password with the decrypted password value.

    Args:
        org_id: Organization UUID
        password_id: Password UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Password details with decrypted password

    Raises:
        HTTPException: If password not found
    """
    password_repo = PasswordRepository(db)
    password = await password_repo.get_by_id_and_org(password_id, org_id)

    if not password:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Password not found",
        )

    # Decrypt the password
    decrypted_password = decrypt_secret(password.password_encrypted)

    # Decrypt TOTP secret if present
    decrypted_totp = None
    if password.totp_secret_encrypted:
        decrypted_totp = decrypt_secret(password.totp_secret_encrypted)

    # Audit log - sensitive access
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.VIEW,
        "password",
        password.id,
        actor=current_user,
        organization_id=org_id,
    )

    logger.info(
        f"Password revealed: {password.name}",
        extra={"password_id": str(password.id), "org_id": str(org_id), "user_id": str(current_user.user_id)},
    )

    return PasswordReveal(
        id=str(password.id),
        organization_id=str(password.organization_id),
        name=password.name,
        username=password.username,
        url=password.url,
        notes=password.notes,
        has_totp=bool(password.totp_secret_encrypted),
        metadata=password.metadata_ if isinstance(password.metadata_, dict) else {},
        is_enabled=password.is_enabled,
        created_at=password.created_at,
        updated_at=password.updated_at,
        updated_by_user_id=str(password.updated_by_user_id) if password.updated_by_user_id else None,
        updated_by_user_name=password.updated_by_user.email if password.updated_by_user else None,
        password=decrypted_password,
        totp_secret=decrypted_totp,
    )


@router.put("/{password_id}", response_model=PasswordPublic)
async def update_password(
    org_id: UUID,
    password_id: UUID,
    password_data: PasswordUpdate,
    current_user: RequireContributor,
    db: DbSession,
) -> PasswordPublic:
    """
    Update a password entry.

    Args:
        org_id: Organization UUID
        password_id: Password UUID
        password_data: Password update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated password (without password value)

    Raises:
        HTTPException: If password not found
    """
    password_repo = PasswordRepository(db)
    password = await password_repo.get_by_id_and_org(password_id, org_id)

    if not password:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Password not found",
        )

    # Update fields
    if password_data.name is not None:
        password.name = password_data.name
    if password_data.username is not None:
        password.username = password_data.username
    if password_data.password is not None:
        password.password_encrypted = encrypt_secret(password_data.password)
    if password_data.totp_secret is not None:
        password.totp_secret_encrypted = encrypt_secret(password_data.totp_secret)
    if password_data.url is not None:
        password.url = password_data.url
    if password_data.notes is not None:
        password.notes = password_data.notes
    if password_data.metadata is not None:
        password.metadata_ = password_data.metadata
    if password_data.is_enabled is not None:
        password.is_enabled = password_data.is_enabled

    # Track who updated
    password.updated_by_user_id = current_user.user_id

    password = await password_repo.update(password)

    # Audit log
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.UPDATE,
        "password",
        password.id,
        actor=current_user,
        organization_id=org_id,
    )

    logger.info(
        f"Password updated: {password.name}",
        extra={"password_id": str(password.id), "org_id": str(org_id), "user_id": str(current_user.user_id)},
    )

    # Update search index (async, non-blocking on failure)
    await index_entity_for_search(db, "password", password.id, org_id)

    return PasswordPublic(
        id=str(password.id),
        organization_id=str(password.organization_id),
        name=password.name,
        username=password.username,
        url=password.url,
        notes=password.notes,
        has_totp=bool(password.totp_secret_encrypted),
        metadata=password.metadata_ if isinstance(password.metadata_, dict) else {},
        is_enabled=password.is_enabled,
        created_at=password.created_at,
        updated_at=password.updated_at,
        updated_by_user_id=str(password.updated_by_user_id) if password.updated_by_user_id else None,
        updated_by_user_name=password.updated_by_user.email if password.updated_by_user else None,
    )


@router.delete("/{password_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_password(
    org_id: UUID,
    password_id: UUID,
    current_user: RequireContributor,
    db: DbSession,
) -> None:
    """
    Delete a password entry.

    Args:
        org_id: Organization UUID
        password_id: Password UUID
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If password not found
    """
    password_repo = PasswordRepository(db)
    password = await password_repo.get_by_id_and_org(password_id, org_id)

    if not password:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Password not found",
        )

    # Audit log (before delete)
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.DELETE,
        "password",
        password_id,
        actor=current_user,
        organization_id=org_id,
    )

    await password_repo.delete(password)

    # Remove from search index (async, non-blocking on failure)
    await remove_entity_from_search(db, "password", password_id)

    logger.info(
        f"Password deleted: {password.name}",
        extra={"password_id": str(password.id), "org_id": str(org_id), "user_id": str(current_user.user_id)},
    )


@router.patch("/batch", response_model=BatchToggleResponse)
async def batch_toggle_passwords(
    org_id: UUID,
    request: BatchToggleRequest,
    current_user: RequireContributor,
    db: DbSession,
) -> BatchToggleResponse:
    """
    Batch toggle passwords enabled/disabled status.

    Args:
        org_id: Organization UUID
        request: Batch toggle request with IDs and new is_enabled value
        current_user: Current authenticated user
        db: Database session

    Returns:
        Number of passwords updated
    """
    # Convert string IDs to UUIDs
    password_ids = [UUID(id_str) for id_str in request.ids]

    # Batch update
    result = await db.execute(
        update(Password)
        .where(Password.id.in_(password_ids))
        .where(Password.organization_id == org_id)
        .values(is_enabled=request.is_enabled)
    )
    await db.commit()

    logger.info(
        f"Batch toggle passwords: {result.rowcount} passwords set to is_enabled={request.is_enabled}",
        extra={
            "org_id": str(org_id),
            "user_id": str(current_user.user_id),
            "updated_count": result.rowcount,
        },
    )

    # Update search index for each affected password
    # The worker will index if enabled, remove from index if disabled
    for password_id in password_ids:
        await index_entity_for_search(db, "password", password_id, org_id)

    return BatchToggleResponse(updated_count=result.rowcount)
