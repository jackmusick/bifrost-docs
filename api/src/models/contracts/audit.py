"""
Audit log contracts (API request/response schemas).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditLogEntry(BaseModel):
    """Single audit log entry for API response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str | None = None
    organization_name: str | None = None
    action: str
    entity_type: str
    entity_id: str
    entity_name: str | None = Field(default=None, description="Resolved from entity if available")
    actor_type: str
    actor_user_id: str | None = None
    actor_display_name: str | None = Field(
        default=None, description="User email/name or API key name"
    )
    actor_label: str | None = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    """Paginated response for audit log list."""

    items: list[AuditLogEntry]
    total: int = Field(..., description="Total number of audit log entries matching the query")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")


class AuditLogFilters(BaseModel):
    """Query filters for audit logs."""

    organization_id: UUID | None = Field(default=None, description="Filter by organization")
    entity_type: str | None = Field(default=None, description="Filter by entity type")
    entity_id: UUID | None = Field(default=None, description="Filter by specific entity")
    action: str | None = Field(default=None, description="Filter by action type")
    actor_user_id: UUID | None = Field(default=None, description="Filter by actor user")
    start_date: datetime | None = Field(default=None, description="Filter entries after this date")
    end_date: datetime | None = Field(default=None, description="Filter entries before this date")
