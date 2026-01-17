"""OpenAI LLM client implementation."""
import json
from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from src.services.llm.base import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk,
    ToolCall,
    ToolDefinition,
)


class OpenAIClient(BaseLLMClient):
    """OpenAI API client implementation.

    Also works with OpenAI-compatible APIs by setting a custom endpoint.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        endpoint: str | None = None,
    ) -> None:
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=endpoint,
        )
        self.model = model

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """Convert LLMMessage list to OpenAI message format."""
        return [{"role": msg.role.value, "content": msg.content} for msg in messages]

    def _convert_tools(self, tools: list[ToolDefinition]) -> list[dict]:
        """Convert ToolDefinition list to OpenAI tools format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]

    def _parse_tool_calls(self, tool_calls) -> list[ToolCall]:  # noqa: ANN001
        """Parse OpenAI tool calls to ToolCall objects."""
        if not tool_calls:
            return []
        return [
            ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=json.loads(tc.function.arguments),
            )
            for tc in tool_calls
        ]

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Send a completion request to OpenAI."""
        request_kwargs: dict = {
            "model": kwargs.get("model", self.model),
            "messages": self._convert_messages(messages),
        }

        if tools:
            request_kwargs["tools"] = self._convert_tools(tools)

        if "max_tokens" in kwargs:
            request_kwargs["max_tokens"] = kwargs["max_tokens"]
        if "temperature" in kwargs:
            request_kwargs["temperature"] = kwargs["temperature"]

        response = await self.client.chat.completions.create(**request_kwargs)
        choice = response.choices[0]

        return LLMResponse(
            content=choice.message.content,
            tool_calls=self._parse_tool_calls(choice.message.tool_calls),
            finish_reason=choice.finish_reason or "stop",
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        **kwargs,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Stream a completion response from OpenAI."""
        request_kwargs: dict = {
            "model": kwargs.get("model", self.model),
            "messages": self._convert_messages(messages),
            "stream": True,
        }

        if tools:
            request_kwargs["tools"] = self._convert_tools(tools)

        if "max_tokens" in kwargs:
            request_kwargs["max_tokens"] = kwargs["max_tokens"]
        if "temperature" in kwargs:
            request_kwargs["temperature"] = kwargs["temperature"]

        response = await self.client.chat.completions.create(**request_kwargs)

        async for chunk in response:  # type: ignore[union-attr]
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            finish_reason = chunk.choices[0].finish_reason

            if delta.content:
                yield LLMStreamChunk(type="delta", content=delta.content)

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tc.function and tc.function.name:
                        yield LLMStreamChunk(
                            type="tool_call",
                            tool_call=ToolCall(
                                id=tc.id or "",
                                name=tc.function.name,
                                arguments=json.loads(tc.function.arguments or "{}"),
                            ),
                        )

            if finish_reason:
                yield LLMStreamChunk(type="done")
