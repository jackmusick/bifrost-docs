"""
Attachments Router

Provides endpoints for file attachments including:
- Upload (presigned URL generation)
- Download (presigned URL generation)
- List attachments for entities
- Delete attachments
- Document image uploads for markdown embedding
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from src.config import get_settings
from src.core.auth import CurrentActiveUser, RequireContributor
from src.core.database import DbSession
from src.models.contracts.attachment import (
    AttachmentCreate,
    AttachmentDownloadResponse,
    AttachmentList,
    AttachmentPublic,
    AttachmentUploadResponse,
    DocumentImageCreate,
    DocumentImageUploadResponse,
)
from src.models.enums import EntityType
from src.models.orm.attachment import Attachment
from src.repositories.attachment import AttachmentRepository
from src.services.file_storage import get_file_storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/organizations/{org_id}", tags=["attachments"])


@router.get("/attachments", response_model=AttachmentList)
async def list_attachments(
    org_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
    entity_type: EntityType | None = Query(None, description="Filter by entity type"),
    entity_id: UUID | None = Query(None, description="Filter by entity ID"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> AttachmentList:
    """
    List attachments for an organization.

    Can filter by entity_type and entity_id to get attachments for a specific entity.

    Args:
        org_id: Organization UUID
        current_user: Current authenticated user
        db: Database session
        entity_type: Optional entity type filter
        entity_id: Optional entity ID filter (requires entity_type)
        limit: Maximum results (1-1000)
        offset: Results to skip

    Returns:
        List of attachments with total count
    """
    repo = AttachmentRepository(db)

    if entity_type and entity_id:
        attachments = await repo.get_by_entity(
            organization_id=org_id,
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit,
            offset=offset,
        )
        total = await repo.count_by_entity(org_id, entity_type, entity_id)
    else:
        attachments = await repo.get_all_for_org(
            organization_id=org_id,
            entity_type=entity_type,
            limit=limit,
            offset=offset,
        )
        total = len(attachments)  # Simplified; could add count query

    return AttachmentList(
        items=[
            AttachmentPublic(
                id=str(att.id),
                organization_id=str(att.organization_id),
                entity_type=att.entity_type,
                entity_id=str(att.entity_id),
                filename=att.filename,
                s3_key=att.s3_key,
                content_type=att.content_type,
                size_bytes=att.size_bytes,
                created_at=att.created_at,
            )
            for att in attachments
        ],
        total=total,
    )


@router.post(
    "/attachments",
    response_model=AttachmentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_attachment(
    org_id: UUID,
    attachment_data: AttachmentCreate,
    current_user: RequireContributor,
    db: DbSession,
) -> AttachmentUploadResponse:
    """
    Create an attachment record and get a presigned upload URL.

    The client should:
    1. Call this endpoint to get the upload URL
    2. PUT the file directly to the presigned URL
    3. The attachment is ready for download after upload completes

    Args:
        org_id: Organization UUID
        attachment_data: Attachment metadata
        current_user: Current authenticated user
        db: Database session

    Returns:
        Attachment ID and presigned upload URL
    """
    settings = get_settings()
    if not settings.s3_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File storage is not configured",
        )

    repo = AttachmentRepository(db)
    file_storage = get_file_storage_service()

    # Create attachment record
    attachment = Attachment(
        organization_id=org_id,
        entity_type=attachment_data.entity_type,
        entity_id=attachment_data.entity_id,
        filename=attachment_data.filename,
        content_type=attachment_data.content_type,
        size_bytes=attachment_data.size_bytes,
        s3_key="",  # Will be set after generating
    )

    # Create first to get ID
    attachment = await repo.create(attachment)

    # Generate S3 key with attachment ID
    s3_key = file_storage.generate_s3_key(
        organization_id=org_id,
        entity_type=attachment_data.entity_type.value,
        entity_id=attachment_data.entity_id,
        attachment_id=attachment.id,
        filename=attachment_data.filename,
    )

    # Update with S3 key
    attachment.s3_key = s3_key
    await repo.update(attachment)

    # Generate presigned upload URL
    upload_url = await file_storage.generate_upload_url(
        s3_key=s3_key,
        content_type=attachment_data.content_type,
    )

    logger.info(
        f"Created attachment: {attachment.filename}",
        extra={
            "attachment_id": str(attachment.id),
            "org_id": str(org_id),
            "entity_type": attachment_data.entity_type.value,
            "entity_id": str(attachment_data.entity_id),
            "user_id": str(current_user.user_id),
        },
    )

    return AttachmentUploadResponse(
        id=str(attachment.id),
        filename=attachment.filename,
        upload_url=upload_url,
        expires_in=settings.s3_presigned_url_expiry,
    )


@router.get("/attachments/{attachment_id}", response_model=AttachmentPublic)
async def get_attachment(
    org_id: UUID,
    attachment_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> AttachmentPublic:
    """
    Get attachment metadata by ID.

    Args:
        org_id: Organization UUID
        attachment_id: Attachment UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Attachment metadata
    """
    repo = AttachmentRepository(db)
    attachment = await repo.get_by_id_and_org(attachment_id, org_id)

    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    return AttachmentPublic(
        id=str(attachment.id),
        organization_id=str(attachment.organization_id),
        entity_type=attachment.entity_type,
        entity_id=str(attachment.entity_id),
        filename=attachment.filename,
        s3_key=attachment.s3_key,
        content_type=attachment.content_type,
        size_bytes=attachment.size_bytes,
        created_at=attachment.created_at,
    )


@router.get("/attachments/{attachment_id}/download", response_model=AttachmentDownloadResponse)
async def download_attachment(
    org_id: UUID,
    attachment_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> AttachmentDownloadResponse:
    """
    Get a presigned download URL for an attachment.

    The client should redirect or fetch from the returned URL.

    Args:
        org_id: Organization UUID
        attachment_id: Attachment UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Presigned download URL and file metadata
    """
    settings = get_settings()
    if not settings.s3_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File storage is not configured",
        )

    repo = AttachmentRepository(db)
    attachment = await repo.get_by_id_and_org(attachment_id, org_id)

    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    file_storage = get_file_storage_service()
    download_url = await file_storage.generate_download_url(
        s3_key=attachment.s3_key,
        filename=attachment.filename,
    )

    return AttachmentDownloadResponse(
        download_url=download_url,
        filename=attachment.filename,
        content_type=attachment.content_type,
        size_bytes=attachment.size_bytes,
        expires_in=settings.s3_download_url_expiry,
    )


@router.get("/attachments/{attachment_id}/view")
async def view_attachment(
    org_id: UUID,
    attachment_id: UUID,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> RedirectResponse:
    """
    Redirect to a presigned download URL for an attachment.

    This endpoint provides a stable URL that can be embedded in documents.
    It generates a fresh presigned URL and redirects to it.

    Args:
        org_id: Organization UUID
        attachment_id: Attachment UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        302 redirect to presigned download URL
    """
    settings = get_settings()
    if not settings.s3_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File storage is not configured",
        )

    repo = AttachmentRepository(db)
    attachment = await repo.get_by_id_and_org(attachment_id, org_id)

    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    file_storage = get_file_storage_service()
    download_url = await file_storage.generate_download_url(
        s3_key=attachment.s3_key,
        filename=attachment.filename,
    )

    return RedirectResponse(url=download_url, status_code=status.HTTP_302_FOUND)


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    org_id: UUID,
    attachment_id: UUID,
    current_user: RequireContributor,
    db: DbSession,
) -> None:
    """
    Delete an attachment (database record and S3 file).

    Args:
        org_id: Organization UUID
        attachment_id: Attachment UUID
        current_user: Current authenticated user
        db: Database session
    """
    repo = AttachmentRepository(db)
    attachment = await repo.get_by_id_and_org(attachment_id, org_id)

    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    s3_key = attachment.s3_key

    # Delete from database first
    await repo.delete(attachment)

    # Then delete from S3 (best effort)
    settings = get_settings()
    if settings.s3_configured:
        file_storage = get_file_storage_service()
        await file_storage.delete_file(s3_key)

    logger.info(
        f"Deleted attachment: {attachment.filename}",
        extra={
            "attachment_id": str(attachment_id),
            "org_id": str(org_id),
            "user_id": str(current_user.user_id),
        },
    )


# Document images endpoint (for markdown embedding)
@router.post(
    "/documents/images",
    response_model=DocumentImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document_image(
    org_id: UUID,
    image_data: DocumentImageCreate,
    current_user: RequireContributor,
    db: DbSession,
) -> DocumentImageUploadResponse:
    """
    Upload an image for embedding in markdown documents.

    Returns a presigned upload URL and the final image URL to use in markdown.

    Args:
        org_id: Organization UUID
        image_data: Image metadata
        current_user: Current authenticated user
        db: Database session

    Returns:
        Upload URL and image URL for markdown
    """
    settings = get_settings()
    if not settings.s3_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File storage is not configured",
        )

    # Validate content type is an image
    if not image_data.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content type must be an image",
        )

    repo = AttachmentRepository(db)
    file_storage = get_file_storage_service()

    # Use a placeholder entity_id for document images without a document
    from uuid import uuid4

    entity_id = image_data.document_id or uuid4()

    # Create attachment record
    attachment = Attachment(
        organization_id=org_id,
        entity_type=EntityType.DOCUMENT_IMAGE,
        entity_id=entity_id,
        filename=image_data.filename,
        content_type=image_data.content_type,
        size_bytes=image_data.size_bytes,
        s3_key="",
    )

    attachment = await repo.create(attachment)

    # Generate S3 key
    s3_key = file_storage.generate_s3_key(
        organization_id=org_id,
        entity_type=EntityType.DOCUMENT_IMAGE.value,
        entity_id=entity_id,
        attachment_id=attachment.id,
        filename=image_data.filename,
    )

    attachment.s3_key = s3_key
    await repo.update(attachment)

    # Generate presigned upload URL
    upload_url = await file_storage.generate_upload_url(
        s3_key=s3_key,
        content_type=image_data.content_type,
    )

    # Generate stable image URL using the /view endpoint
    # This URL never expires and always redirects to a fresh presigned URL
    image_url = f"/api/organizations/{org_id}/attachments/{attachment.id}/view"

    logger.info(
        f"Created document image: {attachment.filename}",
        extra={
            "attachment_id": str(attachment.id),
            "org_id": str(org_id),
            "user_id": str(current_user.user_id),
        },
    )

    return DocumentImageUploadResponse(
        id=str(attachment.id),
        upload_url=upload_url,
        image_url=image_url,
        expires_in=settings.s3_presigned_url_expiry,
    )
