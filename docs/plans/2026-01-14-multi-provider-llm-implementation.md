# Multi-Provider LLM Support Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add support for multiple LLM providers (OpenAI, Anthropic, OpenAI-compatible) for completions while keeping embeddings OpenAI-only.

**Architecture:** Create an LLM abstraction layer with `BaseLLMClient` interface and provider-specific implementations. Replace the single `ai_settings` table with a flexible `system_config` key-value store. Update services to use the new abstraction.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0+, OpenAI SDK, Anthropic SDK, Fernet encryption, pytest

---

## Task 1: Add Anthropic Dependency

**Files:**
- Modify: `api/requirements.txt`

**Step 1: Add anthropic package**

Add to `api/requirements.txt`:
```
anthropic>=0.40.0
```

**Step 2: Install dependencies**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pip install -r requirements.txt`
Expected: Successfully installed anthropic

**Step 3: Commit**

```bash
git add api/requirements.txt
git commit -m "chore: add anthropic SDK dependency"
```

---

## Task 2: Create SystemConfig ORM Model

**Files:**
- Create: `api/src/models/orm/system_config.py`
- Modify: `api/src/models/orm/__init__.py`

**Step 1: Write the test**

Create `api/tests/unit/models/test_system_config.py`:

```python
"""Tests for SystemConfig ORM model."""
import pytest
from uuid import uuid4
from datetime import datetime, UTC

from src.models.orm.system_config import SystemConfig


@pytest.mark.unit
class TestSystemConfigModel:
    """Tests for SystemConfig model."""

    def test_create_system_config(self):
        """Test creating a SystemConfig instance."""
        config = SystemConfig(
            category="llm",
            key="completions_config",
            value_json={"provider": "openai", "model": "gpt-4o"},
        )
        assert config.category == "llm"
        assert config.key == "completions_config"
        assert config.value_json["provider"] == "openai"

    def test_system_config_defaults(self):
        """Test that SystemConfig has correct defaults."""
        config = SystemConfig(
            category="test",
            key="test_key",
            value_json={},
        )
        assert config.id is not None
        assert config.created_at is not None
        assert config.updated_at is not None
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/models/test_system_config.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.models.orm.system_config'"

**Step 3: Create the model**

Create `api/src/models/orm/system_config.py`:

```python
"""SystemConfig ORM model for flexible key-value configuration storage."""
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.orm.base import Base


class SystemConfig(Base):
    """System configuration key-value store.

    Stores configuration as JSON values, organized by category and key.
    Example: category="llm", key="completions_config" stores LLM settings.
    """

    __tablename__ = "system_config"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint("category", "key", name="uq_system_config_category_key"),
    )

    def __repr__(self) -> str:
        return f"<SystemConfig {self.category}/{self.key}>"
```

**Step 4: Export from __init__.py**

Add to `api/src/models/orm/__init__.py`:
```python
from src.models.orm.system_config import SystemConfig
```

**Step 5: Run test to verify it passes**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/models/test_system_config.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add api/src/models/orm/system_config.py api/src/models/orm/__init__.py api/tests/unit/models/test_system_config.py
git commit -m "feat: add SystemConfig ORM model for flexible configuration storage"
```

---

## Task 3: Create Database Migration

**Files:**
- Create: `api/migrations/versions/XXXX_add_system_config_drop_ai_settings.py`

**Step 1: Generate migration**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && alembic revision -m "add_system_config_drop_ai_settings"`

**Step 2: Write the migration**

Edit the generated migration file:

```python
"""Add system_config table and drop ai_settings.

Revision ID: <generated>
Revises: <previous>
Create Date: <generated>
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "<generated>"
down_revision: Union[str, None] = "<previous>"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create system_config table
    op.create_table(
        "system_config",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category", "key", name="uq_system_config_category_key"),
    )

    # Drop ai_settings table
    op.drop_table("ai_settings")


def downgrade() -> None:
    # Recreate ai_settings table
    op.create_table(
        "ai_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("openai_api_key", sa.Text(), nullable=True),
        sa.Column("openai_model", sa.String(100), nullable=False),
        sa.Column("embeddings_model", sa.String(100), nullable=False),
        sa.Column("indexing_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Drop system_config table
    op.drop_table("system_config")
```

**Step 3: Run migration**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && alembic upgrade head`
Expected: Migration applies successfully

**Step 4: Commit**

```bash
git add api/migrations/versions/
git commit -m "feat: add system_config table and drop ai_settings"
```

---

## Task 4: Create SystemConfig Repository

**Files:**
- Create: `api/src/repositories/system_config.py`
- Modify: `api/src/repositories/__init__.py`

**Step 1: Write the test**

Create `api/tests/unit/repositories/test_system_config.py`:

```python
"""Tests for SystemConfig repository."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.models.orm.system_config import SystemConfig
from src.repositories.system_config import SystemConfigRepository


@pytest.mark.unit
@pytest.mark.asyncio
class TestSystemConfigRepository:
    """Tests for SystemConfigRepository."""

    async def test_get_config_returns_none_when_not_found(self):
        """Test get_config returns None when config doesn't exist."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = SystemConfigRepository(mock_session)
        result = await repo.get_config("llm", "completions_config")

        assert result is None

    async def test_get_config_returns_config_when_found(self):
        """Test get_config returns config when it exists."""
        mock_session = AsyncMock()
        config = SystemConfig(
            id=uuid4(),
            category="llm",
            key="completions_config",
            value_json={"provider": "openai"},
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = config
        mock_session.execute.return_value = mock_result

        repo = SystemConfigRepository(mock_session)
        result = await repo.get_config("llm", "completions_config")

        assert result == config

    async def test_set_config_creates_new_config(self):
        """Test set_config creates config when it doesn't exist."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.refresh = AsyncMock()

        repo = SystemConfigRepository(mock_session)
        result = await repo.set_config("llm", "completions_config", {"provider": "openai"})

        mock_session.add.assert_called_once()
        assert result.category == "llm"
        assert result.key == "completions_config"
        assert result.value_json["provider"] == "openai"

    async def test_set_config_updates_existing_config(self):
        """Test set_config updates config when it exists."""
        mock_session = AsyncMock()
        existing = SystemConfig(
            id=uuid4(),
            category="llm",
            key="completions_config",
            value_json={"provider": "openai"},
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = mock_result
        mock_session.refresh = AsyncMock()

        repo = SystemConfigRepository(mock_session)
        result = await repo.set_config("llm", "completions_config", {"provider": "anthropic"})

        assert result.value_json["provider"] == "anthropic"
        mock_session.add.assert_not_called()

    async def test_delete_config(self):
        """Test delete_config removes config."""
        mock_session = AsyncMock()
        existing = SystemConfig(
            id=uuid4(),
            category="llm",
            key="completions_config",
            value_json={},
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = mock_result

        repo = SystemConfigRepository(mock_session)
        result = await repo.delete_config("llm", "completions_config")

        assert result is True
        mock_session.delete.assert_called_once_with(existing)
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/repositories/test_system_config.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create the repository**

Create `api/src/repositories/system_config.py`:

```python
"""Repository for SystemConfig model operations."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.orm.system_config import SystemConfig


class SystemConfigRepository:
    """Repository for system configuration operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_config(self, category: str, key: str) -> SystemConfig | None:
        """Get a configuration by category and key."""
        result = await self.session.execute(
            select(SystemConfig).where(
                SystemConfig.category == category,
                SystemConfig.key == key,
            )
        )
        return result.scalar_one_or_none()

    async def set_config(
        self, category: str, key: str, value_json: dict
    ) -> SystemConfig:
        """Set a configuration value, creating or updating as needed."""
        config = await self.get_config(category, key)

        if config is None:
            config = SystemConfig(
                category=category,
                key=key,
                value_json=value_json,
            )
            self.session.add(config)
        else:
            config.value_json = value_json

        await self.session.flush()
        await self.session.refresh(config)
        return config

    async def delete_config(self, category: str, key: str) -> bool:
        """Delete a configuration. Returns True if deleted, False if not found."""
        config = await self.get_config(category, key)
        if config is None:
            return False

        await self.session.delete(config)
        await self.session.flush()
        return True

    async def get_all_by_category(self, category: str) -> list[SystemConfig]:
        """Get all configurations in a category."""
        result = await self.session.execute(
            select(SystemConfig).where(SystemConfig.category == category)
        )
        return list(result.scalars().all())
```

**Step 4: Export from __init__.py**

Add to `api/src/repositories/__init__.py`:
```python
from src.repositories.system_config import SystemConfigRepository
```

**Step 5: Run test to verify it passes**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/repositories/test_system_config.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add api/src/repositories/system_config.py api/src/repositories/__init__.py api/tests/unit/repositories/test_system_config.py
git commit -m "feat: add SystemConfigRepository for configuration CRUD"
```

---

## Task 5: Create LLM Base Types

**Files:**
- Create: `api/src/services/llm/__init__.py`
- Create: `api/src/services/llm/base.py`

**Step 1: Write the test**

Create `api/tests/unit/services/llm/test_base.py`:

```python
"""Tests for LLM base types."""
import pytest

from src.services.llm.base import (
    Role,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk,
    ToolDefinition,
    ToolCall,
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/services/llm/test_base.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create the directory and base types**

Create `api/src/services/llm/__init__.py`:

```python
"""LLM abstraction layer for multi-provider support."""
from src.services.llm.base import (
    Role,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk,
    ToolDefinition,
    ToolCall,
    BaseLLMClient,
)

__all__ = [
    "Role",
    "LLMMessage",
    "LLMResponse",
    "LLMStreamChunk",
    "ToolDefinition",
    "ToolCall",
    "BaseLLMClient",
]
```

Create `api/src/services/llm/base.py`:

```python
"""Base types and abstract class for LLM providers."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncGenerator, Literal


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

    type: Literal["delta", "tool_call", "done", "error"]
    content: str | None = None
    tool_call: ToolCall | None = None
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
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/services/llm/test_base.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/services/llm/ api/tests/unit/services/llm/
git commit -m "feat: add LLM base types and abstract client interface"
```

---

## Task 6: Create OpenAI Client Implementation

**Files:**
- Create: `api/src/services/llm/openai_client.py`
- Modify: `api/src/services/llm/__init__.py`

**Step 1: Write the test**

Create `api/tests/unit/services/llm/test_openai_client.py`:

```python
"""Tests for OpenAI LLM client."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.llm.base import Role, LLMMessage, ToolDefinition
from src.services.llm.openai_client import OpenAIClient


@pytest.mark.unit
@pytest.mark.asyncio
class TestOpenAIClient:
    """Tests for OpenAIClient."""

    async def test_complete_basic_message(self):
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

    async def test_complete_with_tools(self):
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

    async def test_custom_endpoint(self):
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

    async def test_converts_messages_correctly(self):
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/services/llm/test_openai_client.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create OpenAI client**

Create `api/src/services/llm/openai_client.py`:

```python
"""OpenAI LLM client implementation."""
import json
from typing import AsyncGenerator

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

    def _parse_tool_calls(self, tool_calls) -> list[ToolCall]:
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
        request_kwargs = {
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
        request_kwargs = {
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

        async for chunk in response:
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
```

**Step 4: Update __init__.py**

Add to `api/src/services/llm/__init__.py`:
```python
from src.services.llm.openai_client import OpenAIClient

__all__ = [
    # ... existing exports ...
    "OpenAIClient",
]
```

**Step 5: Run test to verify it passes**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/services/llm/test_openai_client.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add api/src/services/llm/openai_client.py api/src/services/llm/__init__.py api/tests/unit/services/llm/test_openai_client.py
git commit -m "feat: add OpenAI client implementation with streaming support"
```

---

## Task 7: Create Anthropic Client Implementation

**Files:**
- Create: `api/src/services/llm/anthropic_client.py`
- Modify: `api/src/services/llm/__init__.py`

**Step 1: Write the test**

Create `api/tests/unit/services/llm/test_anthropic_client.py`:

```python
"""Tests for Anthropic LLM client."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.llm.base import Role, LLMMessage, ToolDefinition
from src.services.llm.anthropic_client import AnthropicClient


@pytest.mark.unit
@pytest.mark.asyncio
class TestAnthropicClient:
    """Tests for AnthropicClient."""

    async def test_complete_basic_message(self):
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

    async def test_extracts_system_message(self):
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

    async def test_complete_with_tools(self):
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

    async def test_converts_tools_correctly(self):
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/services/llm/test_anthropic_client.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create Anthropic client**

Create `api/src/services/llm/anthropic_client.py`:

```python
"""Anthropic LLM client implementation."""
from typing import AsyncGenerator

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

    def _parse_response(self, response) -> LLMResponse:
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

        request_kwargs = {
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

        request_kwargs = {
            "model": kwargs.get("model", self.model),
            "messages": self._convert_messages(conversation),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "stream": True,
        }

        if system_content:
            request_kwargs["system"] = system_content

        if tools:
            request_kwargs["tools"] = self._convert_tools(tools)

        if "temperature" in kwargs:
            request_kwargs["temperature"] = kwargs["temperature"]

        async with self.client.messages.stream(**request_kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        yield LLMStreamChunk(type="delta", content=event.delta.text)
                elif event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        yield LLMStreamChunk(
                            type="tool_call",
                            tool_call=ToolCall(
                                id=event.content_block.id,
                                name=event.content_block.name,
                                arguments={},
                            ),
                        )
                elif event.type == "message_stop":
                    yield LLMStreamChunk(type="done")
```

**Step 4: Update __init__.py**

Add to `api/src/services/llm/__init__.py`:
```python
from src.services.llm.anthropic_client import AnthropicClient

__all__ = [
    # ... existing exports ...
    "AnthropicClient",
]
```

**Step 5: Run test to verify it passes**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/services/llm/test_anthropic_client.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add api/src/services/llm/anthropic_client.py api/src/services/llm/__init__.py api/tests/unit/services/llm/test_anthropic_client.py
git commit -m "feat: add Anthropic client implementation with streaming support"
```

---

## Task 8: Create LLM Factory

**Files:**
- Create: `api/src/services/llm/factory.py`
- Modify: `api/src/services/llm/__init__.py`

**Step 1: Write the test**

Create `api/tests/unit/services/llm/test_factory.py`:

```python
"""Tests for LLM factory."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.services.llm.factory import (
    LLMProvider,
    CompletionsConfig,
    EmbeddingsConfig,
    get_completions_config,
    get_embeddings_config,
    get_llm_client,
)
from src.services.llm.openai_client import OpenAIClient
from src.services.llm.anthropic_client import AnthropicClient


@pytest.mark.unit
class TestLLMProvider:
    """Tests for LLMProvider enum."""

    def test_provider_values(self):
        """Test provider enum values."""
        assert LLMProvider.OPENAI == "openai"
        assert LLMProvider.ANTHROPIC == "anthropic"
        assert LLMProvider.OPENAI_COMPATIBLE == "openai_compatible"


@pytest.mark.unit
class TestGetLLMClient:
    """Tests for get_llm_client factory."""

    def test_returns_openai_client_for_openai(self):
        """Test factory returns OpenAIClient for openai provider."""
        config = CompletionsConfig(
            provider=LLMProvider.OPENAI,
            api_key="test-key",
            model="gpt-4o",
        )

        with patch("src.services.llm.factory.OpenAIClient") as mock_client:
            get_llm_client(config)
            mock_client.assert_called_once_with("test-key", "gpt-4o", None)

    def test_returns_anthropic_client_for_anthropic(self):
        """Test factory returns AnthropicClient for anthropic provider."""
        config = CompletionsConfig(
            provider=LLMProvider.ANTHROPIC,
            api_key="test-key",
            model="claude-sonnet-4-20250514",
        )

        with patch("src.services.llm.factory.AnthropicClient") as mock_client:
            get_llm_client(config)
            mock_client.assert_called_once_with("test-key", "claude-sonnet-4-20250514")

    def test_returns_openai_client_with_endpoint_for_compatible(self):
        """Test factory returns OpenAIClient with endpoint for openai_compatible."""
        config = CompletionsConfig(
            provider=LLMProvider.OPENAI_COMPATIBLE,
            api_key="test-key",
            model="llama3",
            endpoint="http://localhost:11434/v1",
        )

        with patch("src.services.llm.factory.OpenAIClient") as mock_client:
            get_llm_client(config)
            mock_client.assert_called_once_with(
                "test-key", "llama3", "http://localhost:11434/v1"
            )


@pytest.mark.unit
@pytest.mark.asyncio
class TestGetCompletionsConfig:
    """Tests for get_completions_config."""

    async def test_returns_none_when_not_configured(self):
        """Test returns None when no config exists."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await get_completions_config(mock_session)
        assert result is None

    async def test_returns_config_when_exists(self):
        """Test returns decrypted config when it exists."""
        from src.models.orm.system_config import SystemConfig

        mock_session = AsyncMock()
        config = SystemConfig(
            id=uuid4(),
            category="llm",
            key="completions_config",
            value_json={
                "provider": "anthropic",
                "api_key_encrypted": "encrypted_key",
                "model": "claude-sonnet-4-20250514",
                "endpoint": None,
                "max_tokens": 4096,
                "temperature": 0.7,
            },
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = config
        mock_session.execute.return_value = mock_result

        with patch("src.services.llm.factory.decrypt_secret") as mock_decrypt:
            mock_decrypt.return_value = "decrypted_key"
            result = await get_completions_config(mock_session)

            assert result is not None
            assert result.provider == LLMProvider.ANTHROPIC
            assert result.api_key == "decrypted_key"
            assert result.model == "claude-sonnet-4-20250514"
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/services/llm/test_factory.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create factory**

Create `api/src/services/llm/factory.py`:

```python
"""Factory for creating LLM clients based on configuration."""
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import decrypt_secret
from src.models.orm.system_config import SystemConfig
from src.services.llm.anthropic_client import AnthropicClient
from src.services.llm.base import BaseLLMClient
from src.services.llm.openai_client import OpenAIClient


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENAI_COMPATIBLE = "openai_compatible"


@dataclass
class CompletionsConfig:
    """Configuration for completions/chat LLM."""

    provider: LLMProvider
    api_key: str  # Decrypted
    model: str
    endpoint: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class EmbeddingsConfig:
    """Configuration for embeddings."""

    api_key: str  # Decrypted
    model: str = "text-embedding-3-small"


async def get_completions_config(session: AsyncSession) -> CompletionsConfig | None:
    """Load and decrypt completions config from database."""
    result = await session.execute(
        select(SystemConfig).where(
            SystemConfig.category == "llm",
            SystemConfig.key == "completions_config",
        )
    )
    config = result.scalar_one_or_none()

    if config is None:
        return None

    value = config.value_json
    api_key = decrypt_secret(value["api_key_encrypted"])

    return CompletionsConfig(
        provider=LLMProvider(value["provider"]),
        api_key=api_key,
        model=value["model"],
        endpoint=value.get("endpoint"),
        max_tokens=value.get("max_tokens", 4096),
        temperature=value.get("temperature", 0.7),
    )


async def get_embeddings_config(session: AsyncSession) -> EmbeddingsConfig | None:
    """Load and decrypt embeddings config from database."""
    result = await session.execute(
        select(SystemConfig).where(
            SystemConfig.category == "llm",
            SystemConfig.key == "embeddings_config",
        )
    )
    config = result.scalar_one_or_none()

    if config is None:
        return None

    value = config.value_json
    api_key = decrypt_secret(value["api_key_encrypted"])

    return EmbeddingsConfig(
        api_key=api_key,
        model=value.get("model", "text-embedding-3-small"),
    )


def get_llm_client(config: CompletionsConfig) -> BaseLLMClient:
    """Create an LLM client based on configuration."""
    match config.provider:
        case LLMProvider.OPENAI:
            return OpenAIClient(config.api_key, config.model, None)
        case LLMProvider.ANTHROPIC:
            return AnthropicClient(config.api_key, config.model)
        case LLMProvider.OPENAI_COMPATIBLE:
            return OpenAIClient(config.api_key, config.model, config.endpoint)
```

**Step 4: Update __init__.py**

Add to `api/src/services/llm/__init__.py`:
```python
from src.services.llm.factory import (
    LLMProvider,
    CompletionsConfig,
    EmbeddingsConfig,
    get_completions_config,
    get_embeddings_config,
    get_llm_client,
)

__all__ = [
    # ... existing exports ...
    "LLMProvider",
    "CompletionsConfig",
    "EmbeddingsConfig",
    "get_completions_config",
    "get_embeddings_config",
    "get_llm_client",
]
```

**Step 5: Run test to verify it passes**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/services/llm/test_factory.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add api/src/services/llm/factory.py api/src/services/llm/__init__.py api/tests/unit/services/llm/test_factory.py
git commit -m "feat: add LLM factory for provider-based client creation"
```

---

## Task 9: Update AI Chat Service

**Files:**
- Modify: `api/src/services/ai_chat.py`

**Step 1: Update existing tests**

Update `api/tests/unit/services/test_ai_chat.py` to use new abstraction:

```python
"""Tests for AI chat service with multi-provider support."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.ai_chat import AIChatService
from src.services.llm.base import LLMStreamChunk


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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/services/test_ai_chat.py -v`
Expected: FAIL (old implementation)

**Step 3: Update ai_chat.py**

Update `api/src/services/ai_chat.py` to use the new abstraction:

```python
"""AI Chat service using LLM abstraction layer."""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.llm import (
    LLMMessage,
    Role,
    get_completions_config,
    get_llm_client,
)
from src.models.contracts.search import SearchResult


class AIChatService:
    """Service for AI-powered chat using RAG."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def stream_response(
        self,
        query: str,
        search_results: list[SearchResult],
        *,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """Stream a response using search results as context."""
        config = await get_completions_config(self.db)
        if not config:
            raise ValueError("LLM is not configured")

        client = get_llm_client(config)

        # Build context from search results
        context = self._build_context(search_results)

        messages = [
            LLMMessage(
                role=Role.SYSTEM,
                content=self._get_system_prompt(),
            ),
            LLMMessage(
                role=Role.USER,
                content=f"Context:\n{context}\n\nQuestion: {query}",
            ),
        ]

        async for chunk in client.stream(messages, max_tokens=max_tokens):
            if chunk.type == "delta" and chunk.content:
                yield chunk.content

    async def get_response(
        self,
        query: str,
        search_results: list[SearchResult],
        *,
        max_tokens: int = 1024,
    ) -> str:
        """Get a complete response (non-streaming)."""
        config = await get_completions_config(self.db)
        if not config:
            raise ValueError("LLM is not configured")

        client = get_llm_client(config)

        context = self._build_context(search_results)

        messages = [
            LLMMessage(
                role=Role.SYSTEM,
                content=self._get_system_prompt(),
            ),
            LLMMessage(
                role=Role.USER,
                content=f"Context:\n{context}\n\nQuestion: {query}",
            ),
        ]

        response = await client.complete(messages, max_tokens=max_tokens)
        return response.content or ""

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the AI assistant."""
        return """You are a helpful assistant for a password and credential management system.
You help users find and understand their stored credentials, configurations, and documents.

IMPORTANT SECURITY RULES:
- NEVER reveal actual password values, even if they appear in the context
- You may reveal usernames, URLs, notes, and other non-sensitive metadata
- If asked for a password, explain that you cannot reveal it for security reasons
- Guide users to access passwords through the proper UI

Be concise and helpful. Use the provided context to answer questions accurately."""

    def _build_context(self, search_results: list[SearchResult]) -> str:
        """Build context string from search results."""
        if not search_results:
            return "No relevant information found."

        context_parts = []
        for result in search_results[:10]:  # Limit to top 10 results
            context_parts.append(
                f"- {result.entity_type}: {result.name}\n"
                f"  {result.searchable_text[:500]}"
            )

        return "\n\n".join(context_parts)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/services/test_ai_chat.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/services/ai_chat.py api/tests/unit/services/test_ai_chat.py
git commit -m "refactor: update ai_chat service to use LLM abstraction layer"
```

---

## Task 10: Update Embeddings Service

**Files:**
- Modify: `api/src/services/embeddings.py`

**Step 1: Update tests**

Update `api/tests/unit/services/test_embeddings.py`:

```python
"""Tests for embeddings service with new config loading."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/services/test_embeddings.py -v`
Expected: FAIL

**Step 3: Update embeddings.py**

Update the config loading in `api/src/services/embeddings.py`:

```python
# Replace the old _ensure_initialized method with:

async def _ensure_initialized(self) -> None:
    """Fetch AI settings from database if not already done."""
    if self._initialized:
        return

    from src.services.llm.factory import get_embeddings_config

    config = await get_embeddings_config(self.db)
    if config:
        self._api_key = config.api_key
        self._model = config.model
    else:
        self._api_key = None
        self._model = "text-embedding-3-small"

    self._initialized = True
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/services/test_embeddings.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/services/embeddings.py api/tests/unit/services/test_embeddings.py
git commit -m "refactor: update embeddings service to use new config loading"
```

---

## Task 11: Create API Contracts for AI Settings

**Files:**
- Create: `api/src/models/contracts/ai_settings.py` (replace existing)

**Step 1: Write the test**

Create/update `api/tests/unit/models/contracts/test_ai_settings.py`:

```python
"""Tests for AI settings contracts."""
import pytest
from pydantic import ValidationError

from src.models.contracts.ai_settings import (
    CompletionsConfigPublic,
    CompletionsConfigUpdate,
    EmbeddingsConfigPublic,
    EmbeddingsConfigUpdate,
    AISettingsResponse,
    ModelInfo,
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
        for provider in ["openai", "anthropic", "openai_compatible"]:
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

    def test_embeddings_config_public(self):
        """Test EmbeddingsConfigPublic model."""
        config = EmbeddingsConfigPublic(
            api_key_set=True,
            model="text-embedding-3-small",
        )
        assert config.api_key_set is True

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
        assert response.completions.provider == "openai"
        assert response.embeddings.api_key_set is True
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/models/contracts/test_ai_settings.py -v`
Expected: FAIL

**Step 3: Create/update contracts**

Create/update `api/src/models/contracts/ai_settings.py`:

```python
"""AI settings API contracts."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CompletionsConfigPublic(BaseModel):
    """Public view of completions configuration (API key masked)."""

    model_config = ConfigDict(from_attributes=True)

    provider: Literal["openai", "anthropic", "openai_compatible"] = Field(
        description="LLM provider"
    )
    api_key_set: bool = Field(description="Whether an API key is configured")
    model: str = Field(description="Selected model")
    endpoint: str | None = Field(
        default=None, description="Custom endpoint (for openai_compatible)"
    )


class CompletionsConfigUpdate(BaseModel):
    """Request to update completions configuration."""

    provider: Literal["openai", "anthropic", "openai_compatible"] | None = Field(
        default=None, description="LLM provider"
    )
    api_key: str | None = Field(
        default=None,
        min_length=1,
        description="API key (omit to keep existing)",
    )
    model: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Model name",
    )
    endpoint: str | None = Field(
        default=None,
        description="Custom endpoint (required for openai_compatible)",
    )
    max_tokens: int | None = Field(
        default=None,
        ge=1,
        le=100000,
        description="Max tokens for completions",
    )
    temperature: float | None = Field(
        default=None,
        ge=0,
        le=2,
        description="Temperature for completions",
    )


class EmbeddingsConfigPublic(BaseModel):
    """Public view of embeddings configuration (API key masked)."""

    model_config = ConfigDict(from_attributes=True)

    api_key_set: bool = Field(description="Whether an API key is configured")
    model: str = Field(description="Selected embedding model")


class EmbeddingsConfigUpdate(BaseModel):
    """Request to update embeddings configuration."""

    api_key: str | None = Field(
        default=None,
        min_length=1,
        description="OpenAI API key (omit to keep existing)",
    )
    model: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Embedding model name",
    )


class AISettingsResponse(BaseModel):
    """Combined AI settings response."""

    completions: CompletionsConfigPublic | None = Field(
        default=None, description="Completions configuration"
    )
    embeddings: EmbeddingsConfigPublic | None = Field(
        default=None, description="Embeddings configuration"
    )


class ModelInfo(BaseModel):
    """Information about an available model."""

    id: str = Field(description="Model identifier")
    display_name: str = Field(description="Human-readable model name")


class ModelsResponse(BaseModel):
    """Response containing available models."""

    models: list[ModelInfo] = Field(description="Available models")


class TestConnectionRequest(BaseModel):
    """Request to test LLM connection."""

    provider: Literal["openai", "anthropic", "openai_compatible"] = Field(
        description="Provider to test"
    )
    api_key: str = Field(min_length=1, description="API key to test")
    endpoint: str | None = Field(
        default=None, description="Custom endpoint (for openai_compatible)"
    )


class TestConnectionResponse(BaseModel):
    """Response from connection test."""

    success: bool = Field(description="Whether connection succeeded")
    models: list[ModelInfo] = Field(
        default_factory=list, description="Available models"
    )
    error: str | None = Field(default=None, description="Error message if failed")
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/models/contracts/test_ai_settings.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/models/contracts/ai_settings.py api/tests/unit/models/contracts/test_ai_settings.py
git commit -m "feat: add API contracts for multi-provider AI settings"
```

---

## Task 12: Update AI Settings Router

**Files:**
- Modify: `api/src/routers/ai_settings.py`

**Step 1: Write integration tests**

Create `api/tests/unit/routers/test_ai_settings.py`:

```python
"""Tests for AI settings router."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient


@pytest.mark.unit
class TestAISettingsRouter:
    """Tests for AI settings endpoints."""

    def test_get_settings_requires_superuser(self, client, normal_user_token):
        """Test that non-superusers cannot access settings."""
        response = client.get(
            "/api/settings/ai",
            headers={"Authorization": f"Bearer {normal_user_token}"},
        )
        assert response.status_code == 403

    def test_get_settings_returns_config(self, client, superuser_token):
        """Test getting AI settings."""
        with patch("src.routers.ai_settings.SystemConfigRepository") as mock_repo:
            mock_instance = MagicMock()
            mock_instance.get_config = AsyncMock(return_value=None)
            mock_repo.return_value = mock_instance

            response = client.get(
                "/api/settings/ai",
                headers={"Authorization": f"Bearer {superuser_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "completions" in data
            assert "embeddings" in data
```

**Step 2: Update the router**

Update `api/src/routers/ai_settings.py`:

```python
"""AI Settings router for multi-provider LLM configuration."""
from fastapi import APIRouter, HTTPException, Query, status
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from src.core.auth import CurrentActiveUser
from src.core.database import DbSession
from src.core.security import encrypt_secret, decrypt_secret
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
from src.repositories.system_config import SystemConfigRepository


router = APIRouter(prefix="/api/settings/ai", tags=["ai-settings"])


def require_superuser(user: CurrentActiveUser) -> None:
    """Raise 403 if user is not a superuser."""
    if not user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


@router.get("", response_model=AISettingsResponse)
async def get_ai_settings(
    current_user: CurrentActiveUser,
    db: DbSession,
) -> AISettingsResponse:
    """Get current AI settings."""
    require_superuser(current_user)

    repo = SystemConfigRepository(db)

    completions_config = await repo.get_config("llm", "completions_config")
    embeddings_config = await repo.get_config("llm", "embeddings_config")

    completions = None
    if completions_config:
        value = completions_config.value_json
        completions = CompletionsConfigPublic(
            provider=value["provider"],
            api_key_set=bool(value.get("api_key_encrypted")),
            model=value["model"],
            endpoint=value.get("endpoint"),
        )

    embeddings = None
    if embeddings_config:
        value = embeddings_config.value_json
        embeddings = EmbeddingsConfigPublic(
            api_key_set=bool(value.get("api_key_encrypted")),
            model=value["model"],
        )

    return AISettingsResponse(completions=completions, embeddings=embeddings)


@router.put("/completions", response_model=CompletionsConfigPublic)
async def update_completions_config(
    update_data: CompletionsConfigUpdate,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> CompletionsConfigPublic:
    """Update completions configuration."""
    require_superuser(current_user)

    repo = SystemConfigRepository(db)
    existing = await repo.get_config("llm", "completions_config")

    # Build new config, merging with existing
    if existing:
        value = existing.value_json.copy()
    else:
        value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "max_tokens": 4096,
            "temperature": 0.7,
        }

    if update_data.provider is not None:
        value["provider"] = update_data.provider
    if update_data.api_key is not None:
        value["api_key_encrypted"] = encrypt_secret(update_data.api_key)
    if update_data.model is not None:
        value["model"] = update_data.model
    if update_data.endpoint is not None:
        value["endpoint"] = update_data.endpoint
    if update_data.max_tokens is not None:
        value["max_tokens"] = update_data.max_tokens
    if update_data.temperature is not None:
        value["temperature"] = update_data.temperature

    # Validate: openai_compatible requires endpoint
    if value["provider"] == "openai_compatible" and not value.get("endpoint"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endpoint is required for OpenAI-compatible provider",
        )

    await repo.set_config("llm", "completions_config", value)
    await db.commit()

    return CompletionsConfigPublic(
        provider=value["provider"],
        api_key_set=bool(value.get("api_key_encrypted")),
        model=value["model"],
        endpoint=value.get("endpoint"),
    )


@router.put("/embeddings", response_model=EmbeddingsConfigPublic)
async def update_embeddings_config(
    update_data: EmbeddingsConfigUpdate,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> EmbeddingsConfigPublic:
    """Update embeddings configuration."""
    require_superuser(current_user)

    repo = SystemConfigRepository(db)
    existing = await repo.get_config("llm", "embeddings_config")

    if existing:
        value = existing.value_json.copy()
    else:
        value = {"model": "text-embedding-3-small"}

    if update_data.api_key is not None:
        value["api_key_encrypted"] = encrypt_secret(update_data.api_key)
    if update_data.model is not None:
        value["model"] = update_data.model

    await repo.set_config("llm", "embeddings_config", value)
    await db.commit()

    return EmbeddingsConfigPublic(
        api_key_set=bool(value.get("api_key_encrypted")),
        model=value["model"],
    )


@router.get("/models", response_model=ModelsResponse)
async def get_available_models(
    current_user: CurrentActiveUser,
    provider: str = Query(..., description="Provider: openai, anthropic"),
    api_key: str = Query(..., description="API key to use"),
) -> ModelsResponse:
    """Fetch available models from provider."""
    require_superuser(current_user)

    models = []

    if provider == "openai":
        client = AsyncOpenAI(api_key=api_key)
        response = await client.models.list()
        for model in response.data:
            if model.id.startswith(("gpt-", "o1", "o3")):
                models.append(ModelInfo(id=model.id, display_name=model.id))

    elif provider == "anthropic":
        client = AsyncAnthropic(api_key=api_key)
        response = await client.models.list()
        seen_names = set()
        for model in sorted(response.data, key=lambda x: x.id, reverse=True):
            display_name = getattr(model, "display_name", model.id)
            if display_name not in seen_names:
                seen_names.add(display_name)
                models.append(ModelInfo(id=model.id, display_name=display_name))

    elif provider == "openai_compatible":
        # Return empty list - user enters model manually
        pass

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider: {provider}",
        )

    return ModelsResponse(models=models)


@router.post("/test", response_model=TestConnectionResponse)
async def test_connection(
    request: TestConnectionRequest,
    current_user: CurrentActiveUser,
) -> TestConnectionResponse:
    """Test connection to LLM provider."""
    require_superuser(current_user)

    try:
        if request.provider == "openai":
            client = AsyncOpenAI(api_key=request.api_key)
            response = await client.models.list()
            models = [
                ModelInfo(id=m.id, display_name=m.id)
                for m in response.data
                if m.id.startswith(("gpt-", "o1", "o3"))
            ]
            return TestConnectionResponse(success=True, models=models)

        elif request.provider == "anthropic":
            client = AsyncAnthropic(api_key=request.api_key)
            response = await client.models.list()
            seen = set()
            models = []
            for m in sorted(response.data, key=lambda x: x.id, reverse=True):
                name = getattr(m, "display_name", m.id)
                if name not in seen:
                    seen.add(name)
                    models.append(ModelInfo(id=m.id, display_name=name))
            return TestConnectionResponse(success=True, models=models)

        elif request.provider == "openai_compatible":
            if not request.endpoint:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Endpoint required for openai_compatible",
                )
            client = AsyncOpenAI(api_key=request.api_key, base_url=request.endpoint)
            # Just try to list models to verify connection
            await client.models.list()
            return TestConnectionResponse(success=True, models=[])

    except Exception as e:
        return TestConnectionResponse(success=False, error=str(e))
```

**Step 3: Run tests**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest tests/unit/routers/test_ai_settings.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add api/src/routers/ai_settings.py api/tests/unit/routers/test_ai_settings.py
git commit -m "feat: update AI settings router for multi-provider support"
```

---

## Task 13: Clean Up Old AI Settings Code

**Files:**
- Delete: `api/src/models/orm/ai_settings.py`
- Delete: `api/src/repositories/ai_settings.py`
- Modify: `api/src/models/orm/__init__.py`
- Modify: `api/src/repositories/__init__.py`

**Step 1: Remove imports from __init__ files**

Remove `AISettings` from `api/src/models/orm/__init__.py`
Remove `AISettingsRepository` from `api/src/repositories/__init__.py`

**Step 2: Delete old files**

```bash
rm api/src/models/orm/ai_settings.py
rm api/src/repositories/ai_settings.py
```

**Step 3: Run all tests to verify nothing breaks**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove deprecated ai_settings model and repository"
```

---

## Task 14: Run Full Test Suite and Type Check

**Step 1: Run all tests**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pytest -v`
Expected: All tests pass

**Step 2: Run type checking**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && pyright`
Expected: No errors

**Step 3: Run linting**

Run: `cd /Users/jack/GitHub/gocovi-docs/api && ruff check`
Expected: No errors

**Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address any remaining type/lint issues"
```

---

## Summary

This plan creates a complete LLM abstraction layer with:

1. **Database**: New `system_config` table for flexible key-value storage
2. **Abstraction**: `BaseLLMClient` interface with OpenAI and Anthropic implementations
3. **Factory**: Provider-based client creation with config loading
4. **Services**: Updated `ai_chat.py` and `embeddings.py` to use new abstraction
5. **API**: New endpoints for managing completions and embeddings configs separately
6. **Cleanup**: Removed old `ai_settings` code

Frontend implementation (Task 15+) would follow similar patterns for the settings UI.
