"""Tests for AI chat service with multi-provider support."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.contracts.search import SearchResult
from src.services.ai_chat import AIChatService, build_context_from_results
from src.services.llm.base import LLMResponse, LLMStreamChunk


@pytest.mark.unit
@pytest.mark.asyncio
class TestAIChatService:
    """Tests for AIChatService."""

    async def test_raises_error_when_not_configured(self):
        """Test raises error when LLM not configured."""
        mock_session = AsyncMock()

        with patch("src.services.ai_chat.get_completions_config") as mock_config:
            mock_config.return_value = None

            service = AIChatService(mock_session)
            with pytest.raises(ValueError, match="not configured"):
                async for _ in service.stream_response("query", []):
                    pass

    async def test_streams_response_from_llm(self):
        """Test streaming response uses LLM abstraction."""
        mock_session = AsyncMock()

        async def mock_stream(*args, **kwargs):
            yield LLMStreamChunk(type="delta", content="Hello")
            yield LLMStreamChunk(type="delta", content=" world")
            yield LLMStreamChunk(type="done")

        with patch("src.services.ai_chat.get_completions_config") as mock_config:
            with patch("src.services.ai_chat.get_llm_client") as mock_factory:
                mock_config.return_value = MagicMock()
                mock_client = MagicMock()
                mock_client.stream = mock_stream
                mock_factory.return_value = mock_client

                service = AIChatService(mock_session)
                chunks = []
                async for chunk in service.stream_response("query", []):
                    chunks.append(chunk)

                assert "Hello" in "".join(chunks)
                assert "world" in "".join(chunks)

    async def test_get_response_raises_error_when_not_configured(self):
        """Test get_response raises error when LLM not configured."""
        mock_session = AsyncMock()

        with patch("src.services.ai_chat.get_completions_config") as mock_config:
            mock_config.return_value = None

            service = AIChatService(mock_session)
            with pytest.raises(ValueError, match="not configured"):
                await service.get_response("query", [])

    async def test_get_response_returns_complete_response(self):
        """Test get_response uses LLM complete method."""
        mock_session = AsyncMock()

        with patch("src.services.ai_chat.get_completions_config") as mock_config:
            with patch("src.services.ai_chat.get_llm_client") as mock_factory:
                mock_config.return_value = MagicMock()
                mock_client = MagicMock()
                mock_client.complete = AsyncMock(
                    return_value=LLMResponse(content="Complete response")
                )
                mock_factory.return_value = mock_client

                service = AIChatService(mock_session)
                result = await service.get_response("query", [])

                assert result == "Complete response"
                mock_client.complete.assert_called_once()

    async def test_get_response_returns_empty_string_when_no_content(self):
        """Test get_response returns empty string when response has no content."""
        mock_session = AsyncMock()

        with patch("src.services.ai_chat.get_completions_config") as mock_config:
            with patch("src.services.ai_chat.get_llm_client") as mock_factory:
                mock_config.return_value = MagicMock()
                mock_client = MagicMock()
                mock_client.complete = AsyncMock(
                    return_value=LLMResponse(content=None)
                )
                mock_factory.return_value = mock_client

                service = AIChatService(mock_session)
                result = await service.get_response("query", [])

                assert result == ""


@pytest.mark.unit
class TestBuildContextFromResults:
    """Tests for build_context_from_results function."""

    def test_returns_no_results_message_when_empty(self):
        """Test returns appropriate message when no results."""
        result = build_context_from_results([])
        assert "No relevant results found" in result

    def test_builds_context_from_search_results(self):
        """Test builds context string from search results."""
        results = [
            SearchResult(
                entity_id="1",
                entity_type="password",
                name="Test Password",
                organization_id="org-1",
                organization_name="Test Org",
                snippet="This is a snippet",
                score=0.95,
            ),
        ]

        context = build_context_from_results(results)

        assert "Test Org" in context
        assert "Passwords" in context
        assert "Test Password" in context
        assert "95%" in context
        assert "This is a snippet" in context

    def test_groups_results_by_organization_and_type(self):
        """Test groups results by organization and entity type."""
        results = [
            SearchResult(
                entity_id="1",
                entity_type="password",
                name="Password 1",
                organization_id="org-1",
                organization_name="Org A",
                snippet="password snippet 1",
                score=0.9,
            ),
            SearchResult(
                entity_id="2",
                entity_type="configuration",
                name="Config 1",
                organization_id="org-1",
                organization_name="Org A",
                snippet="config snippet",
                score=0.8,
            ),
            SearchResult(
                entity_id="3",
                entity_type="password",
                name="Password 2",
                organization_id="org-2",
                organization_name="Org B",
                snippet="password snippet 2",
                score=0.7,
            ),
        ]

        context = build_context_from_results(results)

        # Both orgs should be present
        assert "Org A" in context
        assert "Org B" in context
        # Both types should be present
        assert "Passwords" in context
        assert "Configurations" in context
