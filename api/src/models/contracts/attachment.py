"""
Attachment contracts (API request/response schemas).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import EntityType


class AttachmentCreate(BaseModel):
    """Attachment creation request model."""

    entity_type: EntityType = Field(..., description="Type of entity this attaches to")
    entity_id: UUID = Field(..., description="ID of the entity this attaches to")
    filename: str = Field(..., max_length=255, description="Original filename")
    content_type: str = Field(..., max_length=255, description="MIME type")
    size_bytes: int = Field(..., ge=0, description="File size in bytes")


class AttachmentPublic(BaseModel):
    """Attachment public response model."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    entity_type: EntityType
    entity_id: str
    filename: str
    s3_key: str
    content_type: str
    size_bytes: int
    created_at: datetime


class AttachmentUploadResponse(BaseModel):
    """Response with presigned upload URL."""

    id: str = Field(..., description="Attachment ID")
    filename: str = Field(..., description="Original filename")
    upload_url: str = Field(..., description="Presigned PUT URL for direct upload")
    expires_in: int = Field(default=600, description="URL expiration in seconds")


class AttachmentDownloadResponse(BaseModel):
    """Response with presigned download URL."""

    download_url: str = Field(..., description="Presigned GET URL for download")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")
    size_bytes: int = Field(..., description="File size in bytes")
    expires_in: int = Field(default=3600, description="URL expiration in seconds")


class AttachmentList(BaseModel):
    """List of attachments response."""

    items: list[AttachmentPublic]
    total: int


class DocumentImageCreate(BaseModel):
    """Document image upload request model."""

    filename: str = Field(..., max_length=255, description="Original filename")
    content_type: str = Field(
        ...,
        max_length=255,
        description="MIME type (must be image/*)",
        pattern=r"^image/",
    )
    size_bytes: int = Field(..., ge=0, description="File size in bytes")
    document_id: UUID | None = Field(
        None, description="Optional document ID to associate with"
    )


class DocumentImageUploadResponse(BaseModel):
    """Response for document image upload."""

    id: str = Field(..., description="Attachment ID")
    upload_url: str = Field(..., description="Presigned PUT URL for direct upload")
    image_url: str = Field(..., description="URL to use in markdown after upload")
    expires_in: int = Field(default=600, description="Upload URL expiration in seconds")
