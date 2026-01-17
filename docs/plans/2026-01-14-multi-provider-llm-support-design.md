# Multi-Provider LLM Support Design

## Overview

Add support for multiple LLM providers for completions (chat) while keeping embeddings OpenAI-only. This enables using Anthropic for faster completions while retaining OpenAI's embedding quality.

## Provider Support

| Feature | Providers |
|---------|-----------|
| **Completions** | OpenAI, Anthropic, OpenAI-compatible |
| **Embeddings** | OpenAI only |

## Database Schema

### New `system_config` Table

```sql
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(50) NOT NULL,
    key VARCHAR(100) NOT NULL,
    value_json JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(category, key)
);
```

### Completions Config

**Location:** `category="llm"`, `key="completions_config"`

```json
{
  "provider": "anthropic",
  "api_key_encrypted": "gAAA...",
  "model": "claude-sonnet-4-20250514",
  "endpoint": null,
  "max_tokens": 4096,
  "temperature": 0.7
}
```

- `provider`: `"openai"`, `"anthropic"`, or `"openai_compatible"`
- `endpoint`: Required for `openai_compatible`, null otherwise

### Embeddings Config

**Location:** `category="llm"`, `key="embeddings_config"`

```json
{
  "api_key_encrypted": "gAAA...",
  "model": "text-embedding-3-small"
}
```

### Migration

- Drop `ai_settings` table
- Create `system_config` table
- Users re-enter API keys (project not yet deployed)

## Abstraction Layer

### File Structure

```
api/src/services/llm/
├── __init__.py
├── base.py              # Types and BaseLLMClient
├── openai_client.py     # OpenAI implementation
├── anthropic_client.py  # Anthropic implementation
└── factory.py           # Config loading and client factory
```

### Core Types

**File: `api/src/services/llm/base.py`**

```python
from enum import Enum
from dataclasses import dataclass
from typing import AsyncGenerator, Literal
from abc import ABC, abstractmethod

class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

@dataclass
class LLMMessage:
    role: Role
    content: str

@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict  # JSON Schema

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict

@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall]
    finish_reason: str

@dataclass
class LLMStreamChunk:
    type: Literal["delta", "tool_call", "done", "error"]
    content: str | None = None
    tool_call: ToolCall | None = None
    error: str | None = None

class BaseLLMClient(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        **kwargs
    ) -> LLMResponse: ...

    @abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        **kwargs
    ) -> AsyncGenerator[LLMStreamChunk, None]: ...
```

### Provider Implementations

**File: `api/src/services/llm/openai_client.py`**

```python
class OpenAIClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str, endpoint: str | None = None):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=endpoint  # None = default, or custom for OpenAI-compatible
        )
        self.model = model

    async def complete(self, messages, tools=None, **kwargs) -> LLMResponse:
        # Convert LLMMessage -> OpenAI format
        # Convert ToolDefinition -> OpenAI function format
        # Call client.chat.completions.create()
        # Convert response -> LLMResponse

    async def stream(self, messages, tools=None, **kwargs):
        # Same conversion, but stream=True
        # Yield LLMStreamChunk for each delta
```

**File: `api/src/services/llm/anthropic_client.py`**

```python
class AnthropicClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def complete(self, messages, tools=None, **kwargs) -> LLMResponse:
        # Extract system message (Anthropic handles separately)
        # Convert LLMMessage -> Anthropic block format
        # Convert ToolDefinition -> Anthropic tool format
        # Call client.messages.create()
        # Convert response -> LLMResponse

    async def stream(self, messages, tools=None, **kwargs):
        # Same but with stream=True
        # Handle Anthropic's event types (content_block_delta, etc.)
```

### Factory & Config Loading

**File: `api/src/services/llm/factory.py`**

```python
from enum import Enum

class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENAI_COMPATIBLE = "openai_compatible"

@dataclass
class CompletionsConfig:
    provider: LLMProvider
    api_key: str  # Decrypted
    model: str
    endpoint: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.7

async def get_completions_config(session: AsyncSession) -> CompletionsConfig | None:
    """Load and decrypt completions config from system_config table."""
    row = await session.execute(
        select(SystemConfig).where(
            SystemConfig.category == "llm",
            SystemConfig.key == "completions_config"
        )
    )
    # Decrypt api_key_encrypted, return CompletionsConfig

def get_llm_client(config: CompletionsConfig) -> BaseLLMClient:
    """Factory: return appropriate client based on provider."""
    match config.provider:
        case LLMProvider.OPENAI:
            return OpenAIClient(config.api_key, config.model)
        case LLMProvider.ANTHROPIC:
            return AnthropicClient(config.api_key, config.model)
        case LLMProvider.OPENAI_COMPATIBLE:
            return OpenAIClient(config.api_key, config.model, config.endpoint)
```

## API Endpoints

### Settings Endpoints

```python
# GET /api/settings/ai
# Returns current config (API keys masked)
{
  "completions": {
    "provider": "anthropic",
    "api_key_set": true,
    "model": "claude-sonnet-4-20250514",
    "endpoint": null
  },
  "embeddings": {
    "api_key_set": true,
    "model": "text-embedding-3-small"
  }
}

# PUT /api/settings/ai/completions
# Update completions config
{
  "provider": "anthropic",
  "api_key": "sk-ant-...",  # Optional if unchanged
  "model": "claude-sonnet-4-20250514",
  "endpoint": null
}

# PUT /api/settings/ai/embeddings
# Update embeddings config
{
  "api_key": "sk-...",  # Optional if unchanged
  "model": "text-embedding-3-small"
}

# GET /api/settings/ai/models?provider=anthropic&api_key=...
# Fetch available models for provider
# Returns: [{"id": "claude-sonnet-4-20250514", "display_name": "Claude Sonnet 4"}]
# For openai_compatible: returns empty list (user enters model manually)

# POST /api/settings/ai/test
# Test connection with provided credentials
{
  "provider": "anthropic",
  "api_key": "sk-ant-...",
  "model": "claude-sonnet-4-20250514"
}
```

## Frontend Settings UI

### Layout

Single settings page with two sections:

**Completions Section:**
1. Provider dropdown: `OpenAI` | `Anthropic` | `OpenAI Compatible`
2. API Key field (password input, shows "••••••" if already set)
3. Endpoint field (only visible when `OpenAI Compatible` selected)
4. Model dropdown (fetches from API on valid key)
   - For `OpenAI Compatible`: free text input instead of dropdown

**Embeddings Section:**
1. API Key field with checkbox: "Use same API key as Completions"
   - Checked by default if completions provider is OpenAI
2. Model dropdown (fetches OpenAI embedding models)

### UX Flow

1. User selects provider → clears model selection
2. User enters API key → triggers model fetch
3. Model dropdown populates → user selects model
4. Save button → validates and persists

### Smart API Key Sharing

- If Completions provider is `OpenAI` and user checks "Use same key", embeddings inherits the key
- Stored separately in database, but UI reduces duplication

## Integration

### ai_chat.py Changes

```python
# Before (OpenAI-coupled):
from openai import AsyncOpenAI
client = AsyncOpenAI(api_key=settings.openai_api_key)
response = await client.chat.completions.create(...)

# After (provider-agnostic):
from services.llm import get_completions_config, get_llm_client

config = await get_completions_config(session)
if not config:
    raise AINotConfiguredError()

client = get_llm_client(config)
async for chunk in client.stream(messages):
    yield chunk.content
```

### embeddings.py Changes

- Still OpenAI-only, reads from new `system_config` table
- `get_embeddings_config(session)` returns API key + model
- No abstraction layer needed (single provider)

### System Prompt Handling

- OpenAI: system message in messages array
- Anthropic: extracted and passed as `system` parameter
- Handled internally by each client implementation

## Dependencies

Add to `requirements.txt`:
```
anthropic>=0.40.0
```

## Files to Create/Modify

### New Files
- `api/src/services/llm/__init__.py`
- `api/src/services/llm/base.py`
- `api/src/services/llm/openai_client.py`
- `api/src/services/llm/anthropic_client.py`
- `api/src/services/llm/factory.py`
- `api/src/models/orm/system_config.py`
- `api/src/repositories/system_config.py`
- Migration file for `system_config` table

### Modified Files
- `api/src/services/ai_chat.py` - Use new abstraction
- `api/src/services/embeddings.py` - Update config loading
- `api/src/routers/settings.py` - New endpoints
- Frontend settings components
