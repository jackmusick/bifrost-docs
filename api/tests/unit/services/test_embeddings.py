"""Tests for embeddings service with new config loading."""

from unittest.mock import AsyncMock, patch

import pytest

from src.services.embeddings import EmbeddingsService
from src.services.llm.factory import EmbeddingsConfig


@pytest.mark.unit
@pytest.mark.asyncio
class TestEmbeddingsService:
    """Tests for EmbeddingsService."""

    async def test_check_openai_available_false_when_not_configured(self):
        """Test returns False when not configured."""
        mock_session = AsyncMock()

        with patch("src.services.embeddings.get_embeddings_config") as mock_config:
            mock_config.return_value = None

            service = EmbeddingsService(mock_session)
            result = await service.check_openai_available()

            assert result is False

    async def test_check_openai_available_true_when_configured(self):
        """Test returns True when configured."""
        mock_session = AsyncMock()

        with patch("src.services.embeddings.get_embeddings_config") as mock_config:
            mock_config.return_value = EmbeddingsConfig(
                api_key="test-key",
                model="text-embedding-3-small",
            )

            service = EmbeddingsService(mock_session)
            result = await service.check_openai_available()

            assert result is True
