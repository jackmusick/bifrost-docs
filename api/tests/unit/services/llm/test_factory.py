"""Tests for LLM factory."""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from cryptography.fernet import InvalidToken

from src.services.llm.factory import (
    CompletionsConfig,
    LLMProvider,
    get_completions_config,
    get_embeddings_config,
    get_llm_client,
    is_indexing_enabled,
)


@pytest.mark.unit
class TestLLMProvider:
    """Tests for LLMProvider enum."""

    def test_provider_values(self):
        """Test provider enum values."""
        assert LLMProvider.OPENAI == "openai"
        assert LLMProvider.ANTHROPIC == "anthropic"
        assert LLMProvider.OPENAI_COMPATIBLE == "openai_compatible"


@pytest.mark.unit
class TestGetLLMClient:
    """Tests for get_llm_client factory."""

    def test_returns_openai_client_for_openai(self):
        """Test factory returns OpenAIClient for openai provider."""
        config = CompletionsConfig(
            provider=LLMProvider.OPENAI,
            api_key="test-key",
            model="gpt-4o",
        )

        with patch("src.services.llm.factory.OpenAIClient") as mock_client:
            get_llm_client(config)
            mock_client.assert_called_once_with("test-key", "gpt-4o", None)

    def test_returns_anthropic_client_for_anthropic(self):
        """Test factory returns AnthropicClient for anthropic provider."""
        config = CompletionsConfig(
            provider=LLMProvider.ANTHROPIC,
            api_key="test-key",
            model="claude-sonnet-4-20250514",
        )

        with patch("src.services.llm.factory.AnthropicClient") as mock_client:
            get_llm_client(config)
            mock_client.assert_called_once_with("test-key", "claude-sonnet-4-20250514")

    def test_returns_openai_client_with_endpoint_for_compatible(self):
        """Test factory returns OpenAIClient with endpoint for openai_compatible."""
        config = CompletionsConfig(
            provider=LLMProvider.OPENAI_COMPATIBLE,
            api_key="test-key",
            model="llama3",
            endpoint="http://localhost:11434/v1",
        )

        with patch("src.services.llm.factory.OpenAIClient") as mock_client:
            get_llm_client(config)
            mock_client.assert_called_once_with(
                "test-key", "llama3", "http://localhost:11434/v1"
            )


@pytest.mark.unit
@pytest.mark.asyncio
class TestGetCompletionsConfig:
    """Tests for get_completions_config."""

    async def test_returns_none_when_not_configured(self):
        """Test returns None when no config exists."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await get_completions_config(mock_session)
        assert result is None

    async def test_returns_config_when_exists(self):
        """Test returns decrypted config when it exists."""
        from src.models.orm.system_config import SystemConfig

        mock_session = AsyncMock()
        config = SystemConfig(
            id=uuid4(),
            category="llm",
            key="completions_config",
            value_json={
                "provider": "anthropic",
                "api_key_encrypted": "encrypted_key",
                "model": "claude-sonnet-4-20250514",
                "endpoint": None,
                "max_tokens": 4096,
                "temperature": 0.7,
            },
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = config
        mock_session.execute.return_value = mock_result

        with patch("src.services.llm.factory.decrypt_secret") as mock_decrypt:
            mock_decrypt.return_value = "decrypted_key"
            result = await get_completions_config(mock_session)

            assert result is not None
            assert result.provider == LLMProvider.ANTHROPIC
            assert result.api_key == "decrypted_key"
            assert result.model == "claude-sonnet-4-20250514"


@pytest.mark.unit
@pytest.mark.asyncio
class TestGetEmbeddingsConfig:
    """Tests for get_embeddings_config."""

    async def test_returns_none_when_not_configured(self):
        """Test returns None when no embeddings config exists."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await get_embeddings_config(mock_session)
        assert result is None

    async def test_returns_config_when_exists(self):
        """Test returns decrypted embeddings config when it exists."""
        from src.models.orm.system_config import SystemConfig

        mock_session = AsyncMock()
        config = SystemConfig(
            id=uuid4(),
            category="llm",
            key="embeddings_config",
            value_json={
                "api_key_encrypted": "encrypted_key",
                "model": "text-embedding-3-large",
            },
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = config
        mock_session.execute.return_value = mock_result

        with patch("src.services.llm.factory.decrypt_secret") as mock_decrypt:
            mock_decrypt.return_value = "decrypted_key"
            result = await get_embeddings_config(mock_session)

            assert result is not None
            assert result.api_key == "decrypted_key"
            assert result.model == "text-embedding-3-large"

    async def test_uses_default_model_when_not_specified(self):
        """Test uses default model when not specified in config."""
        from src.models.orm.system_config import SystemConfig

        mock_session = AsyncMock()
        config = SystemConfig(
            id=uuid4(),
            category="llm",
            key="embeddings_config",
            value_json={
                "api_key_encrypted": "encrypted_key",
            },
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = config
        mock_session.execute.return_value = mock_result

        with patch("src.services.llm.factory.decrypt_secret") as mock_decrypt:
            mock_decrypt.return_value = "decrypted_key"
            result = await get_embeddings_config(mock_session)

            assert result is not None
            assert result.model == "text-embedding-3-small"

    async def test_returns_none_when_api_key_encrypted_missing(self):
        """Test returns None when api_key_encrypted is missing from config."""
        from src.models.orm.system_config import SystemConfig

        mock_session = AsyncMock()
        config = SystemConfig(
            id=uuid4(),
            category="llm",
            key="embeddings_config",
            value_json={
                "model": "text-embedding-3-large",
                # api_key_encrypted is missing
            },
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = config
        mock_session.execute.return_value = mock_result

        result = await get_embeddings_config(mock_session)
        assert result is None

    async def test_returns_none_when_decryption_fails(self):
        """Test returns None when decryption fails."""
        from src.models.orm.system_config import SystemConfig

        mock_session = AsyncMock()
        config = SystemConfig(
            id=uuid4(),
            category="llm",
            key="embeddings_config",
            value_json={
                "api_key_encrypted": "corrupted_encrypted_data",
            },
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = config
        mock_session.execute.return_value = mock_result

        with patch("src.services.llm.factory.decrypt_secret") as mock_decrypt:
            mock_decrypt.side_effect = InvalidToken()
            result = await get_embeddings_config(mock_session)

            assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestGetCompletionsConfigErrorHandling:
    """Tests for get_completions_config error handling."""

    async def test_returns_none_when_api_key_encrypted_missing(self):
        """Test returns None when api_key_encrypted is missing from config."""
        from src.models.orm.system_config import SystemConfig

        mock_session = AsyncMock()
        config = SystemConfig(
            id=uuid4(),
            category="llm",
            key="completions_config",
            value_json={
                "provider": "openai",
                "model": "gpt-4o",
                # api_key_encrypted is missing
            },
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = config
        mock_session.execute.return_value = mock_result

        result = await get_completions_config(mock_session)
        assert result is None

    async def test_returns_none_when_decryption_fails(self):
        """Test returns None when decryption fails."""
        from src.models.orm.system_config import SystemConfig

        mock_session = AsyncMock()
        config = SystemConfig(
            id=uuid4(),
            category="llm",
            key="completions_config",
            value_json={
                "provider": "openai",
                "api_key_encrypted": "corrupted_encrypted_data",
                "model": "gpt-4o",
            },
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = config
        mock_session.execute.return_value = mock_result

        with patch("src.services.llm.factory.decrypt_secret") as mock_decrypt:
            mock_decrypt.side_effect = InvalidToken()
            result = await get_completions_config(mock_session)

            assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestIsIndexingEnabled:
    """Tests for is_indexing_enabled function."""

    async def test_returns_true_when_no_config_exists(self):
        """Test returns True when no indexing config exists (default behavior)."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await is_indexing_enabled(mock_session)
        assert result is True

    async def test_returns_true_when_enabled_in_config(self):
        """Test returns True when indexing is enabled in config."""
        from src.models.orm.system_config import SystemConfig

        mock_session = AsyncMock()
        config = SystemConfig(
            id=uuid4(),
            category="llm",
            key="indexing_config",
            value_json={"enabled": True},
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = config
        mock_session.execute.return_value = mock_result

        result = await is_indexing_enabled(mock_session)
        assert result is True

    async def test_returns_false_when_disabled_in_config(self):
        """Test returns False when indexing is disabled in config."""
        from src.models.orm.system_config import SystemConfig

        mock_session = AsyncMock()
        config = SystemConfig(
            id=uuid4(),
            category="llm",
            key="indexing_config",
            value_json={"enabled": False},
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = config
        mock_session.execute.return_value = mock_result

        result = await is_indexing_enabled(mock_session)
        assert result is False

    async def test_returns_true_when_enabled_key_missing(self):
        """Test returns True when enabled key is missing from config (default)."""
        from src.models.orm.system_config import SystemConfig

        mock_session = AsyncMock()
        config = SystemConfig(
            id=uuid4(),
            category="llm",
            key="indexing_config",
            value_json={},  # Empty config
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = config
        mock_session.execute.return_value = mock_result

        result = await is_indexing_enabled(mock_session)
        assert result is True

    async def test_returns_true_when_value_json_is_none(self):
        """Test returns True when value_json is None."""
        from src.models.orm.system_config import SystemConfig

        mock_session = AsyncMock()
        config = SystemConfig(
            id=uuid4(),
            category="llm",
            key="indexing_config",
            value_json=None,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = config
        mock_session.execute.return_value = mock_result

        result = await is_indexing_enabled(mock_session)
        assert result is True
