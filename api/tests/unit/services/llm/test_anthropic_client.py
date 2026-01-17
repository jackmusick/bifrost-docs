"""Tests for Anthropic LLM client."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.llm.anthropic_client import AnthropicClient
from src.services.llm.base import LLMMessage, Role, ToolDefinition


@pytest.mark.unit
@pytest.mark.asyncio
class TestAnthropicClient:
    """Tests for AnthropicClient."""

    async def test_complete_basic_message(self) -> None:
        """Test basic completion without tools."""
        with patch("src.services.llm.anthropic_client.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_anthropic.return_value = mock_client

            mock_response = MagicMock()
            mock_response.content = [MagicMock(type="text", text="Hello!")]
            mock_response.stop_reason = "end_turn"
            mock_client.messages.create = AsyncMock(return_value=mock_response)

            client = AnthropicClient(api_key="test-key", model="claude-sonnet-4-20250514")
            messages = [LLMMessage(role=Role.USER, content="Hi")]

            result = await client.complete(messages)

            assert result.content == "Hello!"
            assert result.finish_reason == "end_turn"

    async def test_extracts_system_message(self) -> None:
        """Test that system message is extracted and passed separately."""
        with patch("src.services.llm.anthropic_client.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_anthropic.return_value = mock_client

            mock_response = MagicMock()
            mock_response.content = [MagicMock(type="text", text="Response")]
            mock_response.stop_reason = "end_turn"
            mock_client.messages.create = AsyncMock(return_value=mock_response)

            client = AnthropicClient(api_key="test-key", model="claude-sonnet-4-20250514")
            messages = [
                LLMMessage(role=Role.SYSTEM, content="You are helpful"),
                LLMMessage(role=Role.USER, content="Hi"),
            ]

            await client.complete(messages)

            call_args = mock_client.messages.create.call_args
            assert call_args.kwargs["system"] == "You are helpful"
            assert len(call_args.kwargs["messages"]) == 1
            assert call_args.kwargs["messages"][0]["role"] == "user"

    async def test_complete_with_tools(self) -> None:
        """Test completion with tool calls."""
        with patch("src.services.llm.anthropic_client.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_anthropic.return_value = mock_client

            mock_tool_use = MagicMock()
            mock_tool_use.type = "tool_use"
            mock_tool_use.id = "call_123"
            mock_tool_use.name = "search"
            mock_tool_use.input = {"query": "test"}

            mock_response = MagicMock()
            mock_response.content = [mock_tool_use]
            mock_response.stop_reason = "tool_use"
            mock_client.messages.create = AsyncMock(return_value=mock_response)

            client = AnthropicClient(api_key="test-key", model="claude-sonnet-4-20250514")
            messages = [LLMMessage(role=Role.USER, content="Search for X")]
            tools = [ToolDefinition(name="search", description="Search", parameters={})]

            result = await client.complete(messages, tools=tools)

            assert len(result.tool_calls) == 1
            assert result.tool_calls[0].name == "search"
            assert result.tool_calls[0].arguments["query"] == "test"

    async def test_converts_tools_correctly(self) -> None:
        """Test that tools are converted to Anthropic format."""
        with patch("src.services.llm.anthropic_client.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_anthropic.return_value = mock_client

            mock_response = MagicMock()
            mock_response.content = [MagicMock(type="text", text="Response")]
            mock_response.stop_reason = "end_turn"
            mock_client.messages.create = AsyncMock(return_value=mock_response)

            client = AnthropicClient(api_key="test-key", model="claude-sonnet-4-20250514")
            messages = [LLMMessage(role=Role.USER, content="Hi")]
            tools = [
                ToolDefinition(
                    name="search",
                    description="Search for info",
                    parameters={"type": "object", "properties": {}},
                )
            ]

            await client.complete(messages, tools=tools)

            call_args = mock_client.messages.create.call_args
            anthropic_tools = call_args.kwargs["tools"]
            assert anthropic_tools[0]["name"] == "search"
            assert anthropic_tools[0]["description"] == "Search for info"
            assert "input_schema" in anthropic_tools[0]
