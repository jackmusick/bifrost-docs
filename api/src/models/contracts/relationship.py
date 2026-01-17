"""
Relationship contracts (API request/response schemas).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RelationshipCreate(BaseModel):
    """Relationship creation request model."""

    source_type: str = Field(
        ...,
        description="Entity type: password, configuration, location, document, custom_asset",
    )
    source_id: str = Field(..., description="Source entity UUID")
    target_type: str = Field(
        ...,
        description="Entity type: password, configuration, location, document, custom_asset",
    )
    target_id: str = Field(..., description="Target entity UUID")


class RelationshipPublic(BaseModel):
    """Relationship public response model."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    created_at: datetime


class RelatedEntity(BaseModel):
    """Resolved entity info for display."""

    entity_type: str
    entity_id: str
    name: str


class RelatedItemsResponse(BaseModel):
    """Response containing resolved related entities."""

    items: list[RelatedEntity]
