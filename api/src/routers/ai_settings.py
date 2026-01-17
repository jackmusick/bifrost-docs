"""
AI Settings Router

Provides endpoints for multi-provider AI configuration (OpenAI, Anthropic, OpenAI-compatible).
Only accessible by superusers (platform admins).

Key features:
- Multi-provider support (openai, anthropic, openai_compatible)
- Separate completions and embeddings configuration
- API keys are encrypted using Fernet before storage
- Dynamic model fetching from providers
- Connection testing with model discovery
"""

import logging
import re
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, status

from src.core.auth import CurrentActiveUser
from src.core.database import DbSession
from src.core.security import decrypt_secret, encrypt_secret
from src.models.contracts.ai_settings import (
    AISettingsResponse,
    CompletionsConfigPublic,
    CompletionsConfigUpdate,
    EmbeddingsConfigPublic,
    EmbeddingsConfigUpdate,
    IndexingConfigPublic,
    IndexingConfigUpdate,
    ModelInfo,
    ModelsResponse,
    OpenAIModelLegacy,
    TestConnectionRequest,
    TestConnectionResponse,
)
from src.repositories.system_config import SystemConfigRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings/ai", tags=["ai-settings"])

# Date suffix patterns for model names: -YYYY-MM-DD or -YYYYMMDD
DATE_SUFFIX_PATTERN = re.compile(r"-\d{4}-?\d{2}-?\d{2}$")

# Config keys in SystemConfig table
COMPLETIONS_CONFIG_KEY = "completions_config"
EMBEDDINGS_CONFIG_KEY = "embeddings_config"
INDEXING_CONFIG_KEY = "indexing_config"
LLM_CATEGORY = "llm"

# Default configurations
DEFAULT_COMPLETIONS_CONFIG: dict[str, Any] = {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "api_key_encrypted": None,
    "endpoint": None,
    "max_tokens": 4096,
    "temperature": 0.7,
}

DEFAULT_EMBEDDINGS_CONFIG: dict[str, Any] = {
    "model": "text-embedding-3-small",
    "api_key_encrypted": None,
}


# =============================================================================
# Helper: Require Superuser
# =============================================================================


def require_superuser(user: CurrentActiveUser) -> None:
    """Raise 403 if user is not a superuser."""
    if not user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


# =============================================================================
# Helper: Model Display Names
# =============================================================================


def _get_display_name(model_id: str) -> str:
    """
    Get a user-friendly display name for a model.

    Strips date suffixes and formats nicely:
    - gpt-4o-2024-11-20 -> GPT-4o
    - text-embedding-3-small -> Text Embedding 3 Small
    - claude-3-5-sonnet-20241022 -> Claude 3.5 Sonnet
    """
    # Strip date suffix
    display_name = DATE_SUFFIX_PATTERN.sub("", model_id)

    # Handle GPT models
    if display_name.startswith("gpt-"):
        parts = display_name.split("-")
        parts[0] = "GPT"
        return "-".join(parts[:2]) + (
            " " + " ".join(p.title() for p in parts[2:]) if len(parts) > 2 else ""
        )

    # Handle Claude models
    if display_name.startswith("claude-"):
        return " ".join(word.title() for word in display_name.replace("-", " ").split())

    # Handle o1/o3 models
    if display_name.startswith(("o1", "o3")):
        return display_name.upper().replace("-", " ")

    # Handle embedding models
    if "embedding" in display_name.lower():
        return " ".join(word.title() for word in display_name.replace("-", " ").split())

    return display_name


# =============================================================================
# Helper: Fetch Models from Providers
# =============================================================================


async def _fetch_openai_models(api_key: str) -> list[ModelInfo]:
    """
    Fetch available models from OpenAI API.

    Returns models matching gpt-*, o1*, o3* patterns.
    """
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    models_response = await client.models.list()

    models: list[ModelInfo] = []
    seen_display_names: set[str] = set()

    # Sort by ID descending to get newest versions first
    sorted_models = sorted(models_response.data, key=lambda x: x.id, reverse=True)

    logger.info(
        f"OpenAI returned {len(sorted_models)} models, sample IDs: {[m.id for m in sorted_models[:10]]}"
    )

    for model in sorted_models:
        model_id = model.id

        # Filter for GPT and o-series models
        if model_id.startswith("gpt-") or model_id.startswith(("o1", "o3")):
            # Skip deprecated/special models
            if any(
                x in model_id
                for x in [
                    "instruct",
                    "0301",
                    "0314",
                    "0613",
                    "1106",
                    "vision",
                    "realtime",
                    "audio",
                ]
            ):
                continue

            display_name = _get_display_name(model_id)

            # Only include the newest version of each model
            if display_name in seen_display_names:
                continue
            seen_display_names.add(display_name)

            models.append(ModelInfo(id=model_id, display_name=display_name))

    # Sort by display name for consistent ordering
    models.sort(key=lambda m: m.display_name)

    logger.info(f"Filtered to {len(models)} chat models: {[m.id for m in models]}")

    return models


async def _fetch_anthropic_models(api_key: str) -> list[ModelInfo]:
    """
    Fetch available models from Anthropic API.
    """
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=api_key)
    models_response = await client.models.list()

    models: list[ModelInfo] = []

    for model in models_response.data:
        model_id = model.id
        display_name = _get_display_name(model_id)
        models.append(ModelInfo(id=model_id, display_name=display_name))

    models.sort(key=lambda m: m.display_name)
    return models


async def _fetch_openai_embedding_models(api_key: str) -> list[ModelInfo]:
    """
    Fetch available embedding models from OpenAI API.
    """
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    models_response = await client.models.list()

    models: list[ModelInfo] = []
    seen_display_names: set[str] = set()

    sorted_models = sorted(models_response.data, key=lambda x: x.id, reverse=True)

    for model in sorted_models:
        model_id = model.id

        if "embedding" in model_id:
            display_name = _get_display_name(model_id)

            if display_name in seen_display_names:
                continue
            seen_display_names.add(display_name)

            models.append(ModelInfo(id=model_id, display_name=display_name))

    models.sort(key=lambda m: m.display_name)
    return models


# =============================================================================
# AI Settings Endpoints
# =============================================================================


@router.get("", response_model=AISettingsResponse)
async def get_ai_settings(
    current_user: CurrentActiveUser,
    db: DbSession,
) -> AISettingsResponse:
    """
    Get current AI settings.

    Returns completions and embeddings configurations with masked API keys.
    """
    require_superuser(current_user)

    repo = SystemConfigRepository(db)

    # Get completions config
    completions_config_row = await repo.get_config(LLM_CATEGORY, COMPLETIONS_CONFIG_KEY)
    completions_data: dict[str, Any] = (
        completions_config_row.value_json
        if completions_config_row and completions_config_row.value_json
        else DEFAULT_COMPLETIONS_CONFIG
    )

    completions_public = CompletionsConfigPublic(
        provider=completions_data.get("provider", "openai"),
        api_key_set=completions_data.get("api_key_encrypted") is not None,
        model=completions_data.get("model", "gpt-4o-mini"),
        endpoint=completions_data.get("endpoint"),
    )

    # Get embeddings config
    embeddings_config_row = await repo.get_config(LLM_CATEGORY, EMBEDDINGS_CONFIG_KEY)
    embeddings_data: dict[str, Any] = (
        embeddings_config_row.value_json
        if embeddings_config_row and embeddings_config_row.value_json
        else DEFAULT_EMBEDDINGS_CONFIG
    )

    embeddings_public = EmbeddingsConfigPublic(
        api_key_set=embeddings_data.get("api_key_encrypted") is not None,
        model=embeddings_data.get("model", "text-embedding-3-small"),
    )

    # Get indexing config
    indexing_config_row = await repo.get_config(LLM_CATEGORY, INDEXING_CONFIG_KEY)
    indexing_data: dict[str, Any] = (
        indexing_config_row.value_json
        if indexing_config_row and indexing_config_row.value_json
        else {"enabled": True}  # Default to enabled
    )

    indexing_public = IndexingConfigPublic(
        enabled=indexing_data.get("enabled", True),
    )

    return AISettingsResponse(
        completions=completions_public,
        embeddings=embeddings_public,
        indexing=indexing_public,
    )


@router.put("/completions", response_model=CompletionsConfigPublic)
async def update_completions_config(
    update_data: CompletionsConfigUpdate,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> CompletionsConfigPublic:
    """
    Update completions configuration.

    Merges with existing config (partial updates supported).
    Validates that endpoint is provided for openai_compatible provider.
    """
    require_superuser(current_user)

    repo = SystemConfigRepository(db)

    # Get existing config or defaults
    existing_row = await repo.get_config(LLM_CATEGORY, COMPLETIONS_CONFIG_KEY)
    config: dict[str, Any] = (
        dict(existing_row.value_json)
        if existing_row and existing_row.value_json
        else dict(DEFAULT_COMPLETIONS_CONFIG)
    )

    # Merge updates
    if update_data.provider is not None:
        config["provider"] = update_data.provider
    if update_data.model is not None:
        config["model"] = update_data.model
    if update_data.endpoint is not None:
        config["endpoint"] = update_data.endpoint
    if update_data.max_tokens is not None:
        config["max_tokens"] = update_data.max_tokens
    if update_data.temperature is not None:
        config["temperature"] = update_data.temperature

    # Handle API key - encrypt before storage
    if update_data.api_key is not None:
        config["api_key_encrypted"] = encrypt_secret(update_data.api_key)

    # Validate: endpoint required for openai_compatible
    if config.get("provider") == "openai_compatible" and not config.get("endpoint"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endpoint is required for openai_compatible provider",
        )

    # Save config
    await repo.set_config(LLM_CATEGORY, COMPLETIONS_CONFIG_KEY, config)

    logger.info(
        "Completions config updated",
        extra={
            "user_id": str(current_user.user_id),
            "provider": config.get("provider"),
            "model": config.get("model"),
            "api_key_updated": update_data.api_key is not None,
        },
    )

    return CompletionsConfigPublic(
        provider=config.get("provider", "openai"),
        api_key_set=config.get("api_key_encrypted") is not None,
        model=config.get("model", "gpt-4o-mini"),
        endpoint=config.get("endpoint"),
    )


@router.put("/embeddings", response_model=EmbeddingsConfigPublic)
async def update_embeddings_config(
    update_data: EmbeddingsConfigUpdate,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> EmbeddingsConfigPublic:
    """
    Update embeddings configuration.

    Merges with existing config (partial updates supported).
    """
    require_superuser(current_user)

    repo = SystemConfigRepository(db)

    # Get existing config or defaults
    existing_row = await repo.get_config(LLM_CATEGORY, EMBEDDINGS_CONFIG_KEY)
    config: dict[str, Any] = (
        dict(existing_row.value_json)
        if existing_row and existing_row.value_json
        else dict(DEFAULT_EMBEDDINGS_CONFIG)
    )

    # Merge updates
    if update_data.model is not None:
        config["model"] = update_data.model

    # Handle API key - encrypt before storage
    if update_data.api_key is not None:
        config["api_key_encrypted"] = encrypt_secret(update_data.api_key)

    # Save config
    await repo.set_config(LLM_CATEGORY, EMBEDDINGS_CONFIG_KEY, config)

    logger.info(
        "Embeddings config updated",
        extra={
            "user_id": str(current_user.user_id),
            "model": config.get("model"),
            "api_key_updated": update_data.api_key is not None,
        },
    )

    return EmbeddingsConfigPublic(
        api_key_set=config.get("api_key_encrypted") is not None,
        model=config.get("model", "text-embedding-3-small"),
    )


@router.get("/indexing", response_model=IndexingConfigPublic)
async def get_indexing_config(
    current_user: CurrentActiveUser,
    db: DbSession,
) -> IndexingConfigPublic:
    """
    Get current indexing configuration.

    Returns whether automatic search indexing is enabled.
    """
    require_superuser(current_user)

    repo = SystemConfigRepository(db)

    # Get indexing config
    indexing_config_row = await repo.get_config(LLM_CATEGORY, INDEXING_CONFIG_KEY)
    indexing_data: dict[str, Any] = (
        indexing_config_row.value_json
        if indexing_config_row and indexing_config_row.value_json
        else {"enabled": True}  # Default to enabled
    )

    return IndexingConfigPublic(
        enabled=indexing_data.get("enabled", True),
    )


@router.put("/indexing", response_model=IndexingConfigPublic)
async def update_indexing_config(
    update_data: IndexingConfigUpdate,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> IndexingConfigPublic:
    """
    Update indexing configuration.

    Controls whether automatic search indexing is enabled for new documents.
    """
    require_superuser(current_user)

    repo = SystemConfigRepository(db)

    # Create new config with enabled flag
    config: dict[str, Any] = {"enabled": update_data.enabled}

    # Save config
    await repo.set_config(LLM_CATEGORY, INDEXING_CONFIG_KEY, config)

    logger.info(
        "Indexing config updated",
        extra={
            "user_id": str(current_user.user_id),
            "enabled": update_data.enabled,
        },
    )

    return IndexingConfigPublic(enabled=update_data.enabled)


@router.get("/models", response_model=ModelsResponse)
async def list_available_models(
    current_user: CurrentActiveUser,
    db: DbSession,
    provider: Literal["openai", "anthropic", "openai_compatible", "embeddings"] = Query(
        ..., description="Provider to fetch models for (or 'embeddings' for embedding models)"
    ),
    api_key: str | None = Query(
        default=None, description="API key to use (if not provided, uses stored key)"
    ),
) -> ModelsResponse:
    """
    Fetch available models from a provider.

    For openai: returns gpt-*, o1*, o3* models.
    For anthropic: returns Claude models.
    For openai_compatible: returns empty list (user enters manually).
    For embeddings: returns OpenAI embedding models.
    """
    require_superuser(current_user)

    # For openai_compatible, return empty list
    if provider == "openai_compatible":
        return ModelsResponse(models=[])

    # Get API key from parameter or stored config
    key_to_use = api_key
    if not key_to_use:
        repo = SystemConfigRepository(db)

        if provider == "embeddings":
            # Use embeddings config key
            config_row = await repo.get_config(LLM_CATEGORY, EMBEDDINGS_CONFIG_KEY)
        else:
            # Use completions config key
            config_row = await repo.get_config(LLM_CATEGORY, COMPLETIONS_CONFIG_KEY)

        if (
            config_row
            and config_row.value_json
            and config_row.value_json.get("api_key_encrypted")
        ):
            key_to_use = decrypt_secret(config_row.value_json["api_key_encrypted"])

    if not key_to_use:
        # Return curated list for OpenAI if no key
        if provider == "openai":
            return ModelsResponse(
                models=[
                    ModelInfo(id="gpt-4o", display_name="GPT-4o"),
                    ModelInfo(id="gpt-4o-mini", display_name="GPT-4o Mini"),
                    ModelInfo(id="gpt-4-turbo", display_name="GPT-4 Turbo"),
                    ModelInfo(id="gpt-3.5-turbo", display_name="GPT-3.5 Turbo"),
                    ModelInfo(id="o1", display_name="O1"),
                    ModelInfo(id="o1-mini", display_name="O1 Mini"),
                ]
            )
        elif provider == "embeddings":
            return ModelsResponse(
                models=[
                    ModelInfo(id="text-embedding-3-small", display_name="Text Embedding 3 Small"),
                    ModelInfo(id="text-embedding-3-large", display_name="Text Embedding 3 Large"),
                    ModelInfo(id="text-embedding-ada-002", display_name="Text Embedding Ada 002"),
                ]
            )
        elif provider == "anthropic":
            return ModelsResponse(
                models=[
                    ModelInfo(id="claude-3-5-sonnet-latest", display_name="Claude 3.5 Sonnet"),
                    ModelInfo(id="claude-3-5-haiku-latest", display_name="Claude 3.5 Haiku"),
                    ModelInfo(id="claude-3-opus-latest", display_name="Claude 3 Opus"),
                ]
            )
        return ModelsResponse(models=[])

    try:
        if provider == "openai":
            models = await _fetch_openai_models(key_to_use)
        elif provider == "anthropic":
            models = await _fetch_anthropic_models(key_to_use)
        elif provider == "embeddings":
            models = await _fetch_openai_embedding_models(key_to_use)
        else:
            models = []

        return ModelsResponse(models=models)

    except Exception as e:
        logger.warning(f"Failed to fetch models from {provider}: {e}")
        # Fall back to curated list on error
        if provider == "openai":
            return ModelsResponse(
                models=[
                    ModelInfo(id="gpt-4o", display_name="GPT-4o"),
                    ModelInfo(id="gpt-4o-mini", display_name="GPT-4o Mini"),
                ]
            )
        elif provider == "embeddings":
            return ModelsResponse(
                models=[
                    ModelInfo(id="text-embedding-3-small", display_name="Text Embedding 3 Small"),
                    ModelInfo(id="text-embedding-3-large", display_name="Text Embedding 3 Large"),
                ]
            )
        return ModelsResponse(models=[])


def _model_info_to_legacy(model: ModelInfo) -> OpenAIModelLegacy:
    """Convert ModelInfo to legacy OpenAIModelLegacy format."""
    return OpenAIModelLegacy(
        id=model.id,
        name=model.display_name,
        description="",
    )


@router.post("/test", response_model=TestConnectionResponse)
async def test_ai_connection(
    test_request: TestConnectionRequest,
    current_user: CurrentActiveUser,
) -> TestConnectionResponse:
    """
    Test connection to an AI provider and return available models.

    Validates the API key by attempting to list models from the provider.
    Returns both completions_models and embedding_models for OpenAI provider
    for frontend compatibility.
    """
    require_superuser(current_user)

    # Validate: endpoint required for openai_compatible
    if test_request.provider == "openai_compatible" and not test_request.endpoint:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endpoint is required for openai_compatible provider",
        )

    try:
        completions_models: list[ModelInfo] = []
        embedding_models: list[ModelInfo] = []

        if test_request.provider == "openai":
            # Fetch both chat and embedding models for OpenAI
            completions_models = await _fetch_openai_models(test_request.api_key)
            embedding_models = await _fetch_openai_embedding_models(test_request.api_key)
        elif test_request.provider == "anthropic":
            completions_models = await _fetch_anthropic_models(test_request.api_key)
            # Anthropic doesn't have embedding models
        elif test_request.provider == "openai_compatible":
            # For openai_compatible, try to connect to the endpoint
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=test_request.api_key,
                base_url=test_request.endpoint,
            )
            # Try to list models - may not be supported by all providers
            try:
                models_response = await client.models.list()
                completions_models = [
                    ModelInfo(id=m.id, display_name=_get_display_name(m.id))
                    for m in models_response.data
                ]
            except Exception:
                # If models.list() not supported, return empty but success
                pass

        total_models = len(completions_models) + len(embedding_models)

        logger.info(
            "AI connection test successful",
            extra={
                "user_id": str(current_user.user_id),
                "provider": test_request.provider,
                "completions_count": len(completions_models),
                "embedding_count": len(embedding_models),
            },
        )

        # Build success message
        if test_request.provider == "openai":
            message = f"Connected! Found {len(completions_models)} chat models and {len(embedding_models)} embedding models."
        elif test_request.provider == "anthropic":
            message = f"Connected! Found {len(completions_models)} models."
        else:
            message = f"Connected! Found {total_models} models."

        return TestConnectionResponse(
            success=True,
            message=message,
            # Legacy format for frontend compatibility
            completions_models=[_model_info_to_legacy(m) for m in completions_models],
            embedding_models=[_model_info_to_legacy(m) for m in embedding_models],
            # New format
            models=completions_models,
        )

    except Exception as e:
        error_message = str(e)

        # Clean up common error messages
        if "Incorrect API key" in error_message or "invalid_api_key" in error_message:
            error_message = "Invalid API key"
        elif "authentication" in error_message.lower():
            error_message = "Authentication failed - check your API key"
        elif "Rate limit" in error_message:
            error_message = "Rate limit exceeded - please try again later"
        elif "Connection" in error_message or "timeout" in error_message.lower():
            error_message = "Connection failed - please check your network"

        logger.warning(
            f"AI connection test failed: {error_message}",
            extra={
                "user_id": str(current_user.user_id),
                "provider": test_request.provider,
            },
        )

        return TestConnectionResponse(
            success=False,
            message=error_message,
            models=[],
            error=error_message,
        )
