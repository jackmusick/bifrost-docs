"""Factory for creating LLM clients based on configuration."""
import logging
from dataclasses import dataclass
from enum import Enum

from cryptography.fernet import InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import decrypt_secret
from src.models.orm.system_config import SystemConfig
from src.services.llm.anthropic_client import AnthropicClient
from src.services.llm.base import BaseLLMClient
from src.services.llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

# Constants for database queries
LLM_CATEGORY = "llm"
COMPLETIONS_CONFIG_KEY = "completions_config"
EMBEDDINGS_CONFIG_KEY = "embeddings_config"
INDEXING_CONFIG_KEY = "indexing_config"


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENAI_COMPATIBLE = "openai_compatible"


@dataclass
class CompletionsConfig:
    """Configuration for completions/chat LLM."""

    provider: LLMProvider
    api_key: str  # Decrypted
    model: str
    endpoint: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class EmbeddingsConfig:
    """Configuration for embeddings."""

    api_key: str  # Decrypted
    model: str = "text-embedding-3-small"


async def get_completions_config(session: AsyncSession) -> CompletionsConfig | None:
    """Load and decrypt completions config from database.

    Returns:
        CompletionsConfig if valid config exists and can be decrypted, None otherwise.
    """
    result = await session.execute(
        select(SystemConfig).where(
            SystemConfig.category == LLM_CATEGORY,
            SystemConfig.key == COMPLETIONS_CONFIG_KEY,
        )
    )
    config = result.scalar_one_or_none()

    if config is None or config.value_json is None:
        return None

    value = config.value_json

    # Validate required fields
    if "api_key_encrypted" not in value:
        logger.error("Completions config missing required 'api_key_encrypted' field")
        return None

    # Attempt decryption with error handling
    try:
        api_key = decrypt_secret(value["api_key_encrypted"])
    except (InvalidToken, ValueError) as e:
        logger.error("Failed to decrypt completions API key: %s", e)
        return None

    return CompletionsConfig(
        provider=LLMProvider(value["provider"]),
        api_key=api_key,
        model=value["model"],
        endpoint=value.get("endpoint"),
        max_tokens=value.get("max_tokens", 4096),
        temperature=value.get("temperature", 0.7),
    )


async def get_embeddings_config(session: AsyncSession) -> EmbeddingsConfig | None:
    """Load and decrypt embeddings config from database.

    Returns:
        EmbeddingsConfig if valid config exists and can be decrypted, None otherwise.
    """
    result = await session.execute(
        select(SystemConfig).where(
            SystemConfig.category == LLM_CATEGORY,
            SystemConfig.key == EMBEDDINGS_CONFIG_KEY,
        )
    )
    config = result.scalar_one_or_none()

    if config is None or config.value_json is None:
        return None

    value = config.value_json

    # Validate required fields
    if "api_key_encrypted" not in value:
        logger.error("Embeddings config missing required 'api_key_encrypted' field")
        return None

    # Attempt decryption with error handling
    try:
        api_key = decrypt_secret(value["api_key_encrypted"])
    except (InvalidToken, ValueError) as e:
        logger.error("Failed to decrypt embeddings API key: %s", e)
        return None

    return EmbeddingsConfig(
        api_key=api_key,
        model=value.get("model", "text-embedding-3-small"),
    )


async def is_indexing_enabled(session: AsyncSession) -> bool:
    """Check if automatic search indexing is enabled.

    The indexing setting is stored in SystemConfig under llm/indexing_config.
    Returns True by default if no configuration exists.

    Args:
        session: Database session.

    Returns:
        True if indexing is enabled, False otherwise.
    """
    result = await session.execute(
        select(SystemConfig).where(
            SystemConfig.category == LLM_CATEGORY,
            SystemConfig.key == INDEXING_CONFIG_KEY,
        )
    )
    config = result.scalar_one_or_none()

    if config is None or config.value_json is None:
        # Default to enabled if no config exists
        return True

    return config.value_json.get("enabled", True)


def get_llm_client(config: CompletionsConfig) -> BaseLLMClient:
    """Create an LLM client based on configuration.

    Args:
        config: Completions configuration with provider, API key, and model.

    Returns:
        Configured LLM client instance.

    Raises:
        ValueError: If the provider is not supported.
    """
    match config.provider:
        case LLMProvider.OPENAI:
            return OpenAIClient(config.api_key, config.model, None)
        case LLMProvider.ANTHROPIC:
            return AnthropicClient(config.api_key, config.model)
        case LLMProvider.OPENAI_COMPATIBLE:
            return OpenAIClient(config.api_key, config.model, config.endpoint)
        case _:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")
