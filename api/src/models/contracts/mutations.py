"""Mutation request/response contracts."""
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentMutation(BaseModel):
    """Mutation for a document."""

    content: str = Field(..., description="Updated document content (markdown)")
    summary: str = Field(..., min_length=1, max_length=500, description="TL;DR of changes")


class AssetMutation(BaseModel):
    """Mutation for a custom asset."""

    field_updates: dict[str, str] = Field(..., min_length=1, description="Field name to new value mapping")
    summary: str = Field(..., min_length=1, max_length=500, description="TL;DR of changes")


class MutationPreview(BaseModel):
    """Preview of a mutation before applying."""

    entity_type: Literal["document", "custom_asset"] = Field(..., description="Type of entity")
    entity_id: UUID = Field(..., description="ID of entity to mutate")
    organization_id: UUID = Field(..., description="Organization ID")
    mutation: Union[DocumentMutation, AssetMutation] = Field(...)


class ApplyMutationRequest(BaseModel):
    """Request to apply a previewed mutation."""

    conversation_id: str = Field(..., description="Conversation ID from chat")
    request_id: str = Field(..., description="Request ID from preview message")
    entity_type: Literal["document", "custom_asset"] = Field(..., description="Type of entity")
    entity_id: UUID = Field(..., description="ID of entity to mutate")
    organization_id: UUID = Field(..., description="Organization ID")
    mutation: Union[DocumentMutation, AssetMutation] = Field(...)


class ApplyMutationResponse(BaseModel):
    """Response after applying a mutation."""

    success: bool = Field(..., description="Whether mutation was applied")
    entity_id: UUID = Field(..., description="ID of mutated entity")
    link: str = Field(..., description="Link to entity (entity:// format)")
    error: str | None = Field(None, description="Error message if failed")
