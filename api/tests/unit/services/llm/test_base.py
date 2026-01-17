"""Tests for LLM base types."""
import pytest

from src.services.llm.base import (
    LLMMessage,
    LLMResponse,
    LLMStreamChunk,
    Role,
    ToolCall,
    ToolDefinition,
)


@pytest.mark.unit
class TestLLMBaseTypes:
    """Tests for LLM base types."""

    def test_role_enum_values(self):
        """Test Role enum has expected values."""
        assert Role.SYSTEM == "system"
        assert Role.USER == "user"
        assert Role.ASSISTANT == "assistant"

    def test_llm_message_creation(self):
        """Test LLMMessage dataclass."""
        msg = LLMMessage(role=Role.USER, content="Hello")
        assert msg.role == Role.USER
        assert msg.content == "Hello"

    def test_llm_response_creation(self):
        """Test LLMResponse dataclass."""
        response = LLMResponse(
            content="Hello back",
            tool_calls=[],
            finish_reason="stop",
        )
        assert response.content == "Hello back"
        assert response.tool_calls == []
        assert response.finish_reason == "stop"

    def test_llm_stream_chunk_delta(self):
        """Test LLMStreamChunk for delta type."""
        chunk = LLMStreamChunk(type="delta", content="Hello")
        assert chunk.type == "delta"
        assert chunk.content == "Hello"
        assert chunk.tool_call is None

    def test_llm_stream_chunk_done(self):
        """Test LLMStreamChunk for done type."""
        chunk = LLMStreamChunk(type="done")
        assert chunk.type == "done"
        assert chunk.content is None

    def test_tool_definition(self):
        """Test ToolDefinition dataclass."""
        tool = ToolDefinition(
            name="search",
            description="Search for information",
            parameters={"type": "object", "properties": {}},
        )
        assert tool.name == "search"
        assert tool.description == "Search for information"

    def test_tool_call(self):
        """Test ToolCall dataclass."""
        call = ToolCall(
            id="call_123",
            name="search",
            arguments={"query": "test"},
        )
        assert call.id == "call_123"
        assert call.name == "search"
        assert call.arguments["query"] == "test"
