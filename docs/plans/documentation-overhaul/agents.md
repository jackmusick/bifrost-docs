# Agents

## Source of Truth (Codebase Review)

_Completed by Codebase Agent_

### Current Features

#### 1. Agent Data Model

**Location**: `/Users/jack/GitHub/bifrost/api/src/models/orm/agents.py`

The Agent model is a fully virtual database entity with the following structure:

```python
class Agent(Base):
    __tablename__ = "agents"

    # Core identity
    id: UUID                    # Primary key
    name: str                   # Agent display name (max 255 chars)
    description: str | None     # Optional description (max 2000 chars)
    system_prompt: str          # The agent's system prompt (max 50000 chars)

    # Configuration
    channels: list[str]         # JSONB - channels agent is available on (default: ["chat"])
    access_level: AgentAccessLevel  # ROLE_BASED or AUTHENTICATED
    organization_id: UUID | None    # NULL = global, else org-specific

    # Feature flags
    is_active: bool             # Soft delete flag
    is_coding_mode: bool        # Enables Claude Agent SDK for coding tasks
    is_system: bool             # System agents can't be deleted

    # RAG and Tools
    knowledge_sources: list[str]  # Array of knowledge namespace names for RAG
    system_tools: list[str]       # Array of enabled system tool IDs

    # Metadata
    created_by: str
    created_at: datetime
    updated_at: datetime
```

**Relationships** (Junction Tables in same file):
- `AgentTool` - Links agents to workflows (type='tool')
- `AgentDelegation` - Parent/child agent delegation relationships
- `AgentRole` - Links agents to roles for RBAC

#### 2. Agent Virtualization (No S3 Storage)

**Key Architecture Decision**: Agents exist ONLY in the database. There is no file storage for agents.

**Location**: `/Users/jack/GitHub/bifrost/api/src/routers/agents.py` (line 7-8 comment)
```python
# Agents are virtual entities stored only in the database.
# Git sync serializes agents on-the-fly from the database.
```

**How Git Sync Works for Agents**:

1. **Virtual File Provider** (`/Users/jack/GitHub/bifrost/api/src/services/github_sync_virtual_files.py`)
   - `VirtualFileProvider` class generates virtual files on-the-fly from DB entities
   - Agents are serialized to `agents/{agent.id}.agent.json` path pattern
   - Uses `_get_agent_files()` method (line 226)

2. **Agent Serialization** (`/Users/jack/GitHub/bifrost/api/src/services/file_storage/indexers/agent.py`)
   - `_serialize_agent_to_json()` function (line 24) converts Agent ORM to JSON
   - Uses `AgentPublic.model_dump()` with serialization context
   - Supports portable workflow refs (UUID -> path::function_name) for cross-environment sync
   - Adds `_export` metadata for portable ref tracking

3. **Agent Indexing** (same file, `AgentIndexer` class line 59)
   - `index_agent()` parses `.agent.json` files and syncs to database
   - Handles ID injection for files without IDs
   - Syncs tool and delegation associations
   - Note: `organization_id` and `access_level` are NOT synced from files (env-specific)

#### 3. Agent Repository

**Location**: `/Users/jack/GitHub/bifrost/api/src/repositories/agents.py`

`AgentRepository` extends `OrgScopedRepository` with:
- **Cascade scoping**: Org users see their org's agents + global agents
- **Role-based access**: Checks `AgentRole` junction table
- Key methods:
  - `list_agents()` - Lists with role filtering (line 33)
  - `list_all_in_scope()` - Admin view without role filtering (line 71)
  - `get_agent_with_access_check()` - Single agent with cascade + role check (line 145)

#### 4. Agent CRUD Endpoints

**Location**: `/Users/jack/GitHub/bifrost/api/src/routers/agents.py`

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/agents` | GET | Active User | List agents (filtered by scope/roles) |
| `/api/agents` | POST | Superuser | Create new agent |
| `/api/agents/{id}` | GET | Active User | Get agent by ID |
| `/api/agents/{id}` | PUT | Superuser | Update agent |
| `/api/agents/{id}` | DELETE | Superuser | Soft delete agent |
| `/api/agents/{id}/tools` | GET | Active User | Get assigned tools |
| `/api/agents/{id}/tools` | POST | Superuser | Assign tools |
| `/api/agents/{id}/tools/{wf_id}` | DELETE | Superuser | Remove tool |
| `/api/agents/{id}/delegations` | GET | Active User | Get delegations |
| `/api/agents/{id}/delegations` | POST | Superuser | Assign delegations |
| `/api/agents/{id}/delegations/{del_id}` | DELETE | Superuser | Remove delegation |

**Validation** (`_validate_agent_references()` line 40):
- Validates tool_ids reference active workflows with type='tool'
- Validates delegated_agent_ids reference active agents
- Prevents self-delegation

#### 5. Agent Execution System

**Location**: `/Users/jack/GitHub/bifrost/api/src/services/agent_executor.py`

`AgentExecutor` handles the chat completion loop:

1. **Message Routing** (uses `AgentRouter`)
   - `@[Agent Name]` mention parsing with `MENTION_PATTERN` regex
   - AI-based routing for first message in agentless conversations

2. **Tool Execution Loop** (line 275)
   - Max 10 iterations (`MAX_TOOL_ITERATIONS`)
   - Streams LLM responses via `ChatStreamChunk`
   - Executes workflow tools via `execute_tool()` service

3. **Context Management**
   - Token estimation (~4 chars/token heuristic)
   - Context pruning with summarization at 120K tokens
   - Warning at 100K tokens

4. **Special Tools**:
   - `search_knowledge` - Built-in RAG search (line 949)
   - `delegate_to_{agent_name}` - Agent delegation (line 1036)

#### 6. Agent Router

**Location**: `/Users/jack/GitHub/bifrost/api/src/services/agent_router.py`

- `parse_mention()` - Finds `@[Agent Name]` in messages
- `route_message()` - AI-powered intent routing to best agent
- `strip_mention()` - Removes mention from message text
- Routing considers agent description, tools, and knowledge sources

#### 7. Chat System

**Location**: `/Users/jack/GitHub/bifrost/api/src/routers/chat.py`

**Conversation Model** (in agents.py ORM file):
```python
class Conversation(Base):
    agent_id: UUID | None  # NULL for agentless chat
    user_id: UUID
    channel: str
    title: str | None
    extra_data: dict       # Channel-specific metadata
    is_active: bool
```

**Message Model**:
```python
class Message(Base):
    conversation_id: UUID
    role: MessageRole      # USER, ASSISTANT, TOOL, SYSTEM
    content: str | None
    tool_calls: list | None     # [{id, name, arguments}]
    tool_call_id: str | None    # For tool results
    tool_name: str | None
    execution_id: str | None    # For log retrieval
    sequence: int               # Order in conversation
```

#### 8. Coding Mode (Claude Agent SDK)

**Location**: `/Users/jack/GitHub/bifrost/api/src/services/coding_mode/client.py`

`CodingModeClient` wraps Claude Agent SDK with Bifrost-specific features:

- **System Tools**: File ops (Read, Write, Edit, Glob, Grep, Bash), WebSearch, TodoWrite
- **MCP Integration**: Bifrost MCP server for workflow execution, knowledge search
- **Permission Modes**: `PLAN` (read-only) or `EXECUTE` (full access)
- **Session Management**: Redis-based with 24hr TTL (`SessionManager` in session.py)
- **AskUserQuestion**: Interactive prompts during execution
- **TodoWrite**: Task tracking with frontend updates

**System Coding Agent** (`/Users/jack/GitHub/bifrost/api/src/core/system_agents.py`):
- Auto-created on startup via `ensure_coding_agent()`
- Name: "Coding Assistant"
- Flags: `is_coding_mode=True`, `is_system=True`
- Access: `ROLE_BASED` with no roles = platform admins only
- Has all system tools and `bifrost-docs` knowledge source

#### 9. Tool Registry

**Location**: `/Users/jack/GitHub/bifrost/api/src/services/tool_registry.py`

`ToolRegistry` provides LLM-friendly tool definitions from workflows:
- `get_all_tools()` - All active workflows with type='tool'
- `get_tool_definitions()` - Converts to OpenAI/Anthropic format
- `_map_type_to_json_schema()` - Type conversion for parameters

**System Tools** (`/Users/jack/GitHub/bifrost/api/src/routers/tools.py`):
- Auto-discovered from `@system_tool` decorated functions
- Available via `/api/tools` and `/api/tools/system` endpoints

#### 10. Contract Models

**Location**: `/Users/jack/GitHub/bifrost/api/src/models/contracts/agents.py`

Key Pydantic models:
- `AgentCreate`, `AgentUpdate`, `AgentPublic`, `AgentSummary`
- `ConversationCreate`, `ConversationPublic`, `ConversationSummary`
- `MessagePublic`, `ChatRequest`, `ChatResponse`
- `ChatStreamChunk` - Unified streaming format (regular + coding mode)
- `ToolCall`, `ToolResult`, `ToolProgress`
- `TodoItem`, `AskUserQuestion` - Coding mode specific
- `AgentSwitch`, `ContextWarning` - Execution events

#### 11. Frontend Implementation

**Hooks** (`/Users/jack/GitHub/bifrost/client/src/hooks/useAgents.ts`):
- `useAgents(filterScope?)` - List agents with scope filtering
- `useAgent(id)`, `useAgentTools(id)`, `useAgentDelegations(id)`
- Mutation hooks for CRUD and assignments

**Pages** (`/Users/jack/GitHub/bifrost/client/src/pages/Agents.tsx`):
- Grid/table view toggle
- Organization filtering for platform admins
- Search by name/description
- Create/edit via `AgentDialog` component

**Chat Components** (`/Users/jack/GitHub/bifrost/client/src/components/chat/`):
- `ChatLayout.tsx`, `ChatWindow.tsx`, `ChatMessage.tsx`
- `ChatInput.tsx`, `ChatSidebar.tsx`
- `MentionPicker.tsx` - @mention autocomplete
- `ChatSystemEvent.tsx` - Agent switch/context events

### Recent Changes

1. **Agent Virtualization** - Agents moved from S3 file storage to database-only
2. **File Path Removal** - `file_path` column removed from agents table (migration `20260119_160000_remove_file_path_columns.py`)
3. **Coding Mode** - Added `is_coding_mode` and `is_system` flags
4. **System Tools** - Added `system_tools` array for granular tool access
5. **Knowledge Sources** - Added `knowledge_sources` for RAG integration
6. **Nullable Agent ID** - Conversations can now have NULL `agent_id` for agentless chat

### Key Concepts to Document

1. **Agent Architecture**
   - Virtual entity model (DB-only, no file storage)
   - Git sync serialization with portable refs
   - Organization scoping and cascade pattern

2. **Access Control**
   - `AUTHENTICATED` vs `ROLE_BASED` access levels
   - Role assignment via `AgentRole` junction table
   - Platform admin bypass

3. **Tool Integration**
   - Workflow tools (type='tool') assignment
   - System tools configuration
   - Tool execution via workflow runner

4. **Agent Delegation**
   - Parent-child agent relationships
   - Delegation tool generation
   - Execution flow

5. **Knowledge Base Integration**
   - `knowledge_sources` namespace configuration
   - `search_knowledge` built-in tool
   - RAG search during execution

6. **Chat System**
   - Conversation lifecycle
   - Message types and tool calls
   - Streaming response format

7. **Coding Mode**
   - Claude Agent SDK integration
   - Permission modes (PLAN vs EXECUTE)
   - MCP server tools
   - Session management

8. **Agent Routing**
   - @mention syntax
   - AI-based intent routing
   - Agent switching events

9. **Context Management**
   - Token estimation
   - Context pruning and summarization
   - Warning thresholds

---

## Documentation State (Docs Review)

_Completed by Docs Review Agent on 2026-01-20_

### Existing Docs

| File | Purpose |
|------|---------|
| `/src/content/docs/how-to-guides/ai/agents-and-chat.mdx` | Main agents and chat documentation |
| `/src/content/docs/how-to-guides/ai/knowledge-bases.mdx` | Knowledge base / RAG documentation |
| `/src/content/docs/how-to-guides/ai/llm-configuration.mdx` | LLM provider configuration |
| `/src/content/docs/how-to-guides/ai/using-ai-in-workflows.mdx` | AI completions in workflows |
| `/src/content/docs/sdk-reference/sdk/ai-module.mdx` | AI module SDK reference |
| `/src/content/docs/sdk-reference/sdk/knowledge-module.mdx` | Knowledge module SDK reference |

**Note:** No dedicated "Agents" core concept page exists.

### Gaps Identified

#### Critical Gaps (Fix Immediately)

1. **Access Level Documentation is INCORRECT**
   - Docs show "Public, Authenticated, Role-based" levels
   - Code only has `AUTHENTICATED` and `ROLE_BASED` - "Public" does not exist
   - Missing: cascade scoping pattern (org users see org + global agents)
   - Missing: platform admin bypass documentation
   - Missing: role assignment via AgentRole junction table

2. **Agent Architecture Not Documented**
   - Agents are virtual database entities only (no file storage)
   - Git sync serializes on-the-fly from database
   - Portable workflow refs for cross-environment deployment
   - Users may incorrectly assume file-based storage

#### Moderate Gaps (High Impact)

3. **System Tools vs Workflow Tools Unclear**
   - Two distinct tool types: workflow tools (junction table) vs system tools (array)
   - Missing: `system_tools` configuration field documentation
   - Missing: How to enable system tools for custom agents
   - Coding Agent gets all system tools by default (not explained)

4. **Coding Mode Incomplete**
   - Missing: Permission modes (PLAN vs EXECUTE)
   - Missing: Session management (Redis, 24hr TTL)
   - Missing: MCP integration details
   - Missing: `AskUserQuestion` interactive prompts
   - Missing: `TodoWrite` task tracking

#### Minor Gaps (Completeness)

5. **@Mention Syntax Wrong** - Docs show `@agent-name`, code uses `@[Agent Name]`

6. **Chat System Details Missing**
   - Missing: Message model fields (tool_calls, execution_id)
   - Missing: Context management (token estimation, pruning at 120K)
   - Missing: Streaming event types (ToolProgress, AgentSwitch, ContextWarning)

7. **Delegation Details Missing**
   - Missing: Automatic `delegate_to_{name}` tool generation
   - Missing: Self-delegation prevention
   - Missing: Delegation CRUD API endpoints

### Recommended Actions

#### Priority 1 - Correctness
- [ ] Fix access level table (remove "Public", clarify AUTHENTICATED vs ROLE_BASED)
- [ ] Add cascade scoping documentation
- [ ] Document agent architecture (database-only, Git sync behavior)

#### Priority 2 - Completeness
- [ ] Add system tools vs workflow tools distinction
- [ ] Document `system_tools` configuration
- [ ] Expand Coding Mode section with permission modes, sessions, MCP
- [ ] Create `/core-concepts/agents.mdx` conceptual overview page

#### Priority 3 - Polish
- [ ] Fix @mention syntax in examples
- [ ] Add streaming event documentation
- [ ] Expand delegation documentation

**Full details:** See `/docs/plans/documentation-overhaul/findings/agents.md`
