"""
Configuration contracts (API request/response schemas).

Includes contracts for:
- ConfigurationType
- ConfigurationStatus
- Configuration
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Configuration Type Contracts
# =============================================================================


class ConfigurationTypeCreate(BaseModel):
    """Configuration type creation request model."""

    name: str


class ConfigurationTypePublic(BaseModel):
    """Configuration type public response model (global, not org-scoped)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    is_active: bool
    created_at: datetime
    configuration_count: int = 0


# =============================================================================
# Configuration Status Contracts
# =============================================================================


class ConfigurationStatusCreate(BaseModel):
    """Configuration status creation request model."""

    name: str


class ConfigurationStatusPublic(BaseModel):
    """Configuration status public response model (global, not org-scoped)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    is_active: bool
    created_at: datetime
    configuration_count: int = 0


# =============================================================================
# Configuration Contracts
# =============================================================================


class ConfigurationCreate(BaseModel):
    """Configuration creation request model."""

    name: str
    configuration_type_id: str | None = None
    configuration_status_id: str | None = None
    serial_number: str | None = None
    asset_tag: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    notes: str | None = None
    metadata: dict | None = None
    interfaces: list | None = None
    is_enabled: bool | None = None  # Defaults to True if not provided


class ConfigurationUpdate(BaseModel):
    """Configuration update request model."""

    name: str | None = None
    configuration_type_id: str | None = None
    configuration_status_id: str | None = None
    serial_number: str | None = None
    asset_tag: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    notes: str | None = None
    metadata: dict | None = None
    interfaces: list | None = None
    is_enabled: bool | None = None  # Don't change if not provided


class ConfigurationPublic(BaseModel):
    """Configuration public response model."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    configuration_type_id: str | None
    configuration_status_id: str | None
    name: str
    serial_number: str | None
    asset_tag: str | None
    manufacturer: str | None
    model: str | None
    ip_address: str | None
    mac_address: str | None
    notes: str | None
    metadata: dict = Field(default_factory=dict)
    interfaces: list = Field(default_factory=list)
    is_enabled: bool = True
    created_at: datetime
    updated_at: datetime
    # Nested type and status names for convenience
    configuration_type_name: str | None = None
    configuration_status_name: str | None = None
    updated_by_user_id: str | None = None
    updated_by_user_name: str | None = None
