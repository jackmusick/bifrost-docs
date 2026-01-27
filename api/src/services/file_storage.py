"""
S3 storage service for file attachments.

Handles S3 operations including:
- Presigned upload URLs
- Presigned download URLs
- File deletion
- MIME type detection

Supports MinIO in development and any S3-compatible storage in production.
"""

import hashlib
import logging
import mimetypes
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any
from uuid import UUID

from src.config import Settings, get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)


class FileStorageService:
    """Service for S3-compatible file storage operations."""

    def __init__(self, settings: Settings | None = None):
        """
        Initialize file storage service.

        Args:
            settings: Application settings with S3 configuration.
                     Uses get_settings() if not provided.
        """
        self.settings = settings or get_settings()

    @asynccontextmanager
    async def get_client(self) -> "AsyncGenerator[Any, None]":
        """
        Get S3 client context manager.

        Yields:
            Async S3 client from aiobotocore

        Raises:
            RuntimeError: If S3 storage is not configured
        """
        if not self.settings.s3_configured:
            raise RuntimeError(
                "S3 storage not configured. "
                "Set BIFROST_DOCS_S3_ACCESS_KEY and BIFROST_DOCS_S3_SECRET_KEY environment variables."
            )

        from aiobotocore.session import get_session

        session = get_session()
        async with session.create_client(
            "s3",
            endpoint_url=self.settings.s3_endpoint,
            aws_access_key_id=self.settings.s3_access_key,
            aws_secret_access_key=self.settings.s3_secret_key,
            region_name=self.settings.s3_region,
        ) as client:
            yield client

    @staticmethod
    def compute_hash(content: bytes) -> str:
        """
        Compute SHA-256 hash of content.

        Args:
            content: File content bytes

        Returns:
            Hex-encoded SHA-256 hash
        """
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def guess_content_type(filename: str) -> str:
        """
        Guess content type from filename.

        Args:
            filename: File name with extension

        Returns:
            MIME type string (defaults to 'application/octet-stream' if unknown)
        """
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or "application/octet-stream"

    def _rewrite_url_for_public(self, url: str) -> str:
        """
        Rewrite internal S3 URL to use public endpoint.

        When S3/MinIO runs in Docker, presigned URLs contain internal hostnames
        (e.g., 'minio:9000') that browsers can't access. This rewrites them to
        use the configured public endpoint.

        Args:
            url: Presigned URL with internal endpoint

        Returns:
            URL with public endpoint substituted
        """
        public_endpoint = self.settings.s3_public_endpoint
        if not public_endpoint:
            return url
        return url.replace(self.settings.s3_endpoint, public_endpoint, 1)

    def generate_s3_key(
        self,
        organization_id: UUID,
        entity_type: str,
        entity_id: UUID,
        attachment_id: UUID,
        filename: str,
    ) -> str:
        """
        Generate a unique S3 key for an attachment.

        Format: {org_id}/{entity_type}/{entity_id}/{attachment_id}/{filename}

        Args:
            organization_id: Organization UUID
            entity_type: Type of entity (password, document, etc.)
            entity_id: Entity UUID
            attachment_id: Attachment UUID
            filename: Original filename

        Returns:
            S3 key path
        """
        return f"{organization_id}/{entity_type}/{entity_id}/{attachment_id}/{filename}"

    async def generate_upload_url(
        self,
        s3_key: str,
        content_type: str,
        expires_in: int | None = None,
    ) -> str:
        """
        Generate a presigned PUT URL for direct S3 upload.

        Args:
            s3_key: Target path in S3
            content_type: MIME type of the file being uploaded
            expires_in: URL expiration time in seconds (default from settings)

        Returns:
            Presigned PUT URL for direct browser upload
        """
        if expires_in is None:
            expires_in = self.settings.s3_presigned_url_expiry

        async with self.get_client() as s3:
            url: str = await s3.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.settings.s3_bucket,
                    "Key": s3_key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )
        return self._rewrite_url_for_public(url)

    async def generate_download_url(
        self,
        s3_key: str,
        filename: str | None = None,
        expires_in: int | None = None,
    ) -> str:
        """
        Generate a presigned GET URL for file download.

        Args:
            s3_key: File path in S3
            filename: Original filename for Content-Disposition header
            expires_in: URL expiration time in seconds (default from settings)

        Returns:
            Presigned GET URL for download
        """
        if expires_in is None:
            expires_in = self.settings.s3_download_url_expiry

        params: dict[str, Any] = {
            "Bucket": self.settings.s3_bucket,
            "Key": s3_key,
        }

        # Add Content-Disposition header for proper filename on download
        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'

        async with self.get_client() as s3:
            url: str = await s3.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expires_in,
            )
        return self._rewrite_url_for_public(url)

    async def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3.

        Args:
            s3_key: File path in S3

        Returns:
            True if deletion was successful
        """
        try:
            async with self.get_client() as s3:
                await s3.delete_object(
                    Bucket=self.settings.s3_bucket,
                    Key=s3_key,
                )
            logger.info(f"Deleted file from S3: {s3_key}")
            return True
        except Exception as e:
            logger.error(
                f"Failed to delete file from S3: {s3_key}, error: {e}")
            return False

    async def upload_file(
        self,
        s3_key: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> bool:
        """
        Upload file content directly to S3.

        Args:
            s3_key: Target path in S3
            content: File content as bytes
            content_type: MIME type of the content

        Returns:
            True if upload was successful
        """
        try:
            async with self.get_client() as s3:
                await s3.put_object(
                    Bucket=self.settings.s3_bucket,
                    Key=s3_key,
                    Body=content,
                    ContentType=content_type,
                )
            logger.info(
                f"Uploaded file to S3: {s3_key} ({len(content)} bytes)")
            return True
        except Exception as e:
            logger.error(f"Failed to upload file to S3: {s3_key}, error: {e}")
            return False

    async def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3.

        Args:
            s3_key: File path in S3

        Returns:
            True if file exists
        """
        try:
            async with self.get_client() as s3:
                await s3.head_object(
                    Bucket=self.settings.s3_bucket,
                    Key=s3_key,
                )
            return True
        except Exception:
            return False

    async def ensure_bucket_exists(self) -> bool:
        """
        Ensure the configured bucket exists, creating it if necessary.

        Useful for development/testing with MinIO.

        Returns:
            True if bucket exists or was created successfully
        """
        try:
            async with self.get_client() as s3:
                try:
                    await s3.head_bucket(Bucket=self.settings.s3_bucket)
                    return True
                except Exception:
                    # Bucket doesn't exist, create it
                    await s3.create_bucket(Bucket=self.settings.s3_bucket)
                    logger.info(
                        f"Created S3 bucket: {self.settings.s3_bucket}")
                    return True
        except Exception as e:
            logger.error(f"Failed to ensure bucket exists: {e}")
            return False


# Module-level singleton for convenience
_file_storage_service: FileStorageService | None = None


def get_file_storage_service() -> FileStorageService:
    """
    Get the file storage service singleton.

    Returns:
        FileStorageService instance
    """
    global _file_storage_service
    if _file_storage_service is None:
        _file_storage_service = FileStorageService()
    return _file_storage_service


def reset_file_storage_service() -> None:
    """Reset the file storage service (for testing)."""
    global _file_storage_service
    _file_storage_service = None
