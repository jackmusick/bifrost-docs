# SDK Workflows

## Source of Truth (Codebase Review)

_Completed by Codebase Agent - 2026-01-20_

### Current Features

#### 1. Bifrost SDK Package (`/api/bifrost/`)

The Bifrost SDK is a Python package that workflows import to access platform capabilities. It provides context-aware modules that automatically use the current execution context.

**Entry Point** - `/api/bifrost/__init__.py`
```python
# Exports all SDK modules as submodules
from bifrost import ai, config, files, integrations, knowledge, tables, workflows, executions, organizations
```

**SDK Modules:**

| Module | File | Purpose |
|--------|------|---------|
| `ai` | `/api/bifrost/ai.py` | LLM operations (chat completion, structured output, embeddings) |
| `config` | `/api/bifrost/config.py` | Workflow configuration values (get, set, list, delete) |
| `files` | `/api/bifrost/files.py` | File operations (read, write, list, delete) with local/cloud modes |
| `integrations` | `/api/bifrost/integrations.py` | Integration credentials (get_client, list, get_credentials) |
| `knowledge` | `/api/bifrost/knowledge.py` | Knowledge base search and retrieval |
| `tables` | `/api/bifrost/tables.py` | Data storage (create, query, insert, update, delete tables/records) |
| `workflows` | `/api/bifrost/workflows.py` | Run other workflows, get metadata |
| `executions` | `/api/bifrost/executions.py` | Query execution history |
| `organizations` | `/api/bifrost/organizations.py` | Organization management |

**Context Management** - `/api/bifrost/_context.py`
- Thread-local storage for `ExecutionContext`
- Functions: `set_context()`, `get_context()`, `clear_context()`
- Context contains: `workflow_id`, `execution_id`, `organization_id`, `user_id`, `base_url`, `auth_token`

**HTTP Client** - `/api/bifrost/client.py`
- `BifrostClient` class with async httpx
- Auto-injects auth headers from context
- Methods: `get()`, `post()`, `put()`, `patch()`, `delete()`

**Data Models** - `/api/bifrost/models.py`
- `ExecutionContext` dataclass
- `FileLocation` enum: `WORKSPACE`, `TEMP`, `UPLOADS`
- `FileInfo`, `ReadFileResult`, `WriteFileResult` dataclasses

#### 2. Workflow Decorators (`/api/src/sdk/decorators.py`)

Three main decorators transform Python functions into platform-aware executables:

**`@workflow` Decorator** - Primary workflow decorator with extensive options:
```python
@workflow(
    name="My Workflow",           # Display name
    description="Description",     # Documentation
    category="Category",           # For organization
    tags=["tag1", "tag2"],        # Searchable tags
    execution_mode="sync"|"async", # Sync or async execution
    timeout_seconds=300,           # Execution timeout (default 300)
    retry_policy={"max_retries": 3, "delay_seconds": 60},
    schedule="0 9 * * *",          # Cron schedule for scheduled workflows
    endpoint_enabled=True,         # Enable HTTP endpoint
    allowed_methods=["GET", "POST"], # Allowed HTTP methods
    disable_global_key=False,      # Disable global API key auth
    public_endpoint=False,         # Allow unauthenticated access
    is_tool=False,                 # Mark as AI agent tool
    tool_description="...",        # Description for AI agents
    time_saved=5,                  # ROI tracking: minutes saved per run
    value=10.0,                    # ROI tracking: dollar value per run
)
async def my_workflow(input_data):
    pass
```

**`@tool` Decorator** - Shorthand for AI agent tools:
```python
@tool(name="search_docs", description="Search documentation")
async def search_docs(query: str):
    pass
# Equivalent to: @workflow(is_tool=True, tool_description="...")
```

**`@data_provider` Decorator** - For form/app builder data sources:
```python
@data_provider(
    name="Get Users",
    description="Returns list of users",
    cache_ttl=300,  # Cache results for 5 minutes
)
async def get_users():
    return [{"id": 1, "name": "User 1"}]
```

All decorators store metadata in `function._executable_metadata` attribute containing:
- `type`: "workflow" | "data_provider"
- `name`, `description`, `category`, `tags`
- Execution settings (timeout, retry, schedule)
- Endpoint configuration
- ROI tracking values

#### 3. Execution Engine (`/api/src/services/execution/`)

**Execution Service** - `/api/src/services/execution/service.py`

High-level service layer with Redis caching:

| Function | Purpose |
|----------|---------|
| `get_workflow_metadata_only()` | Cached metadata lookup (5-min TTL in Redis) |
| `get_workflow_for_execution()` | Get workflow data for subprocess execution |
| `get_workflow_by_id()` | Load workflow function and metadata from file |
| `run_workflow()` | Queue async execution via RabbitMQ |
| `run_code()` | Execute inline Python code (for MCP/coding mode) |
| `execute_tool()` | Execute workflow as AI agent tool |

**Unified Execution Engine** - `/api/src/services/execution/engine.py`

Core execution logic for both workflows and inline scripts:

```python
@dataclass
class ExecutionRequest:
    workflow_id: str | None
    execution_id: str
    organization_id: str
    input_data: dict
    script: str | None          # For inline code execution
    timeout_seconds: int
    # ... additional fields

@dataclass
class ExecutionResult:
    success: bool
    output: Any
    error: str | None
    variables: dict             # Captured variables via sys.settrace()
    logs: list[str]
    duration_ms: int
    tokens_used: dict | None
```

**Key Engine Features:**
- **Unified execution path**: Same `execute()` function handles workflows and scripts
- **Variable capture**: Uses `sys.settrace()` to capture assigned variables during execution
- **Log streaming**: Real-time logs via Redis PubSub (`execution:{id}:logs` channel)
- **Context injection**: Sets up `ExecutionContext` before running workflow code
- **ROI tracking**: Captures `time_saved` and `value` from workflow metadata
- **Error handling**: Comprehensive exception handling with structured error output

**Workflow Loading** - `/api/src/services/execution/loader.py`
- `load_workflow_module()`: Dynamically imports workflow Python file
- `find_workflow_function()`: Locates decorated function in module
- Supports both `@workflow` and `@data_provider` decorated functions

#### 4. File Operations (`/api/bifrost/files.py` + `/api/src/routers/files.py`)

**SDK Module** (`/api/bifrost/files.py`):
```python
# Two operation modes
MODE_LOCAL = "local"   # Direct filesystem access
MODE_CLOUD = "cloud"   # API-based access via HTTP

# Three file locations
class FileLocation(Enum):
    WORKSPACE = "workspace"  # Persistent workflow workspace
    TEMP = "temp"            # Temporary execution files
    UPLOADS = "uploads"      # User-uploaded files

# Key functions
async def read_file(path: str, location: FileLocation = WORKSPACE, as_base64: bool = False)
async def write_file(path: str, content: str | bytes, location: FileLocation = WORKSPACE)
async def list_files(path: str = "", location: FileLocation = WORKSPACE)
async def delete_file(path: str, location: FileLocation = WORKSPACE)
async def file_exists(path: str, location: FileLocation = WORKSPACE)
```

**API Endpoints** (`/api/src/routers/files.py`):
- `POST /api/files/read` - Read file content
- `POST /api/files/write` - Write file content
- `POST /api/files/delete` - Delete file
- `POST /api/files/list` - List directory contents
- `POST /api/files/exists` - Check file existence

**Editor Endpoints** (for browser-based file editor):
- `GET /api/files/editor/tree` - Get file tree structure
- `GET /api/files/editor/file` - Read file with metadata
- `POST /api/files/editor/file` - Create/update file
- `DELETE /api/files/editor/file` - Delete file
- `POST /api/files/editor/directory` - Create directory

**Base64 Binary Support**:
- `as_base64=True` parameter for reading binary files
- Automatic base64 encoding/decoding for binary content
- Supports images, PDFs, and other binary formats

#### 5. Workflow Execution Consumer (`/api/src/jobs/consumers/workflow_execution.py`)

RabbitMQ consumer that processes async workflow executions:
- Listens to `workflow_execution` queue
- Creates execution record in database
- Calls `engine.execute()` with request parameters
- Updates execution record with results
- Handles retries based on workflow retry policy

#### 6. SDK Generator (`/api/src/services/sdk_generator.py`)

Generates Python SDKs from OpenAPI specifications:

```python
class SDKGenerator:
    def generate(self, openapi_spec: dict, config: SDKConfig) -> str:
        # Generates complete Python SDK with:
        # - Dataclass models from schemas
        # - API client class with typed methods
        # - Authentication handling (bearer, api_key, basic, oauth)
```

**Supported Auth Types:**
- `bearer` - Bearer token in Authorization header
- `api_key` - API key in header or query parameter
- `basic` - HTTP Basic authentication
- `oauth` - OAuth 2.0 with token refresh

**Output Structure:**
- Python dataclasses for all schema types
- Async API client with httpx
- Type hints for all parameters and returns
- Error handling with custom exceptions

#### 7. Workflow API Endpoints (`/api/src/routers/workflows.py`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/workflows` | GET | List workflows with filtering |
| `/api/workflows/{id}` | GET | Get workflow details |
| `/api/workflows` | POST | Create new workflow |
| `/api/workflows/{id}` | PUT | Update workflow |
| `/api/workflows/{id}` | DELETE | Delete workflow |
| `/api/workflows/{id}/execute` | POST | Execute workflow synchronously |
| `/api/workflows/{id}/run` | POST | Queue async execution |
| `/api/workflows/{id}/test` | POST | Test workflow with sample input |
| `/api/workflows/code/execute` | POST | Execute inline code (MCP) |
| `/api/execute/{key}` | GET/POST | Execute by global key (public endpoints) |

### Recent Changes

Based on codebase architecture and memory context:

1. **Unified Execution Engine**: Consolidated workflow and script execution into single `engine.execute()` function, eliminating duplicate code paths

2. **Variable Capture via sys.settrace()**: Added ability to capture variables assigned during workflow execution for debugging and result inspection

3. **Redis-Cached Metadata**: Workflow metadata now cached in Redis with 5-minute TTL, reducing database queries for frequently-accessed workflows

4. **Real-time Log Streaming**: Execution logs streamed via Redis PubSub, enabling live log viewing in UI during workflow execution

5. **Base64 Binary File Support**: Added `as_base64` parameter to file operations for handling binary files (images, PDFs, etc.)

6. **ROI Tracking Integration**: `time_saved` and `value` parameters in `@workflow` decorator captured during execution for ROI reporting

7. **Enhanced Error Handling**: Structured error responses with `WorkflowNotFoundError`, `WorkflowLoadError`, and detailed execution failure messages

### Key Concepts to Document

#### For Workflow Developers (Users)

1. **Workflow Decorator Options** - Complete reference for all `@workflow` parameters
2. **SDK Module Reference** - API documentation for each SDK module (ai, config, files, etc.)
3. **File Operations** - How to read/write files, understand locations, handle binary content
4. **Execution Modes** - Difference between sync and async execution
5. **Workflow Triggers** - HTTP endpoints, schedules, form submissions, agent tool calls
6. **Error Handling** - How to handle and report errors in workflows
7. **Testing Workflows** - Using the test endpoint and debugging techniques
8. **ROI Tracking** - Setting `time_saved` and `value` for business metrics

#### For Platform Developers (Internal)

1. **Execution Engine Architecture** - How `engine.execute()` works
2. **Context Management** - Thread-local context and how it propagates
3. **Workflow Loading** - Dynamic module import and function discovery
4. **Redis Caching Strategy** - What's cached and cache invalidation
5. **RabbitMQ Message Format** - Queue message structure for async execution
6. **SDK Generator** - How to generate SDKs from OpenAPI specs

#### Cross-Cutting Concerns

1. **Authentication Flow** - How auth tokens propagate from request to SDK calls
2. **Multi-tenancy** - Organization scoping in workflow execution
3. **Logging and Observability** - Log capture, streaming, and storage
4. **Timeout and Retry** - How timeouts and retries are enforced

---

## Documentation State (Docs Review)

_Completed by Docs Review Agent - 2026-01-20_

### Existing Docs

#### SDK Reference (`/src/content/docs/sdk-reference/sdk/`)

| File | Path | Coverage Quality |
|------|------|------------------|
| bifrost-module.mdx | `/sdk-reference/sdk/bifrost-module.mdx` | **Good** - Comprehensive reference covering imports, decorators, context, and all SDK modules |
| ai-module.mdx | `/sdk-reference/sdk/ai-module.mdx` | **Good** - Complete API for `ai.complete()`, `ai.stream()`, `ai.get_model_info()` with types |
| config-module.mdx | `/sdk-reference/sdk/config-module.mdx` | **Good** - Full coverage of get/set/list/delete with scope parameter |
| context-api.mdx | `/sdk-reference/sdk/context-api.mdx` | **Good** - Comprehensive context proxy documentation |
| decorators.mdx | `/sdk-reference/sdk/decorators.mdx` | **Good** - Full @workflow and @data_provider reference |
| external-sdk.mdx | `/sdk-reference/sdk/external-sdk.mdx` | **Good** - External SDK installation and usage |
| integrations-module.mdx | `/sdk-reference/sdk/integrations-module.mdx` | **Good** - Full API for OAuth and integration mappings |
| knowledge-module.mdx | `/sdk-reference/sdk/knowledge-module.mdx` | **Good** - Complete store/search/delete operations |
| tables-module.mdx | `/sdk-reference/sdk/tables-module.mdx` | **Good** - Full CRUD operations and filter operators |

#### Core Concepts (`/src/content/docs/core-concepts/`)

| File | Path | Coverage Quality |
|------|------|------------------|
| workflows.mdx | `/core-concepts/workflows.mdx` | **Good** - Explains workflow concepts, lifecycle, execution modes |

#### How-To Guides (`/src/content/docs/how-to-guides/workflows/`)

| File | Path | Coverage Quality |
|------|------|------------------|
| writing-workflows.mdx | `/how-to-guides/workflows/writing-workflows.mdx` | **Good** - Basic structure, decorators, SDK usage, logging |
| using-decorators.mdx | `/how-to-guides/workflows/using-decorators.mdx` | **Good** - Advanced decorator patterns |
| scheduled-workflows.mdx | `/how-to-guides/workflows/scheduled-workflows.mdx` | **Good** - Cron scheduling |
| http-endpoints.mdx | `/how-to-guides/workflows/http-endpoints.mdx` | **Good** - HTTP endpoint configuration |
| ai-tools.mdx | `/how-to-guides/workflows/ai-tools.mdx` | **Good** - is_tool and tool_description usage |
| error-handling.mdx | `/how-to-guides/workflows/error-handling.mdx` | **Good** - Exception handling patterns |

### Gaps Identified

#### 1. Missing `files` Module Documentation (HIGH PRIORITY)
**Location**: No dedicated file exists for `files` module in `/sdk-reference/sdk/`

The codebase shows significant file operations functionality that lacks dedicated documentation:
- `files.read()`, `files.read_bytes()` - Read text/binary files
- `files.write()`, `files.write_bytes()` - Write text/binary files
- `files.list()` - List directory contents
- `files.delete()` - Delete files
- `files.exists()` - Check file existence
- **Base64 binary support** (`as_base64` parameter) - Not documented anywhere
- **File locations** (workspace, temp, uploads) - Only briefly mentioned in bifrost-module.mdx
- **Mode parameter** (cloud vs local) - Partially documented

The `bifrost-module.mdx` has a basic `files` section but it uses incorrect function signatures (e.g., `files.read_bytes()` vs the actual implementation).

#### 2. Missing `@tool` Decorator Documentation (MEDIUM PRIORITY)
**Codebase**: Shows `@tool` decorator as shorthand for `@workflow(is_tool=True, tool_description="...")`
**Docs**: Only document `is_tool` and `tool_description` on `@workflow`, not the `@tool` shorthand

#### 3. Execution Engine Details Undocumented (LOW PRIORITY - Internal)
**Codebase features not documented**:
- Variable capture via `sys.settrace()` for debugging
- Redis PubSub log streaming (`execution:{id}:logs` channel)
- Unified execution path for workflows and inline scripts
- Redis-cached workflow metadata (5-min TTL)

These are internal details but could benefit advanced users/platform developers.

#### 4. SDK Generator Not Documented (LOW PRIORITY - Internal)
**Codebase**: `SDKGenerator` class generates Python SDKs from OpenAPI specs
**Docs**: No documentation exists for this feature

#### 5. Incorrect/Outdated Information

**In `how-to-guides/workflows/writing-workflows.mdx`**:
- Shows `oauth.get()` but the actual SDK uses `integrations.get()` for OAuth access
- File operations shown as synchronous but they are async in the actual SDK
- Missing `await` on file operations example

**In `how-to-guides/workflows/error-handling.mdx`**:
- Shows `oauth.get()` but should be `integrations.get()`

**In `core-concepts/workflows.mdx`**:
- Example shows `context` as function parameter instead of using the context proxy pattern

#### 6. Missing Workflow API Endpoints Documentation
The codebase shows extensive API endpoints not fully documented:
- `POST /api/workflows/code/execute` - Execute inline code (MCP)
- `POST /api/workflows/{id}/test` - Test workflow with sample input
- `GET /api/execute/{key}` - Execute by global key

#### 7. ROI Tracking Documentation Incomplete
**Codebase**: `time_saved` and `value` parameters captured for ROI reporting
**Docs**: Mentioned in decorators.mdx but no explanation of how ROI data is used/viewed

#### 8. `workflows` and `executions` SDK Modules Underdocumented
The `bifrost-module.mdx` briefly mentions these but no dedicated reference pages exist:
- `workflows.list()` - List all workflows
- `workflows.get()` - Get execution details
- `executions.list()` - List executions with filtering
- `executions.get()` - Get execution details

### Recommended Actions

#### Immediate (HIGH PRIORITY)

1. **Create `/sdk-reference/sdk/files-module.mdx`**
   - Document all file operations: `read()`, `read_bytes()`, `write()`, `write_bytes()`, `list()`, `delete()`, `exists()`
   - Document `FileLocation` enum: workspace, temp, uploads
   - Document `mode` parameter: cloud vs local
   - Document base64 binary support with examples
   - Include working code examples for each operation

2. **Fix incorrect `oauth.get()` references**
   - Update `writing-workflows.mdx` to use `integrations.get()`
   - Update `error-handling.mdx` to use `integrations.get()`
   - Ensure file operations are shown as async with `await`

3. **Update `core-concepts/workflows.mdx`**
   - Replace old context-as-parameter pattern with context proxy pattern
   - Match the SDK reference documentation

#### Short-term (MEDIUM PRIORITY)

4. **Add `@tool` decorator documentation**
   - Add to `decorators.mdx` as shorthand for `@workflow(is_tool=True)`
   - Include example showing equivalence

5. **Create dedicated pages for minor SDK modules**
   - `/sdk-reference/sdk/workflows-module.mdx` - Workflow metadata and execution
   - `/sdk-reference/sdk/executions-module.mdx` - Execution history queries

6. **Expand ROI tracking documentation**
   - Explain how `time_saved` and `value` are captured
   - Document where ROI data appears in the UI
   - Add examples of ROI tracking workflows

#### Long-term (LOW PRIORITY)

7. **Add platform developer documentation**
   - Execution engine architecture
   - Redis caching strategy
   - Log streaming via PubSub
   - Variable capture mechanism

8. **Document SDK Generator**
   - How to generate SDKs from OpenAPI specs
   - Supported authentication types
   - Output structure

9. **Add Workflow API reference**
   - Document REST endpoints for workflow management
   - Include inline code execution endpoint for MCP users
