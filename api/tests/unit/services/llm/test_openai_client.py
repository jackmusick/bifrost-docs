"""Tests for OpenAI LLM client."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.llm.base import LLMMessage, Role, ToolDefinition
from src.services.llm.openai_client import OpenAIClient


@pytest.mark.unit
@pytest.mark.asyncio
class TestOpenAIClient:
    """Tests for OpenAIClient."""

    async def test_complete_basic_message(self) -> None:
        """Test basic completion without tools."""
        with patch("src.services.llm.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Hello!"
            mock_response.choices[0].message.tool_calls = None
            mock_response.choices[0].finish_reason = "stop"
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            client = OpenAIClient(api_key="test-key", model="gpt-4o")
            messages = [LLMMessage(role=Role.USER, content="Hi")]

            result = await client.complete(messages)

            assert result.content == "Hello!"
            assert result.finish_reason == "stop"
            assert result.tool_calls == []

    async def test_complete_with_tools(self) -> None:
        """Test completion with tool calls."""
        with patch("src.services.llm.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client

            mock_tool_call = MagicMock()
            mock_tool_call.id = "call_123"
            mock_tool_call.function.name = "search"
            mock_tool_call.function.arguments = '{"query": "test"}'

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = None
            mock_response.choices[0].message.tool_calls = [mock_tool_call]
            mock_response.choices[0].finish_reason = "tool_calls"
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            client = OpenAIClient(api_key="test-key", model="gpt-4o")
            messages = [LLMMessage(role=Role.USER, content="Search for X")]
            tools = [ToolDefinition(name="search", description="Search", parameters={})]

            result = await client.complete(messages, tools=tools)

            assert result.content is None
            assert len(result.tool_calls) == 1
            assert result.tool_calls[0].name == "search"

    async def test_custom_endpoint(self) -> None:
        """Test client with custom endpoint for OpenAI-compatible APIs."""
        with patch("src.services.llm.openai_client.AsyncOpenAI") as mock_openai:
            OpenAIClient(
                api_key="test-key",
                model="llama3",
                endpoint="http://localhost:11434/v1",
            )

            mock_openai.assert_called_once_with(
                api_key="test-key",
                base_url="http://localhost:11434/v1",
            )

    async def test_converts_messages_correctly(self) -> None:
        """Test that messages are converted to OpenAI format."""
        with patch("src.services.llm.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Response"
            mock_response.choices[0].message.tool_calls = None
            mock_response.choices[0].finish_reason = "stop"
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            client = OpenAIClient(api_key="test-key", model="gpt-4o")
            messages = [
                LLMMessage(role=Role.SYSTEM, content="You are helpful"),
                LLMMessage(role=Role.USER, content="Hi"),
            ]

            await client.complete(messages)

            call_args = mock_client.chat.completions.create.call_args
            openai_messages = call_args.kwargs["messages"]
            assert openai_messages[0]["role"] == "system"
            assert openai_messages[0]["content"] == "You are helpful"
            assert openai_messages[1]["role"] == "user"
