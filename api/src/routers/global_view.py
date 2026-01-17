"""
Global View Router

Provides read-only endpoints for viewing data across all organizations.
Used by MSP users to see a unified view of all client data.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from src.core.auth import CurrentActiveUser
from src.core.database import DbSession
from src.models.contracts.custom_asset import FieldDefinition
from src.models.orm.configuration import Configuration
from src.models.orm.custom_asset import CustomAsset
from src.models.orm.document import Document
from src.models.orm.location import Location
from src.models.orm.password import Password
from src.repositories.configuration import ConfigurationRepository
from src.repositories.configuration_type import ConfigurationTypeRepository
from src.repositories.custom_asset_type import CustomAssetTypeRepository
from src.repositories.document import DocumentRepository
from src.repositories.location import LocationRepository
from src.repositories.password import PasswordRepository
from src.services.custom_asset_validation import filter_password_fields

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/global", tags=["global"])


# =============================================================================
# Response Models with organization_name field
# =============================================================================


class GlobalPasswordPublic(BaseModel):
    """Password response with organization info for global view."""

    id: str
    organization_id: str
    organization_name: str
    name: str
    username: str | None
    url: str | None
    notes: str | None
    has_totp: bool = False
    created_at: str
    updated_at: str


class GlobalPasswordListResponse(BaseModel):
    """Paginated response for global password list."""

    items: list[GlobalPasswordPublic]
    total: int
    limit: int
    offset: int


class GlobalConfigurationPublic(BaseModel):
    """Configuration response with organization info for global view."""

    id: str
    organization_id: str
    organization_name: str
    configuration_type_id: str | None
    configuration_status_id: str | None
    name: str
    serial_number: str | None
    asset_tag: str | None
    manufacturer: str | None
    model: str | None
    ip_address: str | None
    mac_address: str | None
    notes: str | None
    created_at: str
    updated_at: str
    configuration_type_name: str | None
    configuration_status_name: str | None


class GlobalConfigurationListResponse(BaseModel):
    """Paginated response for global configuration list."""

    items: list[GlobalConfigurationPublic]
    total: int
    limit: int
    offset: int


class GlobalLocationPublic(BaseModel):
    """Location response with organization info for global view."""

    id: str
    organization_id: str
    organization_name: str
    name: str
    notes: str | None
    created_at: str
    updated_at: str


class GlobalLocationListResponse(BaseModel):
    """Paginated response for global location list."""

    items: list[GlobalLocationPublic]
    total: int
    limit: int
    offset: int


class GlobalDocumentPublic(BaseModel):
    """Document response with organization info for global view."""

    id: str
    organization_id: str
    organization_name: str
    path: str
    name: str
    content: str
    created_at: str
    updated_at: str


class GlobalDocumentListResponse(BaseModel):
    """Paginated response for global document list."""

    items: list[GlobalDocumentPublic]
    total: int
    limit: int
    offset: int


class GlobalCustomAssetPublic(BaseModel):
    """Custom asset response with organization info for global view."""

    id: str
    organization_id: str
    organization_name: str
    custom_asset_type_id: str
    values: dict
    is_enabled: bool
    created_at: str
    updated_at: str


class GlobalCustomAssetListResponse(BaseModel):
    """Paginated response for global custom asset list."""

    items: list[GlobalCustomAssetPublic]
    total: int
    limit: int
    offset: int


class GlobalSidebarItemCount(BaseModel):
    """Count for a sidebar navigation item."""

    id: str
    name: str
    count: int


class GlobalSidebarData(BaseModel):
    """
    Sidebar navigation data for global view.

    Contains aggregated counts across ALL organizations.
    """

    # Core entity counts (aggregated)
    passwords_count: int
    locations_count: int
    documents_count: int

    # Dynamic types with counts (aggregated across all orgs)
    configuration_types: list[GlobalSidebarItemCount]
    custom_asset_types: list[GlobalSidebarItemCount]


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/passwords", response_model=GlobalPasswordListResponse)
async def list_global_passwords(
    _current_user: CurrentActiveUser,
    db: DbSession,
    search: str | None = Query(None, description="Search by name, username, url, or notes"),
    sort_by: str | None = Query(None, description="Column to sort by"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
) -> GlobalPasswordListResponse:
    """
    List all passwords across all organizations with pagination and search.

    Args:
        current_user: Current authenticated user
        db: Database session
        search: Optional search term
        sort_by: Column to sort by
        sort_dir: Sort direction ("asc" or "desc")
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        Paginated list of passwords with organization info
    """
    password_repo = PasswordRepository(db)

    # Get paginated results without org filter
    passwords, total = await password_repo.get_paginated(
        filters=[],  # No org filter for global view
        search_columns=password_repo.SEARCH_COLUMNS,
        search_term=search,
        sort_by=sort_by or "name",
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
        options=[joinedload(Password.organization)],
    )

    items = [
        GlobalPasswordPublic(
            id=str(p.id),
            organization_id=str(p.organization_id),
            organization_name=p.organization.name if p.organization else "Unknown",
            name=p.name,
            username=p.username,
            url=p.url,
            notes=p.notes,
            has_totp=bool(p.totp_secret_encrypted),
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in passwords
    ]

    return GlobalPasswordListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/configurations", response_model=GlobalConfigurationListResponse)
async def list_global_configurations(
    _current_user: CurrentActiveUser,
    db: DbSession,
    type_id: UUID | None = Query(None, alias="configuration_type_id"),
    status_id: UUID | None = Query(None, alias="configuration_status_id"),
    search: str | None = Query(None, description="Search configurations"),
    sort_by: str | None = Query(None, description="Column to sort by"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
) -> GlobalConfigurationListResponse:
    """
    List all configurations across all organizations with pagination and search.

    Args:
        current_user: Current authenticated user
        db: Database session
        type_id: Optional filter by configuration type
        status_id: Optional filter by configuration status
        search: Optional search term
        sort_by: Column to sort by
        sort_dir: Sort direction ("asc" or "desc")
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        Paginated list of configurations with organization info
    """
    config_repo = ConfigurationRepository(db)

    # Build filters (no org filter for global view)
    filters = []
    if type_id is not None:
        filters.append(Configuration.configuration_type_id == type_id)
    if status_id is not None:
        filters.append(Configuration.configuration_status_id == status_id)

    configs, total = await config_repo.get_paginated(
        filters=filters,
        search_columns=config_repo.SEARCH_COLUMNS,
        search_term=search,
        sort_by=sort_by or "name",
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
        options=[
            joinedload(Configuration.configuration_type),
            joinedload(Configuration.configuration_status),
            joinedload(Configuration.organization),
        ],
    )

    items = [
        GlobalConfigurationPublic(
            id=str(c.id),
            organization_id=str(c.organization_id),
            organization_name=c.organization.name if c.organization else "Unknown",
            configuration_type_id=str(c.configuration_type_id) if c.configuration_type_id else None,
            configuration_status_id=str(c.configuration_status_id) if c.configuration_status_id else None,
            name=c.name,
            serial_number=c.serial_number,
            asset_tag=c.asset_tag,
            manufacturer=c.manufacturer,
            model=c.model,
            ip_address=c.ip_address,
            mac_address=c.mac_address,
            notes=c.notes,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
            configuration_type_name=c.configuration_type.name if c.configuration_type else None,
            configuration_status_name=c.configuration_status.name if c.configuration_status else None,
        )
        for c in configs
    ]

    return GlobalConfigurationListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/locations", response_model=GlobalLocationListResponse)
async def list_global_locations(
    _current_user: CurrentActiveUser,
    db: DbSession,
    search: str | None = Query(None, description="Search by name or notes"),
    sort_by: str | None = Query(None, description="Column to sort by"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
) -> GlobalLocationListResponse:
    """
    List all locations across all organizations with pagination and search.

    Args:
        current_user: Current authenticated user
        db: Database session
        search: Optional search term
        sort_by: Column to sort by
        sort_dir: Sort direction ("asc" or "desc")
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        Paginated list of locations with organization info
    """
    location_repo = LocationRepository(db)

    locations, total = await location_repo.get_paginated(
        filters=[],  # No org filter for global view
        search_columns=location_repo.SEARCH_COLUMNS,
        search_term=search,
        sort_by=sort_by or "name",
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
        options=[joinedload(Location.organization)],
    )

    items = [
        GlobalLocationPublic(
            id=str(loc.id),
            organization_id=str(loc.organization_id),
            organization_name=loc.organization.name if loc.organization else "Unknown",
            name=loc.name,
            notes=loc.notes,
            created_at=loc.created_at.isoformat(),
            updated_at=loc.updated_at.isoformat(),
        )
        for loc in locations
    ]

    return GlobalLocationListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/documents", response_model=GlobalDocumentListResponse)
async def list_global_documents(
    _current_user: CurrentActiveUser,
    db: DbSession,
    path: str | None = Query(None, description="Filter by folder path"),
    search: str | None = Query(None, description="Search by name, path, or content"),
    sort_by: str | None = Query(None, description="Column to sort by"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
) -> GlobalDocumentListResponse:
    """
    List all documents across all organizations with pagination and search.

    Args:
        current_user: Current authenticated user
        db: Database session
        path: Optional folder path filter
        search: Optional search term
        sort_by: Column to sort by
        sort_dir: Sort direction ("asc" or "desc")
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        Paginated list of documents with organization info
    """
    doc_repo = DocumentRepository(db)

    # Build filters (no org filter for global view)
    filters = []
    if path is not None:
        filters.append(Document.path == path)

    documents, total = await doc_repo.get_paginated(
        filters=filters,
        search_columns=doc_repo.SEARCH_COLUMNS,
        search_term=search,
        sort_by=sort_by or "name",
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
        options=[joinedload(Document.organization)],
    )

    items = [
        GlobalDocumentPublic(
            id=str(doc.id),
            organization_id=str(doc.organization_id),
            organization_name=doc.organization.name if doc.organization else "Unknown",
            path=doc.path,
            name=doc.name,
            content=doc.content,
            created_at=doc.created_at.isoformat(),
            updated_at=doc.updated_at.isoformat(),
        )
        for doc in documents
    ]

    return GlobalDocumentListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/custom-assets", response_model=GlobalCustomAssetListResponse)
async def list_global_custom_assets(
    _current_user: CurrentActiveUser,
    db: DbSession,
    type_id: UUID = Query(..., alias="type_id", description="Custom asset type ID"),
    search: str | None = Query(None, description="Search by name"),
    sort_by: str | None = Query(None, description="Column to sort by"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
) -> GlobalCustomAssetListResponse:
    """
    List all custom assets of a specific type across all organizations.

    Args:
        current_user: Current authenticated user
        db: Database session
        type_id: Custom asset type ID (required)
        search: Optional search term for name
        sort_by: Column to sort by
        sort_dir: Sort direction ("asc" or "desc")
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        Paginated list of custom assets with organization info
    """
    # Get the asset type for field definitions
    type_repo = CustomAssetTypeRepository(db)
    asset_type = await type_repo.get_by_id(type_id)
    if not asset_type:
        return GlobalCustomAssetListResponse(
            items=[],
            total=0,
            limit=limit,
            offset=offset,
        )

    type_fields = [FieldDefinition(**f) for f in asset_type.fields]

    # Get display field key for search (similar to custom_assets router)
    display_field_key = asset_type.display_field_key
    if not display_field_key:
        # Fall back to first text/textbox field, then first non-header field
        non_header_fields = [f for f in type_fields if f.type != "header"]
        for field in non_header_fields:
            if field.type in ("text", "textbox"):
                display_field_key = field.key
                break
        if not display_field_key and non_header_fields:
            display_field_key = non_header_fields[0].key

    # Build query with JSONB search - note: we can't use get_paginated for JSONB search
    # so we use a custom query similar to the custom_assets router
    query = select(CustomAsset).where(CustomAsset.custom_asset_type_id == type_id)
    count_query = select(func.count(CustomAsset.id)).where(
        CustomAsset.custom_asset_type_id == type_id
    )

    # Search within JSONB values field
    if search and display_field_key:
        search_condition = CustomAsset.values[display_field_key].astext.ilike(f"%{search}%")
        query = query.where(search_condition)
        count_query = count_query.where(search_condition)

    # Sort by JSONB field if sort_by starts with "values." or default to created_at
    if sort_by:
        if sort_by.startswith("values."):
            jsonb_key = sort_by[7:]  # Remove "values." prefix
            if sort_dir == "desc":
                query = query.order_by(CustomAsset.values[jsonb_key].astext.desc())
            else:
                query = query.order_by(CustomAsset.values[jsonb_key].astext.asc())
        elif hasattr(CustomAsset, sort_by):
            from sqlalchemy import asc, desc
            order_func = desc if sort_dir == "desc" else asc
            query = query.order_by(order_func(getattr(CustomAsset, sort_by)))
    else:
        query = query.order_by(CustomAsset.created_at.desc())

    # Add joinedload for organization
    query = query.options(joinedload(CustomAsset.organization))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    assets = list(result.unique().scalars().all())

    items = [
        GlobalCustomAssetPublic(
            id=str(asset.id),
            organization_id=str(asset.organization_id),
            organization_name=asset.organization.name if asset.organization else "Unknown",
            custom_asset_type_id=str(asset.custom_asset_type_id),
            values=filter_password_fields(type_fields, asset.values),
            is_enabled=asset.is_enabled,
            created_at=asset.created_at.isoformat(),
            updated_at=asset.updated_at.isoformat(),
        )
        for asset in assets
    ]

    return GlobalCustomAssetListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/sidebar", response_model=GlobalSidebarData)
async def get_global_sidebar_data(
    _current_user: CurrentActiveUser,
    db: DbSession,
) -> GlobalSidebarData:
    """
    Get sidebar navigation data aggregated across ALL organizations.

    Returns counts for all entity types across all orgs:
    - Core entities (passwords, locations, documents)
    - Configuration types with total configuration counts
    - Custom asset types with total asset counts

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Sidebar data with aggregated counts
    """
    # Get aggregated core entity counts
    password_count_result = await db.execute(select(func.count(Password.id)))
    passwords_count = password_count_result.scalar_one()

    location_count_result = await db.execute(select(func.count(Location.id)))
    locations_count = location_count_result.scalar_one()

    document_count_result = await db.execute(select(func.count(Document.id)))
    documents_count = document_count_result.scalar_one()

    # Get configuration types with aggregated counts
    config_type_repo = ConfigurationTypeRepository(db)
    config_types = await config_type_repo.get_all_ordered()

    configuration_types = []
    for ct in config_types:
        count_result = await db.execute(
            select(func.count(Configuration.id)).where(
                Configuration.configuration_type_id == ct.id
            )
        )
        count = count_result.scalar_one()
        configuration_types.append(
            GlobalSidebarItemCount(id=str(ct.id), name=ct.name, count=count)
        )

    # Get custom asset types with aggregated counts
    asset_type_repo = CustomAssetTypeRepository(db)
    asset_types = await asset_type_repo.get_all_ordered()

    custom_asset_types = []
    for at in asset_types:
        count_result = await db.execute(
            select(func.count(CustomAsset.id)).where(
                CustomAsset.custom_asset_type_id == at.id
            )
        )
        count = count_result.scalar_one()
        custom_asset_types.append(
            GlobalSidebarItemCount(id=str(at.id), name=at.name, count=count)
        )

    return GlobalSidebarData(
        passwords_count=passwords_count,
        locations_count=locations_count,
        documents_count=documents_count,
        configuration_types=configuration_types,
        custom_asset_types=custom_asset_types,
    )
