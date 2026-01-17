"""
Access Tracking Contract Models.

Pydantic models for tracking recently and frequently accessed entities.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RecentItem(BaseModel):
    """A recently accessed entity."""

    entity_type: str
    entity_id: UUID
    organization_id: UUID | None
    org_name: str | None
    name: str
    viewed_at: datetime


class FrequentItem(BaseModel):
    """A frequently accessed entity within an organization."""

    entity_type: str
    entity_id: UUID
    name: str
    view_count: int
