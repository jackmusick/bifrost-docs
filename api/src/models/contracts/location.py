"""
Location contracts (API request/response schemas).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LocationCreate(BaseModel):
    """Location creation request model."""

    name: str = Field(..., min_length=1, max_length=255)
    notes: str | None = None
    metadata: dict | None = None
    is_enabled: bool | None = None  # Defaults to True if not provided


class LocationUpdate(BaseModel):
    """Location update request model."""

    name: str | None = Field(None, min_length=1, max_length=255)
    notes: str | None = None
    metadata: dict | None = None
    is_enabled: bool | None = None  # Don't change if not provided


class LocationPublic(BaseModel):
    """Location public response model."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    notes: str | None
    metadata: dict = Field(default_factory=dict)
    is_enabled: bool = True
    created_at: datetime
    updated_at: datetime
    updated_by_user_id: str | None = None
    updated_by_user_name: str | None = None
