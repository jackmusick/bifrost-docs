"""Anthropic LLM client implementation."""
from collections.abc import AsyncGenerator

from anthropic import AsyncAnthropic

from src.services.llm.base import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk,
    Role,
    ToolCall,
    ToolDefinition,
)


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API client implementation."""

    def __init__(self, api_key: str, model: str) -> None:
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    def _extract_system_message(
        self, messages: list[LLMMessage]
    ) -> tuple[str | None, list[LLMMessage]]:
        """Extract system message from message list.

        Anthropic handles system messages separately from the conversation.
        """
        system_content = None
        other_messages = []

        for msg in messages:
            if msg.role == Role.SYSTEM:
                system_content = msg.content
            else:
                other_messages.append(msg)

        return system_content, other_messages

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """Convert LLMMessage list to Anthropic message format."""
        return [{"role": msg.role.value, "content": msg.content} for msg in messages]

    def _convert_tools(self, tools: list[ToolDefinition]) -> list[dict]:
        """Convert ToolDefinition list to Anthropic tools format."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters,
            }
            for tool in tools
        ]

    def _parse_response(self, response) -> LLMResponse:  # noqa: ANN001
        """Parse Anthropic response to LLMResponse."""
        content = None
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    )
                )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=response.stop_reason or "end_turn",
        )

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Send a completion request to Anthropic."""
        system_content, conversation = self._extract_system_message(messages)

        request_kwargs: dict = {
            "model": kwargs.get("model", self.model),
            "messages": self._convert_messages(conversation),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        if system_content:
            request_kwargs["system"] = system_content

        if tools:
            request_kwargs["tools"] = self._convert_tools(tools)

        if "temperature" in kwargs:
            request_kwargs["temperature"] = kwargs["temperature"]

        response = await self.client.messages.create(**request_kwargs)
        return self._parse_response(response)

    async def stream(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        **kwargs,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Stream a completion response from Anthropic."""
        system_content, conversation = self._extract_system_message(messages)

        request_kwargs: dict = {
            "model": kwargs.get("model", self.model),
            "messages": self._convert_messages(conversation),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        if system_content:
            request_kwargs["system"] = system_content

        if tools:
            request_kwargs["tools"] = self._convert_tools(tools)

        if "temperature" in kwargs:
            request_kwargs["temperature"] = kwargs["temperature"]

        # Buffer for accumulating tool call arguments
        current_tool: dict[str, str] | None = None

        async with self.client.messages.stream(**request_kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    # TextDelta has text attribute, InputJSONDelta has partial_json
                    delta_text = getattr(event.delta, "text", None)
                    if delta_text is not None:
                        yield LLMStreamChunk(type="delta", content=delta_text)
                    elif event.delta.type == "input_json_delta":
                        # Accumulate tool call JSON fragments
                        if current_tool:
                            current_tool["input_json"] += event.delta.partial_json
                elif event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        # Initialize tool call buffer
                        current_tool = {
                            "id": event.content_block.id,
                            "name": event.content_block.name,
                            "input_json": "",
                        }
                        # Emit pending state for immediate UI feedback
                        yield LLMStreamChunk(
                            type="mutation_pending",
                            tool_call_id=event.content_block.id,
                        )
                elif event.type == "content_block_stop":
                    # Tool call complete - parse and emit
                    if current_tool:
                        try:
                            import json
                            args = json.loads(current_tool["input_json"]) if current_tool["input_json"] else {}
                        except json.JSONDecodeError:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(f"Failed to parse tool input: {current_tool['input_json']}")
                            args = {}

                        yield LLMStreamChunk(
                            type="tool_call",
                            tool_call=ToolCall(
                                id=current_tool["id"],
                                name=current_tool["name"],
                                arguments=args,
                            ),
                        )
                        current_tool = None
                elif event.type == "message_stop":
                    yield LLMStreamChunk(type="done")
