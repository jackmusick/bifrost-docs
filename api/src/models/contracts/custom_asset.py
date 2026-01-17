"""
Custom Asset contracts (API request/response schemas).

Defines field definitions for custom asset types and the contracts
for both custom asset types and custom asset instances.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# =============================================================================
# Field Definition Schema
# =============================================================================


class FieldDefinition(BaseModel):
    """
    Definition of a single field in a custom asset type.

    This defines the schema for fields that can be added to custom asset types.
    """

    model_config = ConfigDict(extra="forbid")

    key: str  # unique identifier within type
    name: str  # display name
    type: Literal[
        "text", "textbox", "number", "date", "checkbox", "select", "header", "password", "totp"
    ]
    required: bool = False
    show_in_list: bool = False
    hint: str | None = None
    default_value: str | None = None
    options: list[str] | None = None  # required for select type

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: list[str] | None, info) -> list[str] | None:
        """Validate that select type has options."""
        field_type = info.data.get("type")
        if field_type == "select" and (not v or len(v) == 0):
            raise ValueError("Select field type requires options")
        return v


# =============================================================================
# Custom Asset Type Contracts
# =============================================================================


class CustomAssetTypeCreate(BaseModel):
    """Custom asset type creation request model."""

    model_config = ConfigDict(extra="forbid")

    name: str
    fields: list[FieldDefinition]
    display_field_key: str | None = None

    @field_validator("fields")
    @classmethod
    def validate_unique_keys(cls, v: list[FieldDefinition]) -> list[FieldDefinition]:
        """Validate that all field keys are unique."""
        keys = [f.key for f in v]
        if len(keys) != len(set(keys)):
            raise ValueError("Field keys must be unique within a custom asset type")
        return v


class CustomAssetTypeUpdate(BaseModel):
    """Custom asset type update request model."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    fields: list[FieldDefinition] | None = None
    display_field_key: str | None = None

    @field_validator("fields")
    @classmethod
    def validate_unique_keys(
        cls, v: list[FieldDefinition] | None
    ) -> list[FieldDefinition] | None:
        """Validate that all field keys are unique."""
        if v is None:
            return v
        keys = [f.key for f in v]
        if len(keys) != len(set(keys)):
            raise ValueError("Field keys must be unique within a custom asset type")
        return v


class CustomAssetTypeReorder(BaseModel):
    """Custom asset type reorder request model."""

    model_config = ConfigDict(extra="forbid")

    ids: list[str]  # Ordered list of custom asset type IDs


class CustomAssetTypePublic(BaseModel):
    """Custom asset type public response model (global, not org-scoped)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    fields: list[FieldDefinition]
    sort_order: int = 0
    display_field_key: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    asset_count: int = 0


# =============================================================================
# Custom Asset Instance Contracts
# =============================================================================


class CustomAssetCreate(BaseModel):
    """Custom asset creation request model."""

    model_config = ConfigDict(extra="forbid")

    values: dict[str, Any]  # validated against type's fields in service layer
    metadata: dict | None = None
    is_enabled: bool | None = None  # Defaults to True if not provided


class CustomAssetUpdate(BaseModel):
    """Custom asset update request model."""

    model_config = ConfigDict(extra="forbid")

    values: dict[str, Any] | None = None  # validated against type's fields in service layer
    metadata: dict | None = None
    is_enabled: bool | None = None  # Don't change if not provided


class CustomAssetPublic(BaseModel):
    """
    Custom asset public response model.

    Password fields are excluded from values.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    custom_asset_type_id: str
    values: dict[str, Any]  # password fields excluded
    metadata: dict = Field(default_factory=dict)
    is_enabled: bool = True
    created_at: datetime
    updated_at: datetime
    updated_by_user_id: str | None = None
    updated_by_user_name: str | None = None


class CustomAssetReveal(BaseModel):
    """
    Custom asset reveal response model.

    Includes decrypted password field values.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    custom_asset_type_id: str
    values: dict[str, Any]  # includes decrypted password fields
    metadata: dict = Field(default_factory=dict)
    is_enabled: bool = True
    created_at: datetime
    updated_at: datetime
    updated_by_user_id: str | None = None
    updated_by_user_name: str | None = None
