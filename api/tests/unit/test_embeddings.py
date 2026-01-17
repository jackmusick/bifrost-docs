"""
Unit tests for the embeddings service.

Tests searchable text extraction and content hash generation.
Uses mocks for OpenAI API calls.
"""

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.contracts.custom_asset import FieldDefinition
from src.services.embeddings import EmbeddingsService


def create_mock_service() -> EmbeddingsService:
    """Create an EmbeddingsService with a mock database session."""
    mock_db = MagicMock()
    return EmbeddingsService(mock_db)


class TestContentHash:
    """Tests for content hash generation."""

    def test_compute_content_hash_returns_md5(self) -> None:
        """Test that content hash is a 32-character hex MD5."""
        service = create_mock_service()
        text = "Test content for hashing"
        result = service.compute_content_hash(text)

        # MD5 produces 32-character hex string
        assert len(result) == 32
        assert all(c in "0123456789abcdef" for c in result)

    def test_compute_content_hash_deterministic(self) -> None:
        """Test that same input produces same hash."""
        service = create_mock_service()
        text = "Consistent content"

        hash1 = service.compute_content_hash(text)
        hash2 = service.compute_content_hash(text)

        assert hash1 == hash2

    def test_compute_content_hash_different_input(self) -> None:
        """Test that different input produces different hash."""
        service = create_mock_service()

        hash1 = service.compute_content_hash("Content A")
        hash2 = service.compute_content_hash("Content B")

        assert hash1 != hash2

    def test_compute_content_hash_matches_hashlib(self) -> None:
        """Test that hash matches Python's hashlib MD5."""
        service = create_mock_service()
        text = "Verify against hashlib"

        result = service.compute_content_hash(text)
        expected = hashlib.md5(text.encode("utf-8")).hexdigest()

        assert result == expected


class TestExtractSearchableText:
    """Tests for searchable text extraction from entities."""

    def test_extract_password_text(self) -> None:
        """Test extracting searchable text from password entity."""
        service = create_mock_service()

        # Create mock password entity
        password = MagicMock()
        password.name = "Database Admin"
        password.username = "admin@db.local"
        password.url = "https://db.example.com"
        password.notes = "Production database credentials"

        result = service.extract_searchable_text("password", password)

        assert "Database Admin" in result
        assert "Username: admin@db.local" in result
        assert "URL: https://db.example.com" in result
        assert "Production database credentials" in result
        # Ensure password value is NOT included (it shouldn't be on the entity anyway)

    def test_extract_password_text_minimal(self) -> None:
        """Test extracting text from password with only required fields."""
        service = create_mock_service()

        password = MagicMock()
        password.name = "Minimal Password"
        password.username = None
        password.url = None
        password.notes = None

        result = service.extract_searchable_text("password", password)

        assert "Minimal Password" in result
        assert "Username:" not in result
        assert "URL:" not in result

    def test_extract_configuration_text(self) -> None:
        """Test extracting searchable text from configuration entity."""
        service = create_mock_service()

        config = MagicMock()
        config.name = "webserver-01"
        config.serial_number = "SN12345"
        config.asset_tag = "IT-2024-001"
        config.manufacturer = "Dell"
        config.model = "PowerEdge R740"
        config.ip_address = "192.168.1.100"
        config.mac_address = "00:11:22:33:44:55"
        config.notes = "Primary web server"

        result = service.extract_searchable_text("configuration", config)

        assert "webserver-01" in result
        assert "Serial: SN12345" in result
        assert "Asset Tag: IT-2024-001" in result
        assert "Manufacturer: Dell" in result
        assert "Model: PowerEdge R740" in result
        assert "IP: 192.168.1.100" in result
        assert "MAC: 00:11:22:33:44:55" in result
        assert "Primary web server" in result

    def test_extract_configuration_text_minimal(self) -> None:
        """Test extracting text from configuration with only required fields."""
        service = create_mock_service()

        config = MagicMock()
        config.name = "router-01"
        config.serial_number = None
        config.asset_tag = None
        config.manufacturer = None
        config.model = None
        config.ip_address = None
        config.mac_address = None
        config.notes = None

        result = service.extract_searchable_text("configuration", config)

        assert result == "router-01"

    def test_extract_location_text(self) -> None:
        """Test extracting searchable text from location entity."""
        service = create_mock_service()

        location = MagicMock()
        location.name = "Data Center A"
        location.notes = "Primary data center in NYC"

        result = service.extract_searchable_text("location", location)

        assert "Data Center A" in result
        assert "Primary data center in NYC" in result

    def test_extract_location_text_minimal(self) -> None:
        """Test extracting text from location with only required fields."""
        service = create_mock_service()

        location = MagicMock()
        location.name = "Office"
        location.notes = None

        result = service.extract_searchable_text("location", location)

        assert result == "Office"

    def test_extract_document_text(self) -> None:
        """Test extracting searchable text from document entity."""
        service = create_mock_service()

        document = MagicMock()
        document.name = "Network Diagram"
        document.path = "/Infrastructure/Network"
        document.content = "This document describes the network topology..."

        result = service.extract_searchable_text("document", document)

        assert "Network Diagram" in result
        assert "Path: /Infrastructure/Network" in result
        assert "This document describes the network topology..." in result

    def test_extract_document_text_root_path(self) -> None:
        """Test that root path is not included in searchable text."""
        service = create_mock_service()

        document = MagicMock()
        document.name = "Root Document"
        document.path = "/"
        document.content = "Content here"

        result = service.extract_searchable_text("document", document)

        assert "Root Document" in result
        assert "Path:" not in result
        assert "Content here" in result

    def test_extract_custom_asset_text(self) -> None:
        """Test extracting searchable text from custom asset entity."""
        service = create_mock_service()

        # Create field definitions
        fields = [
            FieldDefinition(key="name", name="Name", type="text"),
            FieldDefinition(key="hostname", name="Hostname", type="text"),
            FieldDefinition(key="department", name="Department", type="text"),
            FieldDefinition(key="admin_password", name="Admin Password", type="password"),
        ]

        asset = MagicMock()
        asset.values = {
            "name": "Custom Server",
            "hostname": "custom-01",
            "department": "Engineering",
            # Password should be stored with _encrypted suffix in real data
            # but we test that password fields are excluded
        }

        # display_field_key is "name" - this is what appears as the display name
        result = service.extract_searchable_text("custom_asset", asset, fields, display_field_key="name")

        assert "Custom Server" in result
        assert "Hostname: custom-01" in result
        assert "Department: Engineering" in result
        # Password field should not be included
        assert "Admin Password" not in result

    def test_extract_custom_asset_excludes_encrypted_values(self) -> None:
        """Test that encrypted password values are excluded from searchable text."""
        service = create_mock_service()

        fields = [
            FieldDefinition(key="hostname", name="Hostname", type="text"),
            FieldDefinition(key="secret", name="Secret Key", type="password"),
        ]

        asset = MagicMock()
        asset.name = "Test Asset"  # Changed to avoid "secret" in name
        asset.values = {
            "hostname": "server-01",
            "secret_encrypted": "encrypted_value_here",  # This should be excluded
        }

        result = service.extract_searchable_text("custom_asset", asset, fields)

        assert "server-01" in result
        assert "encrypted_value_here" not in result
        # Password field values should not appear
        assert "secret_encrypted" not in result

    def test_extract_custom_asset_no_fields(self) -> None:
        """Test extracting text from custom asset with no field definitions."""
        service = create_mock_service()

        asset = MagicMock()
        asset.values = {}

        # With no display_field_key and no values, result should be empty
        result = service.extract_searchable_text("custom_asset", asset, None)

        assert result == ""

    def test_extract_unknown_entity_type_returns_empty(self) -> None:
        """Test that unknown entity type returns empty (handled by type system)."""
        service = create_mock_service()

        # Type system prevents this at compile time, but if bypassed,
        # no match case will trigger and parts will be empty
        result = service.extract_searchable_text("unknown_type", MagicMock())  # type: ignore[arg-type]
        # With no matching case, only empty parts list, result is empty string
        assert result == ""


class TestGenerateEmbedding:
    """Tests for embedding generation."""

    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text_raises(self) -> None:
        """Test that empty text raises ValueError."""
        service = create_mock_service()

        with pytest.raises(ValueError, match="Cannot generate embedding for empty text"):
            await service.generate_embedding("")

    @pytest.mark.asyncio
    async def test_generate_embedding_whitespace_only_raises(self) -> None:
        """Test that whitespace-only text raises ValueError."""
        service = create_mock_service()

        with pytest.raises(ValueError, match="Cannot generate embedding for empty text"):
            await service.generate_embedding("   \n\t  ")

    @pytest.mark.asyncio
    async def test_generate_embedding_no_api_key_raises(self) -> None:
        """Test that missing API key raises ValueError."""
        with patch("src.services.embeddings.get_embeddings_config") as mock_config:
            # Return None to simulate no config
            mock_config.return_value = None

            service = create_mock_service()

            with pytest.raises(ValueError, match="OpenAI API key is not configured"):
                await service.generate_embedding("test text")

    @pytest.mark.asyncio
    async def test_generate_embedding_calls_openai(self) -> None:
        """Test that embedding generation calls OpenAI API correctly."""
        from src.services.llm.factory import EmbeddingsConfig

        with patch("src.services.embeddings.get_embeddings_config") as mock_config:
            mock_config.return_value = EmbeddingsConfig(
                api_key="test-api-key",
                model="text-embedding-3-small",
            )

            service = create_mock_service()

            # Mock the OpenAI client
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1536)]

            mock_client = AsyncMock()
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            with patch.object(service, "_client", mock_client):
                result = await service.generate_embedding("test text")

                mock_client.embeddings.create.assert_called_once()
                assert result == [0.1] * 1536
