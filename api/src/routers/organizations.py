"""
Organizations Router

Provides CRUD endpoints for organizations.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.core.auth import CurrentActiveUser, RequireAdmin
from src.core.database import DbSession
from src.models.contracts.organization import (
    OrganizationCreate,
    OrganizationPublic,
    OrganizationUpdate,
    OrganizationWithFrequent,
    SidebarData,
    SidebarItemCount,
)
from src.models.enums import AuditAction
from src.models.orm.organization import Organization
from src.repositories.access_tracking import AccessTrackingRepository
from src.repositories.configuration import ConfigurationRepository
from src.repositories.configuration_type import ConfigurationTypeRepository
from src.repositories.custom_asset import CustomAssetRepository
from src.repositories.custom_asset_type import CustomAssetTypeRepository
from src.repositories.document import DocumentRepository
from src.repositories.location import LocationRepository
from src.repositories.organization import OrganizationRepository
from src.repositories.password import PasswordRepository
from src.services.audit_service import get_audit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


@router.get("", response_model=list[OrganizationPublic])
async def list_organizations(
    current_user: CurrentActiveUser,
    db: DbSession,
    show_disabled: bool = False,
) -> list[OrganizationPublic]:
    """
    List all organizations.

    V1 is MSP-only, so all authenticated users can see all organizations.

    Args:
        current_user: Current authenticated user
        db: Database session
        show_disabled: Include disabled organizations in results

    Returns:
        List of all organizations
    """
    org_repo = OrganizationRepository(db)
    # Filter by is_enabled: when show_disabled=False, only show enabled (True)
    # When show_disabled=True, show all (None filter)
    is_enabled_filter = None if show_disabled else True
    organizations = await org_repo.get_all(is_enabled=is_enabled_filter)

    return [
        OrganizationPublic(
            id=str(org.id),
            name=org.name,
            metadata=org.metadata_ if isinstance(org.metadata_, dict) else {},
            is_enabled=org.is_enabled,
            created_at=org.created_at,
            updated_at=org.updated_at,
            updated_by_user_id=str(org.updated_by_user_id) if org.updated_by_user_id else None,
            updated_by_user_name=org.updated_by_user.email if org.updated_by_user else None,
        )
        for org in organizations
    ]


@router.post("", response_model=OrganizationPublic, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: RequireAdmin,
    db: DbSession,
) -> OrganizationPublic:
    """
    Create a new organization.

    Args:
        org_data: Organization creation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created organization
    """
    org_repo = OrganizationRepository(db)

    # Create organization (default is_enabled to True if not provided)
    org = Organization(
        name=org_data.name,
        metadata_=org_data.metadata,
        is_enabled=org_data.is_enabled if org_data.is_enabled is not None else True
    )
    org = await org_repo.create(org)

    # Audit log (use org.id as organization_id since it's the org being created)
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.CREATE,
        "organization",
        org.id,
        actor=current_user,
        organization_id=org.id,
    )

    logger.info(
        f"Organization created: {org.name}",
        extra={"org_id": str(org.id), "user_id": str(current_user.user_id)},
    )

    return OrganizationPublic(
        id=str(org.id),
        name=org.name,
        metadata=org.metadata_ if isinstance(org.metadata_, dict) else {},
        is_enabled=org.is_enabled,
        created_at=org.created_at,
        updated_at=org.updated_at,
        updated_by_user_id=str(org.updated_by_user_id) if org.updated_by_user_id else None,
        updated_by_user_name=org.updated_by_user.email if org.updated_by_user else None,
    )


@router.get("/{org_id}", response_model=OrganizationWithFrequent)
async def get_organization(
    org_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
    include: list[str] = Query(
        default=[], description="Include additional data: frequently_accessed"
    ),
) -> OrganizationWithFrequent:
    """
    Get organization by ID.

    V1 is MSP-only, so all authenticated users can view any organization.

    Args:
        org_id: Organization UUID
        current_user: Current authenticated user
        db: Database session
        include: Optional list of additional data to include (e.g., frequently_accessed)

    Returns:
        Organization details with optional frequently accessed entities

    Raises:
        HTTPException: If organization not found
    """
    org_repo = OrganizationRepository(db)

    org = await org_repo.get_by_id(org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Log view (with 60-second dedupe)
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.VIEW,
        "organization",
        org.id,
        actor=current_user,
        organization_id=org.id,
        dedupe_seconds=60,
    )

    # Build response with optional frequently_accessed
    frequently_accessed = None
    if "frequently_accessed" in include:
        access_repo = AccessTrackingRepository(db)
        frequently_accessed = await access_repo.get_frequently_accessed(
            org_id, limit=6, days=30
        )

    return OrganizationWithFrequent(
        id=str(org.id),
        name=org.name,
        metadata=org.metadata_ if isinstance(org.metadata_, dict) else {},
        is_enabled=org.is_enabled,
        created_at=org.created_at,
        updated_at=org.updated_at,
        updated_by_user_id=str(org.updated_by_user_id) if org.updated_by_user_id else None,
        updated_by_user_name=org.updated_by_user.email if org.updated_by_user else None,
        frequently_accessed=frequently_accessed,
    )


@router.put("/{org_id}", response_model=OrganizationPublic)
async def update_organization(
    org_id: UUID,
    org_data: OrganizationUpdate,
    current_user: RequireAdmin,
    db: DbSession,
) -> OrganizationPublic:
    """
    Update organization.

    V1 is MSP-only, so all authenticated users can update any organization.

    Args:
        org_id: Organization UUID
        org_data: Organization update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated organization

    Raises:
        HTTPException: If organization not found
    """
    org_repo = OrganizationRepository(db)

    org = await org_repo.get_by_id(org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Update fields
    if org_data.name is not None:
        org.name = org_data.name
    if org_data.metadata is not None:
        org.metadata_ = org_data.metadata
    if org_data.is_enabled is not None:
        org.is_enabled = org_data.is_enabled

    # Track who updated
    org.updated_by_user_id = current_user.user_id

    org = await org_repo.update(org)

    # Audit log
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.UPDATE,
        "organization",
        org.id,
        actor=current_user,
        organization_id=org_id,
    )

    logger.info(
        f"Organization updated: {org.name}",
        extra={"org_id": str(org.id), "user_id": str(current_user.user_id)},
    )

    return OrganizationPublic(
        id=str(org.id),
        name=org.name,
        metadata=org.metadata_ if isinstance(org.metadata_, dict) else {},
        is_enabled=org.is_enabled,
        created_at=org.created_at,
        updated_at=org.updated_at,
        updated_by_user_id=str(org.updated_by_user_id) if org.updated_by_user_id else None,
        updated_by_user_name=org.updated_by_user.email if org.updated_by_user else None,
    )


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: UUID,
    current_user: RequireAdmin,
    db: DbSession,
) -> None:
    """
    Delete organization.

    Requires administrator role or higher.

    Args:
        org_id: Organization UUID
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If organization not found or user not authorized
    """

    org_repo = OrganizationRepository(db)

    org = await org_repo.get_by_id(org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Audit log (before delete)
    audit_service = get_audit_service(db)
    await audit_service.log(
        AuditAction.DELETE,
        "organization",
        org_id,
        actor=current_user,
        organization_id=org_id,
    )

    await org_repo.delete(org)

    logger.info(
        f"Organization deleted: {org.name}",
        extra={"org_id": str(org.id), "user_id": str(current_user.user_id)},
    )


@router.get("/{org_id}/sidebar", response_model=SidebarData)
async def get_sidebar_data(
    org_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> SidebarData:
    """
    Get sidebar navigation data for an organization.

    Returns counts for all entity types:
    - Core entities (passwords, locations, documents)
    - Configuration types with configuration counts
    - Custom asset types with asset counts

    Args:
        org_id: Organization UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Sidebar data with counts
    """
    # Get core entity counts
    password_repo = PasswordRepository(db)
    location_repo = LocationRepository(db)
    document_repo = DocumentRepository(db)

    passwords_count = await password_repo.count_by_organization(org_id)
    locations_count = await location_repo.count_by_organization(org_id)
    documents_count = await document_repo.count_by_organization(org_id)

    # Get configuration types with their configuration counts (types are global)
    config_type_repo = ConfigurationTypeRepository(db)
    config_repo = ConfigurationRepository(db)
    config_types = await config_type_repo.get_all_ordered()

    configuration_types = []
    for ct in config_types:
        count = await config_repo.count_by_type_and_organization(ct.id, org_id)
        configuration_types.append(
            SidebarItemCount(id=str(ct.id), name=ct.name, count=count)
        )

    # Get custom asset types with their asset counts (types are global)
    asset_type_repo = CustomAssetTypeRepository(db)
    asset_repo = CustomAssetRepository(db)
    asset_types = await asset_type_repo.get_all_ordered()

    custom_asset_types = []
    for at in asset_types:
        count = await asset_repo.count_by_type_and_organization(at.id, org_id)
        custom_asset_types.append(
            SidebarItemCount(id=str(at.id), name=at.name, count=count)
        )

    return SidebarData(
        passwords_count=passwords_count,
        locations_count=locations_count,
        documents_count=documents_count,
        configuration_types=configuration_types,
        custom_asset_types=custom_asset_types,
    )
