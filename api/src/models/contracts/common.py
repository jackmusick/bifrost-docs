"""
Common response models.
"""

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str
    message: str
    details: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = "healthy"
    version: str = "1.0.0"


class BatchToggleRequest(BaseModel):
    """Batch toggle request model."""

    ids: list[str] = Field(..., min_length=1, description="List of entity IDs to toggle")
    is_enabled: bool = Field(..., description="The value to set")


class BatchToggleResponse(BaseModel):
    """Batch toggle response model."""

    updated_count: int = Field(..., description="Number of entities updated")
