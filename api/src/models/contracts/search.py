"""
Search contracts (API request/response schemas).

Defines the request and response models for semantic search.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SearchResult(BaseModel):
    """Individual search result with entity metadata."""

    model_config = ConfigDict(from_attributes=True)

    entity_type: Literal["password", "configuration", "location", "document", "custom_asset"]
    entity_id: str
    organization_id: str
    organization_name: str  # For display when searching across orgs
    name: str  # Entity name
    snippet: str  # Excerpt from searchable_text
    score: float = Field(ge=0.0, le=1.0)  # Similarity score (0-1, higher is better)
    is_enabled: bool = True  # Whether the entity is enabled (for display purposes)


class SearchResponse(BaseModel):
    """Search response containing query and results."""

    model_config = ConfigDict(from_attributes=True)

    query: str
    results: list[SearchResult]


# =============================================================================
# AI Search (RAG) Contracts
# =============================================================================


class AISearchRequest(BaseModel):
    """Request body for AI-powered search."""

    query: str = Field(..., min_length=1, max_length=1000, description="Natural language query")
    org_id: UUID | None = Field(None, description="Optional organization filter")


class AISearchCitation(BaseModel):
    """Citation reference to a source entity."""

    entity_type: Literal["password", "configuration", "location", "document", "custom_asset"]
    entity_id: str
    organization_id: str
    name: str


class AISearchResponse(BaseModel):
    """Response for AI search (used for non-streaming fallback)."""

    query: str
    response: str
    citations: list[AISearchCitation]


class AISearchStartResponse(BaseModel):
    """Response when AI search job is started (WebSocket streaming mode)."""

    request_id: str = Field(..., description="Unique request ID to subscribe to via WebSocket")
