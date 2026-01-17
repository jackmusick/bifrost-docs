"""
Unit tests for the AI Settings Router.

Tests the router endpoints for multi-provider AI configuration.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.models.contracts.ai_settings import (
    CompletionsConfigUpdate,
    EmbeddingsConfigUpdate,
    ModelInfo,
    TestConnectionRequest,
)
from src.routers.ai_settings import (
    _get_display_name,
    get_ai_settings,
    list_available_models,
    require_superuser,
    update_completions_config,
    update_embeddings_config,
)
from src.routers.ai_settings import (
    test_ai_connection as router_test_ai_connection,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_superuser():
    """Create a mock superuser."""
    user = MagicMock()
    user.is_platform_admin = True
    user.user_id = uuid4()
    return user


@pytest.fixture
def mock_regular_user():
    """Create a mock regular user (non-admin)."""
    user = MagicMock()
    user.is_platform_admin = False
    user.user_id = uuid4()
    return user


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_completions_config():
    """Create mock completions config data."""
    return {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "api_key_encrypted": "encrypted_key",
        "endpoint": None,
        "max_tokens": 4096,
        "temperature": 0.7,
    }


@pytest.fixture
def mock_embeddings_config():
    """Create mock embeddings config data."""
    return {
        "model": "text-embedding-3-small",
        "api_key_encrypted": "encrypted_key",
    }


# =============================================================================
# Test: require_superuser helper
# =============================================================================


@pytest.mark.unit
class TestRequireSuperuser:
    """Tests for the require_superuser helper function."""

    def test_require_superuser_allows_admin(self, mock_superuser):
        """Test that superusers are allowed."""
        # Should not raise
        require_superuser(mock_superuser)

    def test_require_superuser_blocks_regular_user(self, mock_regular_user):
        """Test that regular users are blocked."""
        with pytest.raises(HTTPException) as exc_info:
            require_superuser(mock_regular_user)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Admin access required"


# =============================================================================
# Test: _get_display_name helper
# =============================================================================


@pytest.mark.unit
class TestGetDisplayName:
    """Tests for the _get_display_name helper function."""

    def test_gpt_model_display_name(self):
        """Test GPT model display name formatting."""
        assert _get_display_name("gpt-4o") == "GPT-4o"
        assert _get_display_name("gpt-4o-mini") == "GPT-4o Mini"
        assert _get_display_name("gpt-3.5-turbo") == "GPT-3.5 Turbo"

    def test_gpt_model_strips_date_suffix(self):
        """Test that date suffixes are stripped from GPT models."""
        assert _get_display_name("gpt-4o-2024-11-20") == "GPT-4o"
        assert _get_display_name("gpt-4o-mini-2024-07-18") == "GPT-4o Mini"

    def test_claude_model_display_name(self):
        """Test Claude model display name formatting."""
        assert _get_display_name("claude-3-5-sonnet-latest") == "Claude 3 5 Sonnet Latest"
        assert _get_display_name("claude-3-opus") == "Claude 3 Opus"

    def test_claude_model_strips_date_suffix(self):
        """Test that date suffixes are stripped from Claude models."""
        # Models with 8-digit date suffixes (YYYYMMDD)
        assert _get_display_name("claude-3-5-sonnet-20241022") == "Claude 3 5 Sonnet"
        # Models with YYYY-MM-DD date suffixes
        assert _get_display_name("claude-3-opus-2024-02-29") == "Claude 3 Opus"

    def test_o_series_model_display_name(self):
        """Test o1/o3 model display name formatting."""
        assert _get_display_name("o1") == "O1"
        assert _get_display_name("o1-mini") == "O1 MINI"
        assert _get_display_name("o3") == "O3"

    def test_embedding_model_display_name(self):
        """Test embedding model display name formatting."""
        assert _get_display_name("text-embedding-3-small") == "Text Embedding 3 Small"
        assert _get_display_name("text-embedding-3-large") == "Text Embedding 3 Large"


# =============================================================================
# Test: GET /api/settings/ai
# =============================================================================


@pytest.mark.unit
class TestGetAISettings:
    """Tests for the get_ai_settings endpoint."""

    @pytest.mark.asyncio
    async def test_get_ai_settings_returns_defaults_when_no_config(
        self, mock_superuser, mock_db_session
    ):
        """Test that defaults are returned when no config exists."""
        with patch(
            "src.routers.ai_settings.SystemConfigRepository"
        ) as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_config.return_value = None
            MockRepo.return_value = mock_repo_instance

            result = await get_ai_settings(mock_superuser, mock_db_session)

            # Verify completions defaults
            assert result.completions is not None
            assert result.completions.api_key_set is False
            assert result.completions.provider == "openai"
            assert result.completions.model == "gpt-4o-mini"
            # Verify embeddings defaults
            assert result.embeddings is not None
            assert result.embeddings.api_key_set is False
            assert result.embeddings.model == "text-embedding-3-small"

    @pytest.mark.asyncio
    async def test_get_ai_settings_returns_stored_config(
        self,
        mock_superuser,
        mock_db_session,
        mock_completions_config,
        mock_embeddings_config,
    ):
        """Test that stored config is returned correctly."""
        with patch(
            "src.routers.ai_settings.SystemConfigRepository"
        ) as MockRepo:
            mock_repo_instance = AsyncMock()

            # Create mock config rows
            mock_completions_row = MagicMock()
            mock_completions_row.value_json = mock_completions_config

            mock_embeddings_row = MagicMock()
            mock_embeddings_row.value_json = mock_embeddings_config

            # get_ai_settings calls get_config twice: completions then embeddings
            mock_repo_instance.get_config.side_effect = [
                mock_completions_row,
                mock_embeddings_row,
            ]
            MockRepo.return_value = mock_repo_instance

            result = await get_ai_settings(mock_superuser, mock_db_session)

            # Verify completions config
            assert result.completions is not None
            assert result.completions.api_key_set is True
            assert result.completions.provider == "openai"
            assert result.completions.model == "gpt-4o-mini"
            # Verify embeddings config
            assert result.embeddings is not None
            assert result.embeddings.api_key_set is True
            assert result.embeddings.model == "text-embedding-3-small"

    @pytest.mark.asyncio
    async def test_get_ai_settings_blocks_non_admin(
        self, mock_regular_user, mock_db_session
    ):
        """Test that non-admins cannot access AI settings."""
        with pytest.raises(HTTPException) as exc_info:
            await get_ai_settings(mock_regular_user, mock_db_session)

        assert exc_info.value.status_code == 403


# =============================================================================
# Test: PUT /api/settings/ai/completions
# =============================================================================


@pytest.mark.unit
class TestUpdateCompletionsConfig:
    """Tests for the update_completions_config endpoint."""

    @pytest.mark.asyncio
    async def test_update_completions_config_partial_update(
        self, mock_superuser, mock_db_session, mock_completions_config
    ):
        """Test partial update of completions config."""
        with (
            patch("src.routers.ai_settings.SystemConfigRepository") as MockRepo,
            patch("src.routers.ai_settings.encrypt_secret") as mock_encrypt,
        ):
            mock_repo_instance = AsyncMock()
            mock_config_row = MagicMock()
            mock_config_row.value_json = mock_completions_config.copy()
            mock_repo_instance.get_config.return_value = mock_config_row
            MockRepo.return_value = mock_repo_instance

            update_data = CompletionsConfigUpdate(model="gpt-4o")

            result = await update_completions_config(
                update_data, mock_superuser, mock_db_session
            )

            assert result.model == "gpt-4o"
            assert result.provider == "openai"  # Unchanged
            mock_encrypt.assert_not_called()  # No API key update

    @pytest.mark.asyncio
    async def test_update_completions_config_encrypts_api_key(
        self, mock_superuser, mock_db_session, mock_completions_config
    ):
        """Test that API key is encrypted before storage."""
        with (
            patch("src.routers.ai_settings.SystemConfigRepository") as MockRepo,
            patch("src.routers.ai_settings.encrypt_secret") as mock_encrypt,
        ):
            mock_repo_instance = AsyncMock()
            mock_config_row = MagicMock()
            mock_config_row.value_json = mock_completions_config.copy()
            mock_repo_instance.get_config.return_value = mock_config_row
            MockRepo.return_value = mock_repo_instance
            mock_encrypt.return_value = "encrypted_new_key"

            update_data = CompletionsConfigUpdate(api_key="sk-new-key")

            result = await update_completions_config(
                update_data, mock_superuser, mock_db_session
            )

            mock_encrypt.assert_called_once_with("sk-new-key")
            assert result.api_key_set is True

    @pytest.mark.asyncio
    async def test_update_completions_config_validates_endpoint_for_compatible(
        self, mock_superuser, mock_db_session
    ):
        """Test that endpoint is required for openai_compatible provider."""
        with patch("src.routers.ai_settings.SystemConfigRepository") as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_config.return_value = None
            MockRepo.return_value = mock_repo_instance

            update_data = CompletionsConfigUpdate(provider="openai_compatible")

            with pytest.raises(HTTPException) as exc_info:
                await update_completions_config(
                    update_data, mock_superuser, mock_db_session
                )

            assert exc_info.value.status_code == 400
            assert "Endpoint is required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_completions_config_allows_compatible_with_endpoint(
        self, mock_superuser, mock_db_session
    ):
        """Test that openai_compatible works when endpoint is provided."""
        with (
            patch("src.routers.ai_settings.SystemConfigRepository") as MockRepo,
            patch("src.routers.ai_settings.encrypt_secret") as mock_encrypt,
        ):
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_config.return_value = None
            MockRepo.return_value = mock_repo_instance
            mock_encrypt.return_value = "encrypted_key"

            update_data = CompletionsConfigUpdate(
                provider="openai_compatible",
                endpoint="https://my-llm.example.com/v1",
                api_key="my-key",
            )

            result = await update_completions_config(
                update_data, mock_superuser, mock_db_session
            )

            assert result.provider == "openai_compatible"
            assert result.endpoint == "https://my-llm.example.com/v1"


# =============================================================================
# Test: PUT /api/settings/ai/embeddings
# =============================================================================


@pytest.mark.unit
class TestUpdateEmbeddingsConfig:
    """Tests for the update_embeddings_config endpoint."""

    @pytest.mark.asyncio
    async def test_update_embeddings_config_partial_update(
        self, mock_superuser, mock_db_session, mock_embeddings_config
    ):
        """Test partial update of embeddings config."""
        with patch("src.routers.ai_settings.SystemConfigRepository") as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_config_row = MagicMock()
            mock_config_row.value_json = mock_embeddings_config.copy()
            mock_repo_instance.get_config.return_value = mock_config_row
            MockRepo.return_value = mock_repo_instance

            update_data = EmbeddingsConfigUpdate(model="text-embedding-3-large")

            result = await update_embeddings_config(
                update_data, mock_superuser, mock_db_session
            )

            assert result.model == "text-embedding-3-large"

    @pytest.mark.asyncio
    async def test_update_embeddings_config_encrypts_api_key(
        self, mock_superuser, mock_db_session, mock_embeddings_config
    ):
        """Test that API key is encrypted before storage."""
        with (
            patch("src.routers.ai_settings.SystemConfigRepository") as MockRepo,
            patch("src.routers.ai_settings.encrypt_secret") as mock_encrypt,
        ):
            mock_repo_instance = AsyncMock()
            mock_config_row = MagicMock()
            mock_config_row.value_json = mock_embeddings_config.copy()
            mock_repo_instance.get_config.return_value = mock_config_row
            MockRepo.return_value = mock_repo_instance
            mock_encrypt.return_value = "encrypted_new_key"

            update_data = EmbeddingsConfigUpdate(api_key="sk-new-key")

            result = await update_embeddings_config(
                update_data, mock_superuser, mock_db_session
            )

            mock_encrypt.assert_called_once_with("sk-new-key")
            assert result.api_key_set is True


# =============================================================================
# Test: GET /api/settings/ai/models
# =============================================================================


@pytest.mark.unit
class TestListAvailableModels:
    """Tests for the list_available_models endpoint."""

    @pytest.mark.asyncio
    async def test_list_models_openai_compatible_returns_empty(
        self, mock_superuser, mock_db_session
    ):
        """Test that openai_compatible returns empty list."""
        result = await list_available_models(
            mock_superuser, mock_db_session, provider="openai_compatible"
        )

        assert result.models == []

    @pytest.mark.asyncio
    async def test_list_models_returns_curated_list_without_key(
        self, mock_superuser, mock_db_session
    ):
        """Test that curated list is returned when no API key is available."""
        with patch("src.routers.ai_settings.SystemConfigRepository") as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_config.return_value = None
            MockRepo.return_value = mock_repo_instance

            result = await list_available_models(
                mock_superuser, mock_db_session, provider="openai", api_key=None
            )

            assert len(result.models) > 0
            model_ids = [m.id for m in result.models]
            assert "gpt-4o" in model_ids
            assert "gpt-4o-mini" in model_ids

    @pytest.mark.asyncio
    async def test_list_models_embeddings_returns_curated_list(
        self, mock_superuser, mock_db_session
    ):
        """Test that embeddings provider returns curated list without key."""
        with patch("src.routers.ai_settings.SystemConfigRepository") as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_config.return_value = None
            MockRepo.return_value = mock_repo_instance

            result = await list_available_models(
                mock_superuser, mock_db_session, provider="embeddings", api_key=None
            )

            assert len(result.models) > 0
            model_ids = [m.id for m in result.models]
            assert "text-embedding-3-small" in model_ids
            assert "text-embedding-3-large" in model_ids

    @pytest.mark.asyncio
    async def test_list_models_anthropic_returns_curated_list(
        self, mock_superuser, mock_db_session
    ):
        """Test that anthropic returns curated list without key."""
        with patch("src.routers.ai_settings.SystemConfigRepository") as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_config.return_value = None
            MockRepo.return_value = mock_repo_instance

            result = await list_available_models(
                mock_superuser, mock_db_session, provider="anthropic", api_key=None
            )

            assert len(result.models) > 0
            model_ids = [m.id for m in result.models]
            assert any("claude" in m for m in model_ids)

    @pytest.mark.asyncio
    async def test_list_models_uses_provided_api_key(
        self, mock_superuser, mock_db_session
    ):
        """Test that provided API key is used for fetching models."""
        with (
            patch("src.routers.ai_settings.SystemConfigRepository") as MockRepo,
            patch("src.routers.ai_settings._fetch_openai_models") as mock_fetch,
        ):
            mock_repo_instance = AsyncMock()
            MockRepo.return_value = mock_repo_instance
            mock_fetch.return_value = [
                ModelInfo(id="gpt-4o", display_name="GPT-4o"),
            ]

            result = await list_available_models(
                mock_superuser,
                mock_db_session,
                provider="openai",
                api_key="sk-test-key",
            )

            mock_fetch.assert_called_once_with("sk-test-key")
            assert len(result.models) == 1

    @pytest.mark.asyncio
    async def test_list_models_uses_stored_api_key(
        self, mock_superuser, mock_db_session, mock_completions_config
    ):
        """Test that stored API key is used when no key provided."""
        with (
            patch("src.routers.ai_settings.SystemConfigRepository") as MockRepo,
            patch("src.routers.ai_settings.decrypt_secret") as mock_decrypt,
            patch("src.routers.ai_settings._fetch_openai_models") as mock_fetch,
        ):
            mock_repo_instance = AsyncMock()
            mock_config_row = MagicMock()
            mock_config_row.value_json = mock_completions_config.copy()
            mock_repo_instance.get_config.return_value = mock_config_row
            MockRepo.return_value = mock_repo_instance
            mock_decrypt.return_value = "sk-decrypted-key"
            mock_fetch.return_value = [
                ModelInfo(id="gpt-4o", display_name="GPT-4o"),
            ]

            await list_available_models(
                mock_superuser, mock_db_session, provider="openai", api_key=None
            )

            mock_decrypt.assert_called_once_with("encrypted_key")
            mock_fetch.assert_called_once_with("sk-decrypted-key")


# =============================================================================
# Test: POST /api/settings/ai/test
# =============================================================================


@pytest.mark.unit
class TestAIConnection:
    """Tests for the test_ai_connection endpoint."""

    @pytest.mark.asyncio
    async def test_connection_openai_success(self, mock_superuser):
        """Test successful OpenAI connection test."""
        with (
            patch("src.routers.ai_settings._fetch_openai_models") as mock_fetch_chat,
            patch("src.routers.ai_settings._fetch_openai_embedding_models") as mock_fetch_embed,
        ):
            mock_fetch_chat.return_value = [
                ModelInfo(id="gpt-4o", display_name="GPT-4o"),
                ModelInfo(id="gpt-4o-mini", display_name="GPT-4o Mini"),
            ]
            mock_fetch_embed.return_value = [
                ModelInfo(id="text-embedding-3-small", display_name="Text Embedding 3 Small"),
            ]

            request = TestConnectionRequest(provider="openai", api_key="sk-test-key")
            result = await router_test_ai_connection(request, mock_superuser)

            assert result.success is True
            assert len(result.models) == 2  # Chat models
            assert result.completions_models is not None
            assert len(result.completions_models) == 2
            assert result.embedding_models is not None
            assert len(result.embedding_models) == 1
            assert result.error is None
            assert "Connected!" in result.message

    @pytest.mark.asyncio
    async def test_connection_anthropic_success(self, mock_superuser):
        """Test successful Anthropic connection test."""
        with patch(
            "src.routers.ai_settings._fetch_anthropic_models"
        ) as mock_fetch:
            mock_fetch.return_value = [
                ModelInfo(id="claude-3-5-sonnet", display_name="Claude 3 5 Sonnet"),
            ]

            request = TestConnectionRequest(provider="anthropic", api_key="sk-ant-key")
            result = await router_test_ai_connection(request, mock_superuser)

            assert result.success is True
            assert len(result.models) == 1

    @pytest.mark.asyncio
    async def test_connection_openai_compatible_requires_endpoint(self, mock_superuser):
        """Test that openai_compatible requires endpoint."""
        request = TestConnectionRequest(
            provider="openai_compatible", api_key="my-key"
        )

        with pytest.raises(HTTPException) as exc_info:
            await router_test_ai_connection(request, mock_superuser)

        assert exc_info.value.status_code == 400
        assert "Endpoint is required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_connection_openai_compatible_success(self, mock_superuser):
        """Test successful openai_compatible connection test."""
        with patch("openai.AsyncOpenAI") as MockClient:
            mock_client = AsyncMock()
            mock_models_response = MagicMock()
            mock_models_response.data = [
                MagicMock(id="llama-3.1-70b"),
            ]
            mock_client.models.list.return_value = mock_models_response
            MockClient.return_value = mock_client

            request = TestConnectionRequest(
                provider="openai_compatible",
                api_key="my-key",
                endpoint="https://my-llm.example.com/v1",
            )
            result = await router_test_ai_connection(request, mock_superuser)

            assert result.success is True
            MockClient.assert_called_with(
                api_key="my-key",
                base_url="https://my-llm.example.com/v1",
            )

    @pytest.mark.asyncio
    async def test_connection_failure_invalid_key(self, mock_superuser):
        """Test connection failure with invalid API key."""
        with patch(
            "src.routers.ai_settings._fetch_openai_models"
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("Incorrect API key provided")

            request = TestConnectionRequest(provider="openai", api_key="sk-invalid")
            result = await router_test_ai_connection(request, mock_superuser)

            assert result.success is False
            assert result.error == "Invalid API key"
            assert result.models == []

    @pytest.mark.asyncio
    async def test_connection_failure_rate_limit(self, mock_superuser):
        """Test connection failure due to rate limit."""
        with patch(
            "src.routers.ai_settings._fetch_openai_models"
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("Rate limit exceeded")

            request = TestConnectionRequest(provider="openai", api_key="sk-test")
            result = await router_test_ai_connection(request, mock_superuser)

            assert result.success is False
            assert result.error is not None
            assert "Rate limit" in result.error

    @pytest.mark.asyncio
    async def test_connection_failure_network(self, mock_superuser):
        """Test connection failure due to network issues."""
        with patch(
            "src.routers.ai_settings._fetch_openai_models"
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("Connection timeout")

            request = TestConnectionRequest(provider="openai", api_key="sk-test")
            result = await router_test_ai_connection(request, mock_superuser)

            assert result.success is False
            assert result.error is not None
            assert "Connection failed" in result.error
