---
title: Discovery System
description: How Bifrost automatically discovers and registers workflows and data providers
---

# Discovery System

Bifrost's discovery system is the mechanism that automatically finds, registers, and makes your workflows and data providers available throughout the platform. It runs when the Azure Functions app starts and enables zero-configuration workflow registration.

## Why Discovery Matters

Without automatic discovery, you'd need to:
- Manually register each workflow in a central registry
- Maintain configuration files listing all your functions
- Redeploy the application to add new workflows
- Track which functions are available

Instead, Bifrost scans your workspace, discovers Python files with decorators, automatically registers them, and makes them available. Just write the code—the platform handles the rest.

## How Discovery Works

The discovery process happens in five stages:

### Stage 1: Workspace Scanning

When the Azure Functions app starts, it scans two directories:

- **`/platform`**: Platform-provided workflows and data providers (built-in examples)
- **`/home`**: User-created workflows and data providers (your organization's custom code)

The scanner:
- Recursively searches for `.py` files
- Ignores files starting with `_` (like `__init__.py`, `_helpers.py`)
- Imports each file as a Python module
- No `__init__.py` files are required

**Example: File discovery**

```
File: /home/workflows/user_onboarding.py
Module name: workspace.user_onboarding

File: /platform/integrations/msgraph_client.py
Module name: workspace.integrations.msgraph_client

File: /home/data_providers/licenses.py
Module name: workspace.data_providers.licenses
```

### Stage 2: Decorator Execution

When each module is imported, Python executes all the code at module level. Your decorators run immediately:

```python
# When this file is imported, the @workflow decorator runs
@workflow(
    name="create_user",
    description="Create new user in M365"
)
async def create_user(context, email: str):
    pass
```

The `@workflow` decorator:
1. Collects metadata (name, description, parameters, etc.)
2. Creates a `WorkflowMetadata` dataclass
3. Registers it in the global `WorkflowRegistry`
4. Returns the original function unmodified

### Stage 3: Registry Storage

All discovered workflows and data providers are stored in a thread-safe singleton registry:

```
WorkflowRegistry (Singleton)
├── Workflows
│   ├── "create_user" → WorkflowMetadata(...)
│   ├── "assign_license" → WorkflowMetadata(...)
│   └── "audit_licenses" → WorkflowMetadata(...)
├── Data Providers
│   ├── "get_available_licenses" → DataProviderMetadata(...)
│   ├── "get_departments" → DataProviderMetadata(...)
│   └── "get_users" → DataProviderMetadata(...)
└── Thread Lock (for concurrent registration)
```

**Why a registry?**

The registry provides:
- **Central source of truth**: Single place to query what's available
- **Thread safety**: Multiple imports can happen concurrently during startup
- **Performance**: Fast lookups by name
- **Testability**: Can be mocked in tests

### Stage 4: API Endpoints Ready

Once discovery completes, these API endpoints become available:

```
GET /api/discovery
  ↓ Returns all discovered workflows and data providers
  ↓
{
  "workflows": [
    {
      "name": "create_user",
      "description": "Create new user in M365",
      "category": "user_management",
      "parameters": [
        {"name": "email", "type": "email", "required": true}
      ]
    }
  ],
  "dataProviders": [
    {
      "name": "get_available_licenses",
      "description": "List available M365 licenses",
      "cacheSeconds": 300
    }
  ]
}
```

### Stage 5: Client Consumption

The frontend uses discovery data to:

1. **Display available workflows** in the Workflows list
2. **Generate forms** dynamically from workflow parameters
3. **Populate data provider dropdowns** with real data
4. **Validate form submissions** against registered parameters
5. **Enable code completion** in the form builder

## What Gets Discovered

### Workflows

Functions decorated with `@workflow`:

```python
from bifrost import workflow, param

@workflow(
    name="send_email",
    description="Send email notification",
    category="communications"
)
@param("recipient", type="email", required=True)
@param("subject", type="string", required=True)
@param("body", type="string", required=True)
async def send_email(context, recipient: str, subject: str, body: str):
    return {"sent": True, "recipient": recipient}
```

**Available in:**
- Workflows page (UI)
- Form builder (as target for form execution)
- Direct API execution (`POST /api/workflows/send_email`)

### Data Providers

Functions decorated with `@data_provider`:

```python
from bifrost import data_provider, param

@data_provider(
    name="get_available_licenses",
    description="Return available M365 licenses",
    category="m365",
    cache_ttl_seconds=300
)
async def get_available_licenses(context):
    return [
        {"label": "Microsoft 365 E3", "value": "SPE_E3"},
        {"label": "Microsoft 365 E5", "value": "SPE_E5"}
    ]
```

**Available in:**
- Form field dropdowns (as `dataProvider="get_available_licenses"`)
- Direct API queries (`POST /api/data-providers/get_available_licenses`)

### Parameters

Parameters are discovered from `@param` decorators attached to workflows and data providers:

```python
@workflow(name="example")
@param("first_name", type="string", label="First Name", required=True)
@param("email", type="email", label="Email", required=True)
async def example(context, first_name: str, email: str):
    pass
```

Parameters define:
- Input validation (type, required, patterns)
- UI rendering (label, help text, field type)
- Default values
- Conditional visibility

## Import Restrictions

The discovery system enforces import restrictions for security:

### `/home` code (user workflows)

✅ **Can import**:
- `bifrost.*` - Public SDK only
- Standard library modules
- Third-party packages (requests, aiohttp, etc.)

❌ **Cannot import**:
- `shared.*` - Internal platform code
- `functions.*` - HTTP handler code
- `azure.*` - Azure SDK directly

**Why?** User code should only use the public API to prevent access to internal systems.

### `/platform` code (platform workflows, examples)

✅ **Can import**:
- `bifrost.*` - Public SDK
- `shared.*` - Internal handlers and utilities
- Standard library and third-party packages

❌ **Cannot import**:
- `functions.*` - HTTP layer

**Why?** Platform code can access internal utilities but shouldn't touch HTTP handlers.

**Example: Import enforcement**

```python
# ❌ This will fail (in /home code)
from shared.registry import get_registry

# ✅ This works (in /home code)
from bifrost import get_registry
```

## Hot Reload

The discovery system is designed for rapid development:

1. **No restart required for new files**: Add a new `.py` file to `/home` or `/platform`
2. **Automatic pickup**: On next function execution, new file is discovered
3. **No `__init__.py` files**: Drop your file, it's automatically found

**How it works**:
- Workspace paths are determined at runtime
- Files are scanned dynamically
- New files in directories are picked up automatically

This makes local development fast: save → test → repeat.

## Discovery Metadata

Each discovered item includes comprehensive metadata:

### Workflow Metadata

```python
{
    "name": "create_user",                      # Unique identifier
    "description": "Create new user in M365",   # Human-readable
    "category": "user_management",              # For organization
    "tags": ["m365", "user"],                   # For filtering
    "executionMode": "sync",                    # Execution type
    "timeoutSeconds": 300,                      # Timeout
    "parameters": [                             # Input parameters
        {
            "name": "email",
            "type": "email",
            "label": "Email Address",
            "required": true,
            "validation": {"pattern": "..."}
        }
    ],
    "source": "home"                            # Where it came from
}
```

### Data Provider Metadata

```python
{
    "name": "get_available_licenses",           # Unique identifier
    "description": "Return available licenses", # Human-readable
    "category": "m365",                         # For organization
    "cacheTtlSeconds": 300,                     # Cache duration
    "parameters": [                             # Input parameters
        {
            "name": "filter_available",
            "type": "bool",
            "label": "Only Available",
            "required": false,
            "defaultValue": true
        }
    ]
}
```

## Discovery in Action: Complete Example

### Step 1: You create a file

Create `/home/workflows/sync_users.py`:

```python
from bifrost import workflow, param, ExecutionContext

@workflow(
    name="sync_users_from_halo",
    description="Sync users from HaloPSA to Microsoft 365",
    category="user_management"
)
@param("department", type="string", label="Department", required=True)
@param("limit", type="int", label="Max Users", default_value=50)
async def sync_users_from_halo(context: ExecutionContext, department: str, limit: int = 50):
    context.log("info", f"Starting sync for {department}")
    return {"users_synced": 12}
```

### Step 2: Function app starts (or next request)

```
Discovery process:
1. Scan /home directory
2. Find sync_users.py
3. Import as workspace.sync_users
4. Execute @workflow decorator
5. Create WorkflowMetadata
6. Register in WorkflowRegistry
7. Available!
```

### Step 3: Frontend fetches discovery

```bash
GET /api/discovery
```

Response includes:

```json
{
  "workflows": [
    {
      "name": "sync_users_from_halo",
      "description": "Sync users from HaloPSA to Microsoft 365",
      "category": "user_management",
      "parameters": [
        {"name": "department", "type": "string", "required": true},
        {"name": "limit", "type": "int", "required": false, "defaultValue": 50}
      ]
    }
  ]
}
```

### Step 4: User executes workflow

Frontend calls:

```bash
POST /api/workflows/sync_users_from_halo
Content-Type: application/json

{
  "department": "Engineering",
  "limit": 100
}
```

## Performance Considerations

### Discovery Startup Time

- **Small workspace** (< 50 files): < 500ms
- **Medium workspace** (50-200 files): 500ms - 2s
- **Large workspace** (> 200 files): 2-5s

Optimization tips:
- Keep workflow files focused (one concept per file)
- Avoid expensive imports at module level
- Use lazy imports for heavy dependencies

### Registry Lookup Performance

All lookups are O(1) dictionary operations:

```python
# Fast O(1) lookup
workflow = registry.get_workflow("create_user")
provider = registry.get_data_provider("get_licenses")
```

This means discovery doesn't impact runtime performance.

## Troubleshooting Discovery

### Workflow not appearing in list

**Check 1: File location**
```bash
# Must be in /home or /platform
ls /home/workflows/my_workflow.py      # ✅ Found
ls /home/my_workflow.py               # ✅ Also found
ls /other/my_workflow.py              # ❌ Not scanned
```

**Check 2: Filename doesn't start with underscore**
```bash
my_workflow.py                        # ✅ Discovered
_helpers.py                           # ❌ Ignored
__init__.py                           # ❌ Ignored
```

**Check 3: Decorator is correct**
```python
from bifrost import workflow           # ✅ Correct
from shared.decorators import workflow # ❌ Wrong (import restriction)

@workflow(name="test")                 # ✅ Applied
# @workflow commented out?             # ❌ Not applied
```

**Check 4: Look at startup logs**
```
✓ Discovered: workspace.workflows.my_workflow
✗ Failed to import: workspace.workflows.broken_file
```

### Parameters not showing in form

**Check 1: @param comes AFTER @workflow**
```python
@workflow(name="test")               # First
@param("field1", type="string")      # After
async def test(context, field1):
    pass
```

**Check 2: Parameter name matches function argument**
```python
@param("email", ...)                 # Must match...
async def create_user(context, email):  # ...function argument
    pass
```

**Check 3: Data provider parameter validation**
```python
@param("license", data_provider="get_licenses")
# Data provider "get_licenses" must exist and be discoverable
```

### Import error during discovery

**Error: Cannot import from shared**
```python
from shared.registry import get_registry  # ❌ Fails in /home code

# Instead, use public API
from bifrost import get_registry  # ✅ Works
```

## Related Topics

- **[Decorators and Parameters](/docs/concepts/decorators)** - How to use @workflow, @param, and @data_provider
- **[Forms](/docs/concepts/forms)** - How forms use discovery data
- **[Local Development](/docs/guides/local-development)** - Running discovery locally
