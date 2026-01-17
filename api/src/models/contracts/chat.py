"""Chat request/response contracts."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in the conversation."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request to send a chat message."""

    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    conversation_id: str | None = Field(None, description="Existing conversation ID")
    history: list[ChatMessage] = Field(
        default_factory=list, description="Previous messages for context"
    )
    org_id: UUID | None = Field(None, description="Filter to specific organization")
    current_entity_id: UUID | None = Field(
        None, description="ID of entity user is currently viewing (for context)"
    )
    current_entity_type: Literal["document", "custom_asset"] | None = Field(
        None, description="Type of entity user is currently viewing"
    )


class ChatStartResponse(BaseModel):
    """Response when starting a chat."""

    request_id: str = Field(..., description="WebSocket channel ID for streaming")
    conversation_id: str = Field(..., description="Conversation ID for follow-ups")
