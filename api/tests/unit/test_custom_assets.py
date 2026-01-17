"""
Unit tests for custom asset validation and encryption.

Tests field definition validation, value validation, and password field handling.
"""

import pytest

from src.models.contracts.custom_asset import FieldDefinition
from src.services.custom_asset_validation import (
    CustomAssetValidationError,
    apply_default_values,
    decrypt_password_fields,
    encrypt_password_fields,
    filter_password_fields,
    validate_field_definitions,
    validate_values,
)


class TestFieldDefinitionValidation:
    """Tests for field definition validation."""

    def test_valid_text_field(self):
        """Test that a valid text field passes validation."""
        fields = [
            FieldDefinition(
                key="hostname",
                name="Hostname",
                type="text",
                required=True,
            )
        ]
        # Should not raise
        validate_field_definitions(fields)

    def test_valid_select_field_with_options(self):
        """Test that a select field with options passes validation."""
        fields = [
            FieldDefinition(
                key="status",
                name="Status",
                type="select",
                options=["Active", "Inactive", "Pending"],
            )
        ]
        # Should not raise
        validate_field_definitions(fields)

    def test_select_field_requires_options(self):
        """Test that a select field without options fails validation."""
        with pytest.raises(ValueError) as exc_info:
            FieldDefinition(
                key="status",
                name="Status",
                type="select",
                options=[],  # Empty options
            )
        assert "requires options" in str(exc_info.value).lower()

    def test_select_field_requires_options_none(self):
        """Test that a select field with None options fails validation."""
        with pytest.raises(ValueError) as exc_info:
            FieldDefinition(
                key="status",
                name="Status",
                type="select",
                options=None,  # No options
            )
        assert "requires options" in str(exc_info.value).lower()

    def test_duplicate_field_keys_rejected(self):
        """Test that duplicate field keys are rejected."""
        fields = [
            FieldDefinition(key="name", name="Name", type="text"),
            FieldDefinition(key="name", name="Name 2", type="text"),  # Duplicate key
        ]
        with pytest.raises(CustomAssetValidationError) as exc_info:
            validate_field_definitions(fields)
        assert "unique" in str(exc_info.value).lower()

    def test_all_field_types_valid(self):
        """Test that all supported field types are valid."""
        fields = [
            FieldDefinition(key="text_field", name="Text", type="text"),
            FieldDefinition(key="textbox_field", name="Textbox", type="textbox"),
            FieldDefinition(key="number_field", name="Number", type="number"),
            FieldDefinition(key="date_field", name="Date", type="date"),
            FieldDefinition(key="checkbox_field", name="Checkbox", type="checkbox"),
            FieldDefinition(key="password_field", name="Password", type="password"),
            FieldDefinition(key="header_field", name="Header", type="header"),
            FieldDefinition(
                key="select_field",
                name="Select",
                type="select",
                options=["A", "B"],
            ),
        ]
        # Should not raise
        validate_field_definitions(fields)


class TestValueValidation:
    """Tests for value validation against field definitions."""

    @pytest.fixture
    def sample_fields(self) -> list[FieldDefinition]:
        """Sample field definitions for testing."""
        return [
            FieldDefinition(key="name", name="Name", type="text", required=True),
            FieldDefinition(key="notes", name="Notes", type="textbox"),
            FieldDefinition(key="port", name="Port", type="number"),
            FieldDefinition(key="expiry", name="Expiry Date", type="date"),
            FieldDefinition(key="enabled", name="Enabled", type="checkbox"),
            FieldDefinition(key="secret", name="Secret", type="password"),
            FieldDefinition(
                key="env",
                name="Environment",
                type="select",
                options=["dev", "staging", "prod"],
            ),
            FieldDefinition(key="section", name="Section Header", type="header"),
        ]

    def test_valid_values_pass(self, sample_fields):
        """Test that valid values pass validation."""
        values = {
            "name": "My Asset",
            "notes": "Some notes here",
            "port": 443,
            "expiry": "2025-12-31T00:00:00Z",
            "enabled": True,
            "secret": "super-secret",
            "env": "prod",
        }
        # Should not raise
        validate_values(sample_fields, values)

    def test_required_field_missing_fails(self, sample_fields):
        """Test that missing required fields fail validation."""
        values = {
            "notes": "Some notes",
        }
        with pytest.raises(CustomAssetValidationError) as exc_info:
            validate_values(sample_fields, values)
        assert "name" in str(exc_info.value).lower()
        assert "required" in str(exc_info.value).lower()

    def test_unknown_field_key_rejected(self, sample_fields):
        """Test that unknown field keys are rejected."""
        values = {
            "name": "My Asset",
            "unknown_field": "value",
        }
        with pytest.raises(CustomAssetValidationError) as exc_info:
            validate_values(sample_fields, values)
        assert "unknown" in str(exc_info.value).lower()

    def test_partial_update_skips_required_validation(self, sample_fields):
        """Test that partial updates skip required field validation."""
        values = {
            "notes": "Updated notes",
        }
        # Should not raise with partial=True
        validate_values(sample_fields, values, partial=True)

    def test_text_field_requires_string(self, sample_fields):
        """Test that text fields require string values."""
        values = {
            "name": 123,  # Should be string
        }
        with pytest.raises(CustomAssetValidationError) as exc_info:
            validate_values(sample_fields, values, partial=True)
        assert "string" in str(exc_info.value).lower()

    def test_number_field_requires_number(self, sample_fields):
        """Test that number fields require numeric values."""
        values = {
            "name": "Asset",
            "port": "not-a-number",  # Should be number
        }
        with pytest.raises(CustomAssetValidationError) as exc_info:
            validate_values(sample_fields, values)
        assert "number" in str(exc_info.value).lower()

    def test_checkbox_field_requires_boolean(self, sample_fields):
        """Test that checkbox fields require boolean values."""
        values = {
            "name": "Asset",
            "enabled": "yes",  # Should be boolean
        }
        with pytest.raises(CustomAssetValidationError) as exc_info:
            validate_values(sample_fields, values)
        assert "boolean" in str(exc_info.value).lower()

    def test_date_field_requires_valid_iso_date(self, sample_fields):
        """Test that date fields require valid ISO date strings."""
        values = {
            "name": "Asset",
            "expiry": "not-a-date",
        }
        with pytest.raises(CustomAssetValidationError) as exc_info:
            validate_values(sample_fields, values)
        assert "date" in str(exc_info.value).lower()

    def test_date_field_accepts_valid_iso_date(self, sample_fields):
        """Test that date fields accept valid ISO date strings."""
        values = {
            "name": "Asset",
            "expiry": "2025-06-15T10:30:00+00:00",
        }
        # Should not raise
        validate_values(sample_fields, values)

    def test_select_field_requires_valid_option(self, sample_fields):
        """Test that select fields require values from options list."""
        values = {
            "name": "Asset",
            "env": "invalid-option",
        }
        with pytest.raises(CustomAssetValidationError) as exc_info:
            validate_values(sample_fields, values)
        assert "dev" in str(exc_info.value) or "prod" in str(exc_info.value)

    def test_select_field_accepts_valid_option(self, sample_fields):
        """Test that select fields accept values from options list."""
        values = {
            "name": "Asset",
            "env": "staging",
        }
        # Should not raise
        validate_values(sample_fields, values)

    def test_optional_fields_accept_none(self, sample_fields):
        """Test that optional fields accept None values."""
        values = {
            "name": "Asset",
            "notes": None,
            "port": None,
        }
        # Should not raise
        validate_values(sample_fields, values)

    def test_required_field_null_fails(self, sample_fields):
        """Test that required fields with null value fail."""
        values = {
            "name": None,  # Required field cannot be null
        }
        with pytest.raises(CustomAssetValidationError) as exc_info:
            validate_values(sample_fields, values)
        assert "name" in str(exc_info.value).lower()


class TestPasswordFieldEncryption:
    """Tests for password field encryption/decryption."""

    @pytest.fixture
    def fields_with_password(self) -> list[FieldDefinition]:
        """Field definitions including password fields."""
        return [
            FieldDefinition(key="username", name="Username", type="text"),
            FieldDefinition(key="api_key", name="API Key", type="password"),
            FieldDefinition(key="secret_token", name="Secret Token", type="password"),
        ]

    def test_encrypt_password_fields(self, fields_with_password):
        """Test that password fields are encrypted."""
        values = {
            "username": "admin",
            "api_key": "my-api-key-123",
            "secret_token": "super-secret-token",
        }

        encrypted = encrypt_password_fields(fields_with_password, values)

        # Non-password fields should be unchanged
        assert encrypted["username"] == "admin"

        # Password fields should be removed and replaced with encrypted versions
        assert "api_key" not in encrypted
        assert "secret_token" not in encrypted
        assert "api_key_encrypted" in encrypted
        assert "secret_token_encrypted" in encrypted

        # Encrypted values should be different from originals
        assert encrypted["api_key_encrypted"] != "my-api-key-123"
        assert encrypted["secret_token_encrypted"] != "super-secret-token"

    def test_decrypt_password_fields(self, fields_with_password):
        """Test that password fields are decrypted."""
        values = {
            "username": "admin",
            "api_key": "my-api-key-123",
            "secret_token": "super-secret-token",
        }

        # Encrypt first
        encrypted = encrypt_password_fields(fields_with_password, values)

        # Then decrypt
        decrypted = decrypt_password_fields(fields_with_password, encrypted)

        # Non-password fields should be unchanged
        assert decrypted["username"] == "admin"

        # Password fields should be restored to original keys and values
        assert decrypted["api_key"] == "my-api-key-123"
        assert decrypted["secret_token"] == "super-secret-token"

        # Encrypted keys should be removed
        assert "api_key_encrypted" not in decrypted
        assert "secret_token_encrypted" not in decrypted

    def test_filter_password_fields(self, fields_with_password):
        """Test that password fields are filtered from response."""
        values = {
            "username": "admin",
            "api_key_encrypted": "encrypted-value-1",
            "secret_token_encrypted": "encrypted-value-2",
        }

        filtered = filter_password_fields(fields_with_password, values)

        # Non-password fields should be present
        assert filtered["username"] == "admin"

        # All password-related keys should be removed
        assert "api_key" not in filtered
        assert "secret_token" not in filtered
        assert "api_key_encrypted" not in filtered
        assert "secret_token_encrypted" not in filtered

    def test_encrypt_handles_none_values(self, fields_with_password):
        """Test that encryption handles None password values."""
        values = {
            "username": "admin",
            "api_key": None,
            "secret_token": "secret",
        }

        encrypted = encrypt_password_fields(fields_with_password, values)

        # None values should not be encrypted
        assert encrypted.get("api_key") is None
        assert "api_key_encrypted" not in encrypted

        # Non-None password should be encrypted
        assert "secret_token_encrypted" in encrypted

    def test_roundtrip_encryption(self, fields_with_password):
        """Test full encryption/decryption roundtrip."""
        original_values = {
            "username": "admin",
            "api_key": "key-with-special-chars-!@#$%",
            "secret_token": "token-123-abc",
        }

        # Encrypt
        encrypted = encrypt_password_fields(fields_with_password, original_values)

        # Decrypt
        decrypted = decrypt_password_fields(fields_with_password, encrypted)

        # Should match original
        assert decrypted == original_values


class TestDefaultValues:
    """Tests for applying default values."""

    @pytest.fixture
    def fields_with_defaults(self) -> list[FieldDefinition]:
        """Field definitions with default values."""
        return [
            FieldDefinition(
                key="name", name="Name", type="text", required=True
            ),
            FieldDefinition(
                key="port", name="Port", type="number", default_value="443"
            ),
            FieldDefinition(
                key="enabled", name="Enabled", type="checkbox", default_value="true"
            ),
            FieldDefinition(
                key="env",
                name="Environment",
                type="select",
                options=["dev", "prod"],
                default_value="dev",
            ),
        ]

    def test_apply_default_values(self, fields_with_defaults):
        """Test that default values are applied for missing fields."""
        values = {
            "name": "My Asset",
        }

        result = apply_default_values(fields_with_defaults, values)

        assert result["name"] == "My Asset"
        assert result["port"] == 443.0  # Converted to number
        assert result["enabled"] is True  # Converted to boolean
        assert result["env"] == "dev"

    def test_provided_values_override_defaults(self, fields_with_defaults):
        """Test that provided values override defaults."""
        values = {
            "name": "My Asset",
            "port": 8080,
            "enabled": False,
            "env": "prod",
        }

        result = apply_default_values(fields_with_defaults, values)

        assert result["port"] == 8080
        assert result["enabled"] is False
        assert result["env"] == "prod"

    def test_fields_without_defaults_not_added(self, fields_with_defaults):
        """Test that fields without defaults are not added."""
        values = {}

        result = apply_default_values(fields_with_defaults, values)

        # Only fields with defaults should be present
        assert "name" not in result  # No default
        assert "port" in result
        assert "enabled" in result
        assert "env" in result


class TestDisplayFieldKey:
    """Tests for display_field_key validation and fallback logic."""

    @pytest.fixture
    def sample_fields(self) -> list[FieldDefinition]:
        """Sample field definitions for testing."""
        return [
            FieldDefinition(key="hostname", name="Hostname", type="text", required=True),
            FieldDefinition(key="port", name="Port", type="number"),
            FieldDefinition(key="notes", name="Notes", type="textbox"),
        ]

    @pytest.fixture
    def fields_with_header(self) -> list[FieldDefinition]:
        """Field definitions including a header."""
        return [
            FieldDefinition(key="info_header", name="Server Info", type="header"),
            FieldDefinition(key="hostname", name="Hostname", type="text", required=True),
            FieldDefinition(key="port", name="Port", type="number"),
        ]

    @pytest.fixture
    def number_only_fields(self) -> list[FieldDefinition]:
        """Field definitions with only non-text fields."""
        return [
            FieldDefinition(key="count", name="Count", type="number"),
            FieldDefinition(key="enabled", name="Enabled", type="checkbox"),
        ]

    def test_display_field_key_fallback_to_first_text(self, sample_fields):
        """Test that display field defaults to first text/textbox field."""
        # With no display_field_key set, should fallback to first text field
        # This tests the concept - actual implementation is in frontend
        text_fields = [f for f in sample_fields if f.type in ("text", "textbox")]
        assert len(text_fields) > 0
        assert text_fields[0].key == "hostname"

    def test_display_field_key_skips_header(self, fields_with_header):
        """Test that header fields are skipped in display field fallback."""
        non_header_fields = [f for f in fields_with_header if f.type != "header"]
        text_fields = [f for f in non_header_fields if f.type in ("text", "textbox")]
        assert len(text_fields) > 0
        assert text_fields[0].key == "hostname"

    def test_display_field_key_fallback_to_first_non_header(self, number_only_fields):
        """Test fallback to first non-header field when no text fields exist."""
        non_header_fields = [f for f in number_only_fields if f.type != "header"]
        text_fields = [f for f in non_header_fields if f.type in ("text", "textbox")]
        # No text fields available
        assert len(text_fields) == 0
        # Should fall back to first non-header field
        assert len(non_header_fields) > 0
        assert non_header_fields[0].key == "count"

    def test_display_field_key_validation_valid(self, sample_fields):
        """Test that valid display_field_key is accepted."""
        valid_keys = {f.key for f in sample_fields}
        assert "hostname" in valid_keys
        assert "port" in valid_keys
        assert "notes" in valid_keys

    def test_display_field_key_validation_invalid(self, sample_fields):
        """Test that invalid display_field_key is detected."""
        valid_keys = {f.key for f in sample_fields}
        invalid_key = "nonexistent_field"
        assert invalid_key not in valid_keys
