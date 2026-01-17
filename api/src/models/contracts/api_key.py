"""
API Key contracts (API request/response schemas).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyCreate(BaseModel):
    """API key creation request model."""

    name: str = Field(..., min_length=1, max_length=255, description="Display name for the API key")
    expires_at: datetime | None = Field(
        default=None, description="Optional expiration date (None = never expires)"
    )


class ApiKeyPublic(BaseModel):
    """API key public response model (without the key value)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime


class ApiKeyCreated(ApiKeyPublic):
    """API key response model returned only on creation (includes the full key)."""

    key: str = Field(..., description="The full API key. Store it securely - it cannot be retrieved again.")
