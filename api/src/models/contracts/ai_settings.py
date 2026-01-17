"""AI settings API contracts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CompletionsConfigPublic(BaseModel):
    """Public view of completions configuration (API key masked)."""

    model_config = ConfigDict(from_attributes=True)

    provider: Literal["openai", "anthropic", "openai_compatible"] = Field(
        description="LLM provider"
    )
    api_key_set: bool = Field(description="Whether an API key is configured")
    model: str = Field(description="Selected model")
    endpoint: str | None = Field(
        default=None, description="Custom endpoint (for openai_compatible)"
    )


class CompletionsConfigUpdate(BaseModel):
    """Request to update completions configuration."""

    provider: Literal["openai", "anthropic", "openai_compatible"] | None = Field(
        default=None, description="LLM provider"
    )
    api_key: str | None = Field(
        default=None,
        min_length=1,
        description="API key (omit to keep existing)",
    )
    model: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Model name",
    )
    endpoint: str | None = Field(
        default=None,
        description="Custom endpoint (required for openai_compatible)",
    )
    max_tokens: int | None = Field(
        default=None,
        ge=1,
        le=100000,
        description="Max tokens for completions",
    )
    temperature: float | None = Field(
        default=None,
        ge=0,
        le=2,
        description="Temperature for completions",
    )


class EmbeddingsConfigPublic(BaseModel):
    """Public view of embeddings configuration (API key masked)."""

    model_config = ConfigDict(from_attributes=True)

    api_key_set: bool = Field(description="Whether an API key is configured")
    model: str = Field(description="Selected embedding model")


class EmbeddingsConfigUpdate(BaseModel):
    """Request to update embeddings configuration."""

    api_key: str | None = Field(
        default=None,
        min_length=1,
        description="OpenAI API key (omit to keep existing)",
    )
    model: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Embedding model name",
    )


class IndexingConfigPublic(BaseModel):
    """Response model for indexing configuration."""

    enabled: bool = Field(description="Whether automatic search indexing is enabled")


class IndexingConfigUpdate(BaseModel):
    """Request model for updating indexing configuration."""

    enabled: bool = Field(description="Whether to enable automatic search indexing")


class AISettingsResponse(BaseModel):
    """Combined AI settings response."""

    completions: CompletionsConfigPublic | None = Field(
        default=None, description="Completions configuration"
    )
    embeddings: EmbeddingsConfigPublic | None = Field(
        default=None, description="Embeddings configuration"
    )
    indexing: IndexingConfigPublic | None = Field(
        default=None, description="Indexing configuration"
    )


class ModelInfo(BaseModel):
    """Information about an available model."""

    id: str = Field(description="Model identifier")
    display_name: str = Field(description="Human-readable model name")


class ModelsResponse(BaseModel):
    """Response containing available models."""

    models: list[ModelInfo] = Field(description="Available models")


class TestConnectionRequest(BaseModel):
    """Request to test LLM connection."""

    provider: Literal["openai", "anthropic", "openai_compatible"] = Field(
        default="openai", description="Provider to test (defaults to openai)"
    )
    api_key: str = Field(min_length=1, description="API key to test")
    endpoint: str | None = Field(
        default=None, description="Custom endpoint (for openai_compatible)"
    )


class OpenAIModelLegacy(BaseModel):
    """OpenAI model information for legacy frontend compatibility."""

    id: str = Field(description="Model ID")
    name: str = Field(description="Display name")
    description: str = Field(default="", description="Model description")


class TestConnectionResponse(BaseModel):
    """Response from connection test."""

    success: bool = Field(description="Whether connection succeeded")
    message: str = Field(default="", description="Success or error message")
    # Legacy fields for frontend compatibility
    completions_models: list[OpenAIModelLegacy] | None = Field(
        default=None, description="Available completions models"
    )
    embedding_models: list[OpenAIModelLegacy] | None = Field(
        default=None, description="Available embedding models"
    )
    # New field for multi-provider support
    models: list[ModelInfo] = Field(
        default_factory=list, description="Available models (new format)"
    )
    error: str | None = Field(default=None, description="Error message if failed")


