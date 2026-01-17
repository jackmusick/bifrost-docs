"""
Password contracts (API request/response schemas).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PasswordCreate(BaseModel):
    """Password creation request model."""

    name: str = Field(..., min_length=1, max_length=255)
    username: str | None = Field(default=None, max_length=255)
    password: str = Field(..., min_length=1)
    totp_secret: str | None = None
    url: str | None = Field(default=None, max_length=2048)
    notes: str | None = None
    metadata: dict | None = None
    is_enabled: bool | None = None  # Defaults to True if not provided


class PasswordUpdate(BaseModel):
    """Password update request model."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    username: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=1)
    totp_secret: str | None = None
    url: str | None = Field(default=None, max_length=2048)
    notes: str | None = None
    metadata: dict | None = None
    is_enabled: bool | None = None  # Don't change if not provided


class PasswordPublic(BaseModel):
    """Password public response model (without password value)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    username: str | None
    url: str | None
    notes: str | None
    has_totp: bool = False
    metadata: dict = Field(default_factory=dict)
    is_enabled: bool = True
    created_at: datetime
    updated_at: datetime
    updated_by_user_id: str | None = None
    updated_by_user_name: str | None = None


class PasswordReveal(PasswordPublic):
    """Password response model with decrypted password and TOTP secret."""

    password: str
    totp_secret: str | None = None
