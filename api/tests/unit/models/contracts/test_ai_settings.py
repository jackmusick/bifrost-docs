"""Tests for AI settings contracts."""

from typing import Literal

import pytest
from pydantic import ValidationError

from src.models.contracts.ai_settings import (
    AISettingsResponse,
    CompletionsConfigPublic,
    CompletionsConfigUpdate,
    EmbeddingsConfigPublic,
    EmbeddingsConfigUpdate,
    ModelInfo,
    ModelsResponse,
    TestConnectionRequest,
    TestConnectionResponse,
)


@pytest.mark.unit
class TestAISettingsContracts:
    """Tests for AI settings Pydantic models."""

    def test_completions_config_public(self):
        """Test CompletionsConfigPublic model."""
        config = CompletionsConfigPublic(
            provider="anthropic",
            api_key_set=True,
            model="claude-sonnet-4-20250514",
            endpoint=None,
        )
        assert config.provider == "anthropic"
        assert config.api_key_set is True

    def test_completions_config_update_valid_providers(self):
        """Test CompletionsConfigUpdate accepts valid providers."""
        providers: list[Literal["openai", "anthropic", "openai_compatible"]] = [
            "openai",
            "anthropic",
            "openai_compatible",
        ]
        for provider in providers:
            config = CompletionsConfigUpdate(provider=provider, model="test")
            assert config.provider == provider

    def test_completions_config_update_requires_endpoint_for_compatible(self):
        """Test endpoint validation for openai_compatible."""
        # This should work (endpoint provided)
        config = CompletionsConfigUpdate(
            provider="openai_compatible",
            model="llama3",
            endpoint="http://localhost:11434/v1",
        )
        assert config.endpoint is not None

    def test_completions_config_update_optional_fields(self):
        """Test all fields in CompletionsConfigUpdate are optional."""
        config = CompletionsConfigUpdate()
        assert config.provider is None
        assert config.api_key is None
        assert config.model is None
        assert config.endpoint is None
        assert config.max_tokens is None
        assert config.temperature is None

    def test_completions_config_update_max_tokens_validation(self):
        """Test max_tokens validation."""
        # Valid range
        config = CompletionsConfigUpdate(max_tokens=100)
        assert config.max_tokens == 100

        # Min boundary
        config = CompletionsConfigUpdate(max_tokens=1)
        assert config.max_tokens == 1

        # Max boundary
        config = CompletionsConfigUpdate(max_tokens=100000)
        assert config.max_tokens == 100000

        # Below min
        with pytest.raises(ValidationError):
            CompletionsConfigUpdate(max_tokens=0)

        # Above max
        with pytest.raises(ValidationError):
            CompletionsConfigUpdate(max_tokens=100001)

    def test_completions_config_update_temperature_validation(self):
        """Test temperature validation."""
        # Valid range
        config = CompletionsConfigUpdate(temperature=0.7)
        assert config.temperature == 0.7

        # Min boundary
        config = CompletionsConfigUpdate(temperature=0)
        assert config.temperature == 0

        # Max boundary
        config = CompletionsConfigUpdate(temperature=2)
        assert config.temperature == 2

        # Below min
        with pytest.raises(ValidationError):
            CompletionsConfigUpdate(temperature=-0.1)

        # Above max
        with pytest.raises(ValidationError):
            CompletionsConfigUpdate(temperature=2.1)

    def test_embeddings_config_public(self):
        """Test EmbeddingsConfigPublic model."""
        config = EmbeddingsConfigPublic(
            api_key_set=True,
            model="text-embedding-3-small",
        )
        assert config.api_key_set is True

    def test_embeddings_config_update(self):
        """Test EmbeddingsConfigUpdate model."""
        config = EmbeddingsConfigUpdate(
            api_key="sk-test-key",
            model="text-embedding-3-large",
        )
        assert config.api_key == "sk-test-key"
        assert config.model == "text-embedding-3-large"

    def test_embeddings_config_update_optional_fields(self):
        """Test all fields in EmbeddingsConfigUpdate are optional."""
        config = EmbeddingsConfigUpdate()
        assert config.api_key is None
        assert config.model is None

    def test_model_info(self):
        """Test ModelInfo model."""
        model = ModelInfo(id="gpt-4o", display_name="GPT-4o")
        assert model.id == "gpt-4o"
        assert model.display_name == "GPT-4o"

    def test_ai_settings_response(self):
        """Test AISettingsResponse model."""
        response = AISettingsResponse(
            completions=CompletionsConfigPublic(
                provider="openai",
                api_key_set=True,
                model="gpt-4o",
                endpoint=None,
            ),
            embeddings=EmbeddingsConfigPublic(
                api_key_set=True,
                model="text-embedding-3-small",
            ),
        )
        assert response.completions is not None
        assert response.completions.provider == "openai"
        assert response.embeddings is not None
        assert response.embeddings.api_key_set is True

    def test_ai_settings_response_nullable_fields(self):
        """Test AISettingsResponse allows null completions/embeddings."""
        response = AISettingsResponse(completions=None, embeddings=None)
        assert response.completions is None
        assert response.embeddings is None

    def test_models_response(self):
        """Test ModelsResponse model."""
        response = ModelsResponse(
            models=[
                ModelInfo(id="gpt-4o", display_name="GPT-4o"),
                ModelInfo(id="gpt-4o-mini", display_name="GPT-4o Mini"),
            ]
        )
        assert len(response.models) == 2
        assert response.models[0].id == "gpt-4o"

    def test_test_connection_request(self):
        """Test TestConnectionRequest model."""
        request = TestConnectionRequest(
            provider="openai",
            api_key="sk-test-key",
            endpoint=None,
        )
        assert request.provider == "openai"
        assert request.api_key == "sk-test-key"

    def test_test_connection_request_with_endpoint(self):
        """Test TestConnectionRequest with custom endpoint."""
        request = TestConnectionRequest(
            provider="openai_compatible",
            api_key="test-key",
            endpoint="http://localhost:11434/v1",
        )
        assert request.endpoint == "http://localhost:11434/v1"

    def test_test_connection_request_api_key_required(self):
        """Test api_key is required in TestConnectionRequest."""
        with pytest.raises(ValidationError):
            TestConnectionRequest(provider="openai", api_key="")

    def test_test_connection_response_success(self):
        """Test TestConnectionResponse for successful connection."""
        response = TestConnectionResponse(
            success=True,
            models=[ModelInfo(id="gpt-4o", display_name="GPT-4o")],
            error=None,
        )
        assert response.success is True
        assert len(response.models) == 1
        assert response.error is None

    def test_test_connection_response_failure(self):
        """Test TestConnectionResponse for failed connection."""
        response = TestConnectionResponse(
            success=False,
            models=[],
            error="Invalid API key",
        )
        assert response.success is False
        assert len(response.models) == 0
        assert response.error == "Invalid API key"
