---
title: Workflow Engine Troubleshooting
description: Diagnose and fix workflow execution and discovery issues
---

# Workflow Engine Troubleshooting

The workflow engine executes your workflows in an isolated environment. This guide helps you diagnose and fix workflow-specific issues.

## Workflow Not Discovered

**Symptom**: Workflow doesn't appear in UI or API `/api/discovery` list

### Check 1: File Location

Workflows must be in discoverable directories:

```
✅ /home/workflows/my_workflow.py
✅ /platform/examples/my_workflow.py
✅ /home/data_providers/my_provider.py

❌ /workspace/my_workflow.py (wrong location)
❌ /other/my_workflow.py (not scanned)
```

### Check 2: Filename Rules

```
✅ my_workflow.py              (discovered)
✅ user_onboarding.py          (discovered)

❌ _my_workflow.py             (ignored, starts with _)
❌ __pycache__.py              (ignored)
❌ my_workflow (no .py)        (ignored)
```

Files starting with underscore are skipped to avoid discovering helper/utility files.

### Check 3: Decorator Applied

```python
# ✅ Correct
from bifrost import workflow

@workflow(name="test", description="Test workflow")
async def test(context):
    pass

# ❌ Wrong: No decorator
async def test(context):
    pass

# ❌ Wrong: Decorator commented out
# @workflow(name="test", description="Test")
async def test(context):
    pass

# ❌ Wrong: Wrong import
from shared.decorators import workflow  # Import restriction violation!
```

### Check 4: Check Startup Logs

When the Function App starts or deploys, it logs discovery:

```bash
# Get logs
az functionapp log tail --resource-group <rg> --name <name>

# Look for:
✅ "Discovered: workspace.workflows.my_workflow"
❌ "Failed to import: workspace.workflows.broken_file"
❌ "Import error in workspace.workflows.my_workflow"
```

**If import fails:**
1. Check Python syntax errors
2. Look at full error message for import issues
3. Verify imports are allowed by the [import restrictions](/docs/concepts/discovery-system#import-restrictions)

### Check 5: Verify Decorator Syntax

```python
# ✅ Correct
@workflow(
    name="create_user",        # Unique identifier
    description="Create user", # Human-readable
    category="users"           # Optional
)
async def create_user(context):
    pass

# ❌ Missing required fields
@workflow(name="create_user")  # Missing description
async def create_user(context):
    pass

# ❌ Wrong field types
@workflow(
    name=123,                  # Should be string
    description="Create user"
)
async def create_user(context):
    pass
```

## Workflow Parameters Not Showing

**Symptom**: Workflow appears but parameters are missing from form

### Check 1: @param Decorator Order

Parameters must be stacked below `@workflow`:

```python
# ✅ Correct order (workflow first, then params)
@workflow(name="test")
@param("email", type="email", required=True)
@param("name", type="string", required=True)
async def test(context, email: str, name: str):
    pass

# ❌ Wrong: params before workflow
@param("email", type="email", required=True)
@workflow(name="test")
async def test(context, email: str):
    pass
```

The order matters because decorators execute bottom-up in Python, and `@workflow` collects the parameters attached to the function.

### Check 2: Parameter Name Matches Argument

```python
# ✅ Correct: param name matches function argument
@param("email", type="email")
async def create_user(context, email: str):
    pass

# ❌ Wrong: param name doesn't match argument
@param("recipient_email", type="email")  # Called "recipient_email"
async def create_user(context, email: str):  # But arg is "email"
    pass

# ❌ Wrong: parameter in decorator but not in function
@param("phone", type="string")
async def create_user(context, email: str):  # "phone" parameter not in args
    pass
```

### Check 3: Parameter Configuration

```python
# ✅ Minimal valid param
@param("email", type="email")

# ✅ Full featured param
@param(
    name="email",                              # Matches function arg
    type="email",                              # Valid type
    label="Email Address",                     # UI label
    required=True,                             # Is required?
    help_text="User's email",                  # Help text
    validation={"pattern": "..."},             # Custom validation
    data_provider="get_email_domains",         # Dropdown provider
    default_value="user@example.com"           # Default value
)

# ❌ Invalid: Unknown field
@param("email", type="email", unknown_field="value")

# ❌ Invalid: Invalid type
@param("email", type="unknown_type")  # Should be: email, string, int, etc.
```

**Valid parameter types:**

```
string   → Text input
int      → Integer number
float    → Decimal number
bool     → True/False checkbox
email    → Email address with validation
json     → JSON object
list     → Array of values
```

### Check 4: Data Provider Reference

```python
# If using data_provider, it must exist and be discoverable

# ✅ Correct: Data provider exists
@param("license", data_provider="get_available_licenses")

# ❌ Wrong: Data provider doesn't exist
@param("license", data_provider="invalid_provider_name")

# ❌ Wrong: Typo in provider name
@param("license", data_provider="get_availble_licenses")  # "availble" typo
```

## Workflow Execution Fails

**Symptom**: Workflow executes but returns error

### Check 1: Look at Execution Logs

Each execution has detailed logs:

```
UI: Workflows → [Select workflow] → Execution History → [Click execution]
    Shows: logs, checkpoints, variables, errors
```

**Log levels:**

```
INFO     → Normal operation messages
WARNING  → Something unexpected but recoverable
ERROR    → Operation failed
```

### Check 2: Check Error Message

The error message tells you what went wrong:

```
❌ "NameError: name 'context' is not defined"
   Fix: Function must accept context as first parameter

❌ "TypeError: missing required argument 'email'"
   Fix: Form didn't pass email parameter

❌ "ImportError: cannot import name 'msgraph'"
   Fix: Integration not found, must use context.get_integration()

❌ "asyncio.TimeoutError"
   Fix: Workflow took longer than timeout (increase timeout_seconds)

❌ "Exception: User does not have E5 license"
   Fix: Your workflow logic raised this error (check your code)
```

### Check 3: Verify Function Signature

```python
# ✅ Correct: Must accept context
async def my_workflow(context: ExecutionContext):
    pass

# ✅ Correct: With parameters
async def my_workflow(context: ExecutionContext, email: str, name: str):
    pass

# ❌ Wrong: Missing context
async def my_workflow(email: str):
    pass

# ❌ Wrong: Not async
def my_workflow(context):  # Should be async
    pass
```

### Check 4: Check for Unhandled Exceptions

```python
# ❌ Will crash the workflow
async def my_workflow(context):
    result = await some_api_call()
    # If some_api_call fails, exception bubbles up
    return result.data  # AttributeError if result is None

# ✅ Better: Handle exceptions
async def my_workflow(context):
    try:
        result = await some_api_call()
        if result is None:
            context.log("error", "API returned None")
            return {"error": "API failed"}
        return result.data
    except Exception as e:
        context.log("error", f"API call failed: {str(e)}")
        return {"error": str(e)}
```

## Import Errors in Workflows

**Symptom**: "ImportError: cannot import..." when executing workflow

### Check 1: Import Restrictions

Different directories have different allowed imports:

**In `/home` code (user workflows):**

```python
# ✅ Allowed
from bifrost import workflow, param, ExecutionContext
import requests
import aiohttp
from datetime import datetime

# ❌ Not allowed
from shared.registry import get_registry          # Internal
from functions.http.discovery import get_discovery  # HTTP layer
```

**In `/platform` code (examples, integrations):**

```python
# ✅ Allowed
from bifrost import workflow, param
from shared.handlers import some_handler  # Can access shared/*
import requests

# ❌ Not allowed
from functions.http.discovery import get_discovery  # HTTP layer
```

### Check 2: Verify Module Exists

```python
# ✅ Correct: bifrost SDK is public API
from bifrost import (
    workflow,
    param,
    ExecutionContext,
    get_registry,  # Available in public API
)

# ❌ Wrong: Not in public API
from bifrost.internal import something_internal

# ❌ Wrong: Module doesn't exist
from bifrost.nonexistent import something
```

### Check 3: Third-Party Packages

Third-party packages are available if in `requirements.txt`:

```
# requirements.txt (in bifrost-api)
requests==2.31.0
aiohttp==3.9.0
azure-storage-blob==12.18.0
pydantic==2.5.0
```

```python
# ✅ Available
import requests
import aiohttp
from azure.storage.blob import BlobServiceClient

# ❌ Not available (not in requirements.txt)
import pandas  # Not installed
```

## Timeout Issues

**Symptom**: "Execution timeout" or "asyncio.TimeoutError"

### Understanding Timeouts

Each workflow has a maximum execution time:

```python
@workflow(
    name="my_workflow",
    timeout_seconds=300  # Default: 5 minutes
)
async def my_workflow(context):
    pass
```

If the workflow takes longer than `timeout_seconds`, it's killed.

### Solution 1: Increase Timeout

```python
# For longer operations
@workflow(
    name="bulk_import",
    timeout_seconds=1800,  # 30 minutes
    execution_mode="async"  # Run in background
)
async def bulk_import(context):
    # Has up to 30 minutes
    pass
```

### Solution 2: Optimize Workflow

```python
# ❌ Slow: One user at a time
async def import_users(context):
    for user in users:
        await create_user(user)  # Wait for each one

# ✅ Fast: Parallel operations (Python 3.10+)
async def import_users(context):
    tasks = [create_user(user) for user in users]
    await asyncio.gather(*tasks)  # Do them all at once
```

### Solution 3: Use Async Mode

```python
# ✅ Good for long workflows
@workflow(
    execution_mode="async",  # Runs in background
    timeout_seconds=3600     # 1 hour
)
async def import_all_users(context):
    pass

# ❌ Risky: Sync mode has hard limits
@workflow(
    execution_mode="sync",   # Blocks user's HTTP request
    timeout_seconds=300      # Azure Functions hard timeout
)
async def import_all_users(context):
    pass
```

## Context Issues

**Symptom**: "context is None" or "Organization not found"

### Check 1: ExecutionContext Access

```python
# ✅ Correct: context provided by framework
async def my_workflow(context: ExecutionContext):
    org_id = context.org_id      # "acme-corp"
    org_name = context.org_name  # "Acme Corporation"
    email = context.executed_by_email  # "user@example.com"

# ❌ Wrong: Trying to access context that's None
async def my_workflow(context):
    if context is None:  # This shouldn't happen
        context.log("error", "Context is None")
```

### Check 2: Organization Scope

Some operations require organization context:

```python
# ✅ Correct: Workflow requires org
@workflow(
    name="create_user",
    requires_org=True  # Must have organization context
)
async def create_user(context: ExecutionContext):
    await context.get_config("api_key")  # Uses org context

# ⚠️ Risky: Global workflow
@workflow(
    name="system_health",
    requires_org=False  # Can run globally
)
async def system_health(context):
    # context might be None or have no org_id
    pass
```

### Check 3: Configuration Access

```python
# ✅ Correct: With default value
value = context.get_config("api_key", default="https://api.example.com")

# ✅ Correct: With error handling
try:
    api_key = context.get_config("api_key")
except KeyError:
    context.log("error", "api_key not configured")
    return {"error": "Configuration missing"}

# ❌ Wrong: No fallback
api_key = context.get_config("api_key")  # Raises if not found
```

## Performance Issues

### Slow Workflow Execution

**Symptom**: Workflow takes much longer than expected

#### Check 1: Look at Logs

```python
@workflow(name="test")
async def test(context):
    # Add timing logs
    context.log("info", "Starting step 1")
    result1 = await step1()

    context.log("info", "Starting step 2")
    result2 = await step2()

    # Look in execution log to see timing:
    # "Starting step 1" at T+0s
    # "Starting step 2" at T+5s  <- Step 1 took 5 seconds
```

#### Check 2: Look for API Delays

```python
# ❌ Slow: Sequential API calls
for user in users:
    await create_m365_user(user)      # Wait 1-2s
    await assign_license(user)        # Wait 1-2s
    # = 3-4s per user
```

```python
# ✅ Fast: Parallel operations
async def create_and_assign(user):
    user_result = await create_m365_user(user)
    return await assign_license(user_result)

tasks = [create_and_assign(user) for user in users]
await asyncio.gather(*tasks)
# All 100 users in ~2-3s instead of 300-400s
```

#### Check 3: Look for Network Delays

```
Slow workflow usually means:
- Waiting for external API calls
- Network latency
- Rate limiting (retry delays)

Solution:
- Use asyncio.gather() for parallel requests
- Add retry logic with backoff
- Cache frequently accessed data
```

## Data Provider Issues

**Symptom**: Dropdown in form is empty or showing error

### Check 1: Data Provider Exists

```bash
# Check if data provider is discoverable
curl http://localhost:7071/api/data-providers

# Should include:
{
  "dataProviders": [
    {"name": "get_available_licenses", ...},
    {"name": "get_departments", ...}
  ]
}
```

### Check 2: Data Provider Returns Data

```python
# ✅ Correct format
@data_provider(name="get_licenses")
async def get_licenses(context):
    return [
        {"label": "E3", "value": "SPE_E3", "metadata": {}},
        {"label": "E5", "value": "SPE_E5", "metadata": {}}
    ]

# ❌ Wrong: Not list of dicts
@data_provider(name="get_licenses")
async def get_licenses(context):
    return ["E3", "E5"]  # Missing label/value structure

# ❌ Wrong: Returns None
@data_provider(name="get_licenses")
async def get_licenses(context):
    # Missing return statement
    pass
```

### Check 3: Caching

Data providers are cached:

```python
@data_provider(
    name="get_licenses",
    cache_ttl_seconds=300  # Cached for 5 minutes
)
async def get_licenses(context):
    pass

# If data doesn't update:
# - Wait 5 minutes for cache to expire
# - Or reduce cache_ttl_seconds to 0 for testing
```

## Hot Reload Issues

**Symptom**: Changes to workflow file don't appear after saving

### Issue 1: File Not Reloaded During Development

During local development with `func start`:

```
Expected workflow reload:
  1. Edit workflow file
  2. Save file
  3. Reload page
  4. New version appears

If not working:
  - Restart `func start` (stops function app, starts fresh)
  - Check file is actually saved
  - Verify no syntax errors preventing import
```

### Issue 2: Production Deployment

In production, changes require redeployment:

```bash
# After pushing code changes:
1. Commit to Git
2. GitHub Actions CI/CD triggers
3. Builds and deploys new version
4. Function App restarts with new code
5. Discovery runs and picks up changes
```

Discovery happens at startup, not continuously.

## File Operations Issues

**Symptom**: "Cannot read/write files" or "Permission denied"

### Understanding File Paths

Bifrost provides isolated file systems:

```python
# ✅ Correct: Use paths provided by context
file_path = context.get_temp_file_path("my_file.txt")
# Returns something like: /tmp/org-12345/workflow-abc123/my_file.txt

# ✅ Correct: Use workspace path (if configured)
file_path = context.get_workspace_file_path("uploads/document.pdf")

# ❌ Wrong: Direct filesystem access
with open("/etc/sensitive_file") as f:  # Denied by import restrictor
    pass

# ❌ Wrong: Hardcoded paths
with open("/tmp/my_file.txt") as f:  # May not exist or have permissions
    pass
```

### Check 1: File Size Limits

```
Temp directory (/tmp): Limited by Azure Functions (usually 512 MB)
Workspace (/workspace): Limited by Azure Files quota (depends on config)
```

```python
# Careful with large files
file_size_mb = 100  # 100 MB
if file_size_mb > 500:
    context.log("error", "File too large for temp storage")
    return {"error": "File too large"}
```

## Quick Reference

| Issue | Most Likely Cause | Fix |
|-------|---|---|
| Workflow not discovered | Wrong location or no decorator | Check file location and decorator |
| Parameters missing | Decorator order wrong or name mismatch | Check @param order, verify names match |
| Import error | Not using public API | Use bifrost.* instead of shared.* |
| Timeout | Workflow too long | Increase timeout or use async mode |
| Context None | Workflow doesn't require org | Add `requires_org=True` |
| Slow execution | Sequential operations | Use asyncio.gather() for parallel work |
| Data provider empty | Wrong format or exception | Check return format and logs |
| File access denied | Using restricted paths | Use context.get_temp_file_path() |

## Getting Help

- **Execution Logs**: Workflows page → Execution History → [Click execution]
- **Discovery Logs**: Azure Portal → Function App → Log Stream
- **Debugging**: Add `context.log()` statements throughout workflow
- **Check Status**: `curl http://your-bifrost.com/api/health`

## Related Topics

- **[Discovery System](/docs/concepts/discovery-system)** - How discovery works
- **[Workflow Development](/docs/guides/creating-workflows)** - How to create workflows
- **[Local Development](/docs/guides/local-development)** - Debug locally
- **[Azure Functions Troubleshooting](/docs/troubleshooting/azure-functions)** - Infrastructure issues
