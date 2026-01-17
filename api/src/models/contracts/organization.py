"""
Organization contracts (API request/response schemas).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.models.contracts.access_tracking import FrequentItem


class OrganizationCreate(BaseModel):
    """Organization creation request model."""

    name: str
    metadata: dict | None = None
    is_enabled: bool | None = None  # Defaults to True if not provided


class OrganizationUpdate(BaseModel):
    """Organization update request model."""

    name: str | None = None
    metadata: dict | None = None
    is_enabled: bool | None = None  # Don't change if not provided


class OrganizationPublic(BaseModel):
    """Organization public response model."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    metadata: dict = Field(default_factory=dict)
    is_enabled: bool = True
    created_at: datetime
    updated_at: datetime
    updated_by_user_id: str | None = None
    updated_by_user_name: str | None = None


class OrganizationWithFrequent(OrganizationPublic):
    """Organization with optional frequently accessed entities."""

    frequently_accessed: list[FrequentItem] | None = None


# =============================================================================
# Sidebar Data Contracts
# =============================================================================


class SidebarItemCount(BaseModel):
    """Count for a sidebar navigation item."""

    id: str
    name: str
    count: int


class SidebarData(BaseModel):
    """
    Sidebar navigation data for an organization.

    Contains counts for core entities and dynamic types
    (configuration types and custom asset types).
    """

    # Core entity counts
    passwords_count: int
    locations_count: int
    documents_count: int

    # Dynamic types with counts
    configuration_types: list[SidebarItemCount]
    custom_asset_types: list[SidebarItemCount]
