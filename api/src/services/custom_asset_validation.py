"""
Custom Asset Validation Service.

Provides validation, encryption, and filtering functions for custom asset values.
"""

from datetime import datetime
from typing import Any

from src.core.security import decrypt_secret, encrypt_secret
from src.models.contracts.custom_asset import FieldDefinition


class CustomAssetValidationError(ValueError):
    """Exception raised when custom asset validation fails."""

    def __init__(self, message: str, field_key: str | None = None):
        self.field_key = field_key
        super().__init__(message)


def validate_field_definitions(fields: list[FieldDefinition]) -> None:
    """
    Validate field definitions for a custom asset type.

    Args:
        fields: List of field definitions to validate

    Raises:
        CustomAssetValidationError: If validation fails
    """
    keys = [f.key for f in fields]
    if len(keys) != len(set(keys)):
        raise CustomAssetValidationError("Field keys must be unique within a custom asset type")

    for field in fields:
        # Validate select type has options
        if field.type == "select" and (not field.options or len(field.options) == 0):
            raise CustomAssetValidationError(
                f"Select field '{field.key}' requires options",
                field_key=field.key,
            )


def validate_values(
    type_fields: list[FieldDefinition],
    values: dict[str, Any],
    partial: bool = False,
) -> None:
    """
    Validate values against a custom asset type's field definitions.

    Args:
        type_fields: List of field definitions from the custom asset type
        values: Dictionary of values to validate
        partial: If True, skip required field validation (for updates)

    Raises:
        CustomAssetValidationError: If validation fails
    """
    field_map = {f.key: f for f in type_fields}
    valid_keys = set(field_map.keys())

    # Check for unknown keys
    provided_keys = set(values.keys())
    unknown_keys = provided_keys - valid_keys
    if unknown_keys:
        raise CustomAssetValidationError(
            f"Unknown field keys: {', '.join(sorted(unknown_keys))}"
        )

    # Validate each provided value
    for key, value in values.items():
        field = field_map[key]
        _validate_field_value(field, value)

    # Check required fields (skip headers which are display-only)
    if not partial:
        for field in type_fields:
            if field.required and field.type != "header":
                if field.key not in values or values[field.key] is None:
                    raise CustomAssetValidationError(
                        f"Required field '{field.key}' is missing",
                        field_key=field.key,
                    )


def _validate_field_value(field: FieldDefinition, value: Any) -> None:
    """
    Validate a single field value against its definition.

    Args:
        field: Field definition
        value: Value to validate

    Raises:
        CustomAssetValidationError: If validation fails
    """
    # Allow None for optional fields
    if value is None:
        if field.required and field.type != "header":
            raise CustomAssetValidationError(
                f"Required field '{field.key}' cannot be null",
                field_key=field.key,
            )
        return

    # Type-specific validation
    match field.type:
        case "text" | "textbox" | "password" | "totp":
            if not isinstance(value, str):
                raise CustomAssetValidationError(
                    f"Field '{field.key}' must be a string",
                    field_key=field.key,
                )
        case "number":
            if not isinstance(value, (int, float)):
                raise CustomAssetValidationError(
                    f"Field '{field.key}' must be a number",
                    field_key=field.key,
                )
        case "date":
            if not isinstance(value, str):
                raise CustomAssetValidationError(
                    f"Field '{field.key}' must be a date string",
                    field_key=field.key,
                )
            # Try to parse the date
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as e:
                raise CustomAssetValidationError(
                    f"Field '{field.key}' must be a valid ISO date string: {e}",
                    field_key=field.key,
                ) from e
        case "checkbox":
            if not isinstance(value, bool):
                raise CustomAssetValidationError(
                    f"Field '{field.key}' must be a boolean",
                    field_key=field.key,
                )
        case "select":
            if not isinstance(value, str):
                raise CustomAssetValidationError(
                    f"Field '{field.key}' must be a string",
                    field_key=field.key,
                )
            if field.options and value not in field.options:
                raise CustomAssetValidationError(
                    f"Field '{field.key}' must be one of: {', '.join(field.options)}",
                    field_key=field.key,
                )
        case "header":
            # Headers don't have values
            pass


def encrypt_password_fields(
    type_fields: list[FieldDefinition],
    values: dict[str, Any],
) -> dict[str, Any]:
    """
    Encrypt password and totp field values for storage.

    Args:
        type_fields: List of field definitions from the custom asset type
        values: Dictionary of values (will be modified in place)

    Returns:
        Values dictionary with password/totp fields encrypted and stored with "_encrypted" suffix
    """
    result = values.copy()
    secret_keys = {f.key for f in type_fields if f.type in ("password", "totp")}

    for key in list(result.keys()):
        if key in secret_keys and result[key] is not None:
            # Encrypt the value
            encrypted = encrypt_secret(str(result[key]))
            # Remove the plain value and store encrypted with suffix
            del result[key]
            result[f"{key}_encrypted"] = encrypted

    return result


def decrypt_password_fields(
    type_fields: list[FieldDefinition],
    values: dict[str, Any],
) -> dict[str, Any]:
    """
    Decrypt password and totp field values for reveal endpoint.

    Args:
        type_fields: List of field definitions from the custom asset type
        values: Dictionary of values from database

    Returns:
        Values dictionary with password/totp fields decrypted and restored to original keys
    """
    result = values.copy()
    secret_keys = {f.key for f in type_fields if f.type in ("password", "totp")}

    for key in secret_keys:
        encrypted_key = f"{key}_encrypted"
        if encrypted_key in result:
            # Decrypt the value
            decrypted = decrypt_secret(result[encrypted_key])
            # Remove encrypted key and restore original
            del result[encrypted_key]
            result[key] = decrypted

    return result


def filter_password_fields(
    type_fields: list[FieldDefinition],
    values: dict[str, Any],
) -> dict[str, Any]:
    """
    Remove password and totp values from response (for public endpoint).

    Args:
        type_fields: List of field definitions from the custom asset type
        values: Dictionary of values from database

    Returns:
        Values dictionary with password/totp fields removed (both plain and encrypted)
    """
    result = values.copy()
    secret_keys = {f.key for f in type_fields if f.type in ("password", "totp")}

    for key in secret_keys:
        # Remove plain key if present
        result.pop(key, None)
        # Remove encrypted key if present
        result.pop(f"{key}_encrypted", None)

    return result


def apply_default_values(
    type_fields: list[FieldDefinition],
    values: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply default values for fields not provided.

    Args:
        type_fields: List of field definitions from the custom asset type
        values: Dictionary of provided values

    Returns:
        Values dictionary with defaults applied for missing fields
    """
    result = values.copy()

    for field in type_fields:
        if field.key not in result and field.default_value is not None:
            # Convert default value to appropriate type
            match field.type:
                case "checkbox":
                    result[field.key] = field.default_value.lower() == "true"
                case "number":
                    try:
                        result[field.key] = float(field.default_value)
                    except ValueError:
                        result[field.key] = field.default_value
                case _:
                    result[field.key] = field.default_value

    return result
