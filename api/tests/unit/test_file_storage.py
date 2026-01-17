"""
Unit tests for file storage service.

Tests S3 URL generation and utility functions with mocked S3 client.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.services.file_storage import FileStorageService, reset_file_storage_service


@pytest.fixture(autouse=True)
def reset_service():
    """Reset file storage service singleton before each test."""
    reset_file_storage_service()
    yield
    reset_file_storage_service()


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock()
    settings.s3_configured = True
    settings.s3_endpoint = "http://localhost:9000"
    settings.s3_access_key = "test-access-key"
    settings.s3_secret_key = "test-secret-key"
    settings.s3_region = "us-east-1"
    settings.s3_bucket = "test-bucket"
    settings.s3_presigned_url_expiry = 600
    settings.s3_download_url_expiry = 3600
    return settings


@pytest.fixture
def file_storage_service(mock_settings):
    """Create file storage service with mock settings."""
    return FileStorageService(settings=mock_settings)


class TestFileStorageService:
    """Tests for FileStorageService."""

    def test_compute_hash(self):
        """Test SHA-256 hash computation."""
        content = b"Hello, World!"
        hash_result = FileStorageService.compute_hash(content)

        # SHA-256 hash should be 64 hex characters
        assert len(hash_result) == 64
        assert all(c in "0123456789abcdef" for c in hash_result)

        # Same content should produce same hash
        assert FileStorageService.compute_hash(content) == hash_result

        # Different content should produce different hash
        assert FileStorageService.compute_hash(b"Different") != hash_result

    def test_guess_content_type(self):
        """Test MIME type guessing."""
        # Common file types
        assert FileStorageService.guess_content_type("document.pdf") == "application/pdf"
        assert FileStorageService.guess_content_type("image.png") == "image/png"
        assert FileStorageService.guess_content_type("image.jpg") == "image/jpeg"
        assert FileStorageService.guess_content_type("data.json") == "application/json"
        assert FileStorageService.guess_content_type("script.js") in [
            "application/javascript",
            "text/javascript",
        ]
        assert FileStorageService.guess_content_type("style.css") == "text/css"
        assert FileStorageService.guess_content_type("page.html") == "text/html"

        # Unknown type should default to octet-stream
        assert (
            FileStorageService.guess_content_type("file.unknown")
            == "application/octet-stream"
        )

    def test_generate_s3_key(self, file_storage_service):
        """Test S3 key generation."""
        org_id = uuid4()
        entity_id = uuid4()
        attachment_id = uuid4()

        s3_key = file_storage_service.generate_s3_key(
            entity_type="document",
            entity_id=entity_id,
            attachment_id=attachment_id,
            filename="test-file.pdf",
        )

        # Key should contain all components
        assert str(org_id) in s3_key
        assert "document" in s3_key
        assert str(entity_id) in s3_key
        assert str(attachment_id) in s3_key
        assert "test-file.pdf" in s3_key

        # Key should follow expected format
        expected = f"{org_id}/document/{entity_id}/{attachment_id}/test-file.pdf"
        assert s3_key == expected

    @pytest.mark.asyncio
    async def test_generate_upload_url(self, file_storage_service):
        """Test presigned upload URL generation."""
        with patch(
            "aiobotocore.session.get_session"
        ) as mock_get_session:
            # Setup mock S3 client
            mock_s3_client = AsyncMock()
            mock_s3_client.generate_presigned_url = AsyncMock(
                return_value="https://s3.example.com/upload-url"
            )

            mock_session = MagicMock()
            mock_session.create_client = MagicMock()
            mock_session.create_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_s3_client
            )
            mock_session.create_client.return_value.__aexit__ = AsyncMock()

            mock_get_session.return_value = mock_session

            # Generate upload URL
            url = await file_storage_service.generate_upload_url(
                s3_key="test/key.pdf",
                content_type="application/pdf",
            )

            assert url == "https://s3.example.com/upload-url"

            # Verify S3 client was called correctly
            mock_s3_client.generate_presigned_url.assert_called_once_with(
                "put_object",
                Params={
                    "Bucket": "test-bucket",
                    "Key": "test/key.pdf",
                    "ContentType": "application/pdf",
                },
                ExpiresIn=600,
            )

    @pytest.mark.asyncio
    async def test_generate_download_url(self, file_storage_service):
        """Test presigned download URL generation."""
        with patch(
            "aiobotocore.session.get_session"
        ) as mock_get_session:
            # Setup mock S3 client
            mock_s3_client = AsyncMock()
            mock_s3_client.generate_presigned_url = AsyncMock(
                return_value="https://s3.example.com/download-url"
            )

            mock_session = MagicMock()
            mock_session.create_client = MagicMock()
            mock_session.create_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_s3_client
            )
            mock_session.create_client.return_value.__aexit__ = AsyncMock()

            mock_get_session.return_value = mock_session

            # Generate download URL with filename
            url = await file_storage_service.generate_download_url(
                s3_key="test/key.pdf",
                filename="document.pdf",
            )

            assert url == "https://s3.example.com/download-url"

            # Verify S3 client was called with Content-Disposition
            mock_s3_client.generate_presigned_url.assert_called_once()
            call_args = mock_s3_client.generate_presigned_url.call_args
            assert call_args[0][0] == "get_object"
            assert call_args[1]["Params"]["Bucket"] == "test-bucket"
            assert call_args[1]["Params"]["Key"] == "test/key.pdf"
            assert (
                'filename="document.pdf"'
                in call_args[1]["Params"]["ResponseContentDisposition"]
            )
            assert call_args[1]["ExpiresIn"] == 3600

    @pytest.mark.asyncio
    async def test_generate_download_url_without_filename(self, file_storage_service):
        """Test download URL generation without filename."""
        with patch(
            "aiobotocore.session.get_session"
        ) as mock_get_session:
            mock_s3_client = AsyncMock()
            mock_s3_client.generate_presigned_url = AsyncMock(
                return_value="https://s3.example.com/download-url"
            )

            mock_session = MagicMock()
            mock_session.create_client = MagicMock()
            mock_session.create_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_s3_client
            )
            mock_session.create_client.return_value.__aexit__ = AsyncMock()

            mock_get_session.return_value = mock_session

            # Generate download URL without filename
            url = await file_storage_service.generate_download_url(
                s3_key="test/key.pdf",
            )

            assert url == "https://s3.example.com/download-url"

            # Verify no Content-Disposition header
            call_args = mock_s3_client.generate_presigned_url.call_args
            assert "ResponseContentDisposition" not in call_args[1]["Params"]

    @pytest.mark.asyncio
    async def test_delete_file(self, file_storage_service):
        """Test file deletion."""
        with patch(
            "aiobotocore.session.get_session"
        ) as mock_get_session:
            mock_s3_client = AsyncMock()
            mock_s3_client.delete_object = AsyncMock()

            mock_session = MagicMock()
            mock_session.create_client = MagicMock()
            mock_session.create_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_s3_client
            )
            mock_session.create_client.return_value.__aexit__ = AsyncMock()

            mock_get_session.return_value = mock_session

            result = await file_storage_service.delete_file("test/key.pdf")

            assert result is True
            mock_s3_client.delete_object.assert_called_once_with(
                Bucket="test-bucket",
                Key="test/key.pdf",
            )

    @pytest.mark.asyncio
    async def test_delete_file_failure(self, file_storage_service):
        """Test file deletion failure handling."""
        # Patch the get_client method directly to raise an exception
        with patch.object(
            file_storage_service, "get_client"
        ) as mock_get_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.side_effect = Exception("S3 error")
            mock_get_client.return_value = mock_context

            result = await file_storage_service.delete_file("test/key.pdf")

            assert result is False

    @pytest.mark.asyncio
    async def test_file_exists(self, file_storage_service):
        """Test file existence check."""
        with patch(
            "aiobotocore.session.get_session"
        ) as mock_get_session:
            mock_s3_client = AsyncMock()
            mock_s3_client.head_object = AsyncMock()

            mock_session = MagicMock()
            mock_session.create_client = MagicMock()
            mock_session.create_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_s3_client
            )
            mock_session.create_client.return_value.__aexit__ = AsyncMock()

            mock_get_session.return_value = mock_session

            result = await file_storage_service.file_exists("test/key.pdf")

            assert result is True
            mock_s3_client.head_object.assert_called_once_with(
                Bucket="test-bucket",
                Key="test/key.pdf",
            )

    @pytest.mark.asyncio
    async def test_file_not_exists(self, file_storage_service):
        """Test file existence check for non-existent file."""
        # Patch the get_client method directly to raise an exception
        with patch.object(
            file_storage_service, "get_client"
        ) as mock_get_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.side_effect = Exception("NoSuchKey")
            mock_get_client.return_value = mock_context

            result = await file_storage_service.file_exists("test/nonexistent.pdf")

            assert result is False


class TestFileStorageServiceNotConfigured:
    """Tests for FileStorageService when S3 is not configured."""

    @pytest.mark.asyncio
    async def test_get_client_raises_when_not_configured(self):
        """Test that get_client raises RuntimeError when S3 is not configured."""
        mock_settings = MagicMock()
        mock_settings.s3_configured = False

        service = FileStorageService(settings=mock_settings)

        with pytest.raises(RuntimeError, match="S3 storage not configured"):
            async with service.get_client():
                pass
