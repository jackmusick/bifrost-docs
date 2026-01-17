"""Base types and abstract class for LLM providers."""
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class Role(str, Enum):
    """Message role in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class LLMMessage:
    """A message in a conversation."""

    role: Role
    content: str


@dataclass
class ToolDefinition:
    """Definition of a tool/function that can be called."""

    name: str
    description: str
    parameters: dict  # JSON Schema


@dataclass
class ToolCall:
    """A tool call requested by the model."""

    id: str
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    """Response from a completion request."""

    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"


@dataclass
class LLMStreamChunk:
    """A chunk from a streaming response."""

    type: Literal["delta", "tool_call", "mutation_pending", "done", "error"]
    content: str | None = None
    tool_call: ToolCall | None = None
    tool_call_id: str | None = None  # For tracking pending tool calls
    error: str | None = None


class BaseLLMClient(ABC):
    """Abstract base class for LLM provider clients."""

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Send a completion request and return the full response."""
        ...

    @abstractmethod
    def stream(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        **kwargs,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Stream a completion response chunk by chunk."""
        ...
