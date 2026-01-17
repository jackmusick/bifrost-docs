"""
User Preferences contracts (API request/response schemas).

Defines the schemas for persisting user UI preferences like column visibility,
order, and widths for DataTable components.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ColumnPreferences(BaseModel):
    """Column-specific preferences for a DataTable."""

    visible: list[str] = Field(
        default_factory=list,
        description="List of visible column IDs in display order",
    )
    order: list[str] = Field(
        default_factory=list,
        description="Order of all columns (visible and hidden)",
    )
    widths: dict[str, int] = Field(
        default_factory=dict,
        description="Column widths by column ID (in pixels)",
    )


class PreferencesData(BaseModel):
    """
    User preferences data structure.

    Stores column preferences for DataTable components.
    Extensible to support additional preference types in the future.
    """

    columns: ColumnPreferences = Field(
        default_factory=ColumnPreferences,
        description="Column visibility, order, and width preferences",
    )


class UserPreferencesCreate(BaseModel):
    """Request schema for creating user preferences."""

    entity_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Entity type identifier (e.g., 'passwords', 'configurations', 'custom_asset_{uuid}')",
    )
    preferences: PreferencesData = Field(
        ...,
        description="Preferences data to store",
    )


class UserPreferencesUpdate(BaseModel):
    """Request schema for updating user preferences."""

    preferences: PreferencesData = Field(
        ...,
        description="Updated preferences data",
    )


class UserPreferencesPublic(BaseModel):
    """Response schema for user preferences."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Preference record ID")
    user_id: UUID = Field(description="User ID")
    entity_type: str = Field(description="Entity type identifier")
    preferences: dict[str, Any] = Field(description="Preferences data")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class UserPreferencesResponse(BaseModel):
    """Response wrapper for preferences (returns empty defaults if not found)."""

    entity_type: str = Field(description="Entity type identifier")
    preferences: PreferencesData = Field(description="Preferences data (or defaults)")
