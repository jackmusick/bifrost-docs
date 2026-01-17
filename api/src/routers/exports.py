"""
Exports Router

Provides endpoints for data export operations:
- Create export job
- List user's exports
- Download export (get presigned URL)
- Revoke export
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import CurrentActiveUser, RequireAdmin
from src.core.database import get_db
from src.models.orm.export import Export, ExportStatus
from src.repositories.export import ExportRepository
from src.services.file_storage import get_file_storage_service

router = APIRouter(prefix="/api/exports", tags=["exports"])


# =============================================================================
# Request/Response Schemas
# =============================================================================


class CreateExportRequest(BaseModel):
    """Request to create a new data export."""

    organization_ids: list[UUID] | None = Field(
        default=None,
        description="List of organization IDs to export. None means all organizations.",
    )
    expires_in_days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Number of days until the export expires (1-30).",
    )


class ExportResponse(BaseModel):
    """Response containing export details."""

    id: UUID
    user_id: UUID
    organization_ids: list[str] | None
    status: str
    s3_key: str | None
    file_size_bytes: int | None
    expires_at: datetime
    revoked_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DownloadUrlResponse(BaseModel):
    """Response containing presigned download URL."""

    download_url: str
    expires_in_seconds: int


class RevokeResponse(BaseModel):
    """Response confirming export revocation."""

    revoked: bool
    revoked_at: datetime


# =============================================================================
# Helper Functions
# =============================================================================


def export_to_response(export: Export) -> ExportResponse:
    """Convert Export ORM model to response schema."""
    return ExportResponse(
        id=export.id,
        user_id=export.user_id,
        organization_ids=export.organization_ids,
        status=export.status.value if isinstance(export.status, ExportStatus) else export.status,
        s3_key=export.s3_key,
        file_size_bytes=export.file_size_bytes,
        expires_at=export.expires_at,
        revoked_at=export.revoked_at,
        error_message=export.error_message,
        created_at=export.created_at,
        updated_at=export.updated_at,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.post("", response_model=ExportResponse, status_code=status.HTTP_201_CREATED)
async def create_export(
    request: CreateExportRequest,
    background_tasks: BackgroundTasks,
    user: RequireAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExportResponse:
    """
    Create a new data export job.

    Only administrators can create exports. The export will be processed
    in the background and progress will be streamed via WebSocket.

    Args:
        request: Export configuration
        background_tasks: FastAPI background tasks
        user: Authenticated admin user
        db: Database session

    Returns:
        Created export record
    """
    # Import here to avoid circular imports
    from src.services.export_service import process_export

    repo = ExportRepository(db)

    # Convert UUID list to string list for JSONB storage
    org_ids_str = [str(org_id) for org_id in request.organization_ids] if request.organization_ids else None

    export = Export(
        user_id=user.user_id,
        organization_ids=org_ids_str,
        status=ExportStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(days=request.expires_in_days),
    )

    created_export = await repo.create(export)
    await db.commit()
    await db.refresh(created_export)

    # Queue background job to process the export
    background_tasks.add_task(process_export, created_export.id)

    return export_to_response(created_export)


@router.get("", response_model=list[ExportResponse])
async def list_exports(
    user: CurrentActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
    offset: int = 0,
) -> list[ExportResponse]:
    """
    List all exports for the current user.

    Args:
        user: Authenticated user
        db: Database session
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        List of user's exports
    """
    repo = ExportRepository(db)
    exports = await repo.get_by_user(user.user_id, limit=limit, offset=offset)
    return [export_to_response(e) for e in exports]


@router.get("/{export_id}", response_model=ExportResponse)
async def get_export(
    export_id: UUID,
    user: CurrentActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExportResponse:
    """
    Get a specific export by ID.

    Args:
        export_id: Export UUID
        user: Authenticated user
        db: Database session

    Returns:
        Export details

    Raises:
        HTTPException: If export not found or not owned by user
    """
    repo = ExportRepository(db)
    export = await repo.get_by_id_and_user(export_id, user.user_id)

    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found",
        )

    return export_to_response(export)


@router.get("/{export_id}/download", response_model=DownloadUrlResponse)
async def download_export(
    export_id: UUID,
    user: CurrentActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DownloadUrlResponse:
    """
    Get a presigned download URL for an export.

    The export must be completed, not revoked, and not expired.

    Args:
        export_id: Export UUID
        user: Authenticated user
        db: Database session

    Returns:
        Presigned download URL with expiration

    Raises:
        HTTPException: If export not found, not ready, revoked, or expired
    """
    repo = ExportRepository(db)
    export = await repo.get_by_id_and_user(export_id, user.user_id)

    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found",
        )

    if export.revoked_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Export has been revoked",
        )

    if export.expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Export has expired",
        )

    export_status = export.status if isinstance(export.status, str) else export.status.value
    if export_status != ExportStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Export not ready. Current status: {export_status}",
        )

    if not export.s3_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Export completed but no file available",
        )

    # Generate presigned URL (valid for 1 hour)
    expires_in_seconds = 3600
    file_storage = get_file_storage_service()
    download_url = await file_storage.generate_download_url(
        export.s3_key,
        filename=f"export-{export.id}.zip",
        expires_in=expires_in_seconds,
    )

    return DownloadUrlResponse(
        download_url=download_url,
        expires_in_seconds=expires_in_seconds,
    )


@router.delete("/{export_id}", response_model=RevokeResponse)
async def revoke_export(
    export_id: UUID,
    user: CurrentActiveUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RevokeResponse:
    """
    Revoke an export, making it unavailable for download.

    The actual file in S3 is not deleted immediately but will be
    cleaned up by a scheduled job.

    Args:
        export_id: Export UUID
        user: Authenticated user
        db: Database session

    Returns:
        Revocation confirmation

    Raises:
        HTTPException: If export not found or not owned by user
    """
    repo = ExportRepository(db)
    export = await repo.get_by_id_and_user(export_id, user.user_id)

    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found",
        )

    if export.revoked_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Export has already been revoked",
        )

    updated_export = await repo.revoke(export)
    await db.commit()

    return RevokeResponse(
        revoked=True,
        revoked_at=updated_export.revoked_at,  # type: ignore[arg-type]
    )
