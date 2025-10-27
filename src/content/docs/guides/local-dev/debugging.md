---
title: Debug Workflows
description: Guide for debugging workflows locally using VS Code, logging, and inspection tools
---

# Debug Workflows

This guide covers debugging workflows locally using the VS Code debugger, logging, and inspection techniques.

## Table of Contents

- [Quick Start](#quick-start)
- [VS Code Debugger Setup](#vs-code-debugger-setup)
- [Logging & Inspection](#logging--inspection)
- [Debugging Techniques](#debugging-techniques)
- [Common Debugging Scenarios](#common-debugging-scenarios)
- [Performance Debugging](#performance-debugging)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Without Dev Container

If you're not using dev containers, you can still debug by starting the Functions runtime manually:

```bash
# Terminal 1: Start Azurite
azurite --blobPort 10000 --queuePort 10001 --tablePort 10002

# Terminal 2: Start Functions with debugging
export DEBUGPY_ENABLED=1
export DEBUGPY_PORT=5678
func start

# Terminal 3: Set breakpoints and run curl commands
curl -X POST \
  -H "x-functions-key: test" \
  -H "X-Organization-Id: test-org-active" \
  http://localhost:7071/api/health
```

Then attach your debugger to `localhost:5678`.

### With Dev Container (Easiest)

The dev container has debugging pre-configured:

1. **Open the repository in VS Code** with dev container
2. **Start the Functions runtime:**
   ```bash
   func start
   ```
3. **Set a breakpoint** in your Python code (click in the left margin)
4. **Press F5** or go to Run → Start Debugging
5. **Trigger the function** with curl or Postman
6. **Debugger pauses** at your breakpoint

## VS Code Debugger Setup

### Configuration (Dev Container)

The `.devcontainer/devcontainer.json` includes VS Code extensions and settings:

```json
{
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "ms-azuretools.vscode-azurefunctions"
      ]
    }
  }
}
```

The `func start` command automatically enables debugging on port 5678.

### Manual Debugger Setup

If not using dev container, create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Attach to Azure Functions",
      "type": "python",
      "request": "attach",
      "connect": {
        "host": "localhost",
        "port": 5678
      },
      "pathMappings": [
        {
          "localRoot": "${workspaceFolder}",
          "remoteRoot": "/workspace"
        }
      ],
      "justMyCode": true
    }
  ]
}
```

### Starting a Debug Session

1. **Open a Python file** in VS Code
2. **Set a breakpoint** (click in left margin, red dot appears)
3. **Start the Functions runtime:**
   ```bash
   func start
   ```
4. **Attach debugger** (F5 or Run → Start Debugging)
5. **Expected message:** "Debugger attached"
6. **Trigger the function** (curl, Postman, or API call)
7. **Debugger pauses** at the breakpoint

### Debugging Controls

Once stopped at a breakpoint:

| Key              | Action                                    |
| ---------------- | ----------------------------------------- |
| **F10**          | Step over (next line in current function) |
| **F11**          | Step into (enter called functions)        |
| **Shift+F11**    | Step out (exit current function)          |
| **F5**           | Continue execution                        |
| **Ctrl+Shift+D** | Open Debug view                           |

### Inspecting Variables

While paused at a breakpoint:

- **Hover over variables** - See their current value
- **Debug Console** - Evaluate expressions:
  ```python
  # Type in Debug Console:
  context.org_id
  request.dict()
  my_variable + 1
  ```
- **Watch panel** - Add expressions to monitor:
  1. Right-click variable → "Add to Watch"
  2. Or type expression in Watch panel

## Logging & Inspection

### Using Print Statements

The simplest debugging approach:

```python
# functions/http/endpoints.py
from functions.shared.openapi_decorators import openapi_handler

@openapi_handler(...)
async def execute_workflow(req: func.HttpRequest) -> func.HttpResponse:
    org_id = req.headers.get("X-Organization-Id")

    print(f"DEBUG: org_id = {org_id}")  # Visible in logs
    print(f"DEBUG: request body = {req.get_json()}")

    # ... rest of function
    return func.HttpResponse("Success")
```

Print output appears in the terminal where `func start` is running:

```
[2024-10-24T10:30:45.123Z] DEBUG: org_id = test-org-active
[2024-10-24T10:30:45.124Z] DEBUG: request body = {'name': 'Alice'}
```

### Structured Logging

For production-like logging, use Python's logging module:

```python
import logging
from functions.shared.openapi_decorators import openapi_handler

logger = logging.getLogger(__name__)

@openapi_handler(...)
async def execute_workflow(req: func.HttpRequest) -> func.HttpResponse:
    org_id = req.headers.get("X-Organization-Id")

    logger.info(f"Executing workflow for org={org_id}")
    logger.debug(f"Request body: {req.get_json()}")
    logger.warning(f"Deprecation notice: old parameter used")
    logger.error(f"Failed to access storage: {error}")

    return func.HttpResponse("Success")
```

### Checking Azure Functions Logs

Logs from the Functions runtime:

```bash
# Stream logs from running Functions instance
az functionapp log tail --name <function-app-name> --resource-group <rg>

# View Application Insights logs
az monitor app-insights query --app <app-insights-name> \
  --analytics-query "traces | order by timestamp desc | take 100"
```

## Debugging Techniques

### Inspect Context Object

The `context` object contains execution information:

```python
# In any function or workflow
from functions.shared._context import get_context

async def my_function(req, context):
    # Get context information
    print(f"Organization: {context.org_id}")
    print(f"Execution ID: {context.execution_id}")
    print(f"User ID: {context.user_id}")
    print(f"Request ID: {context.request_id}")
```

### Request/Response Inspection

Inspect what was received and what will be sent:

```python
@openapi_handler(...)
async def my_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    # Inspect incoming request
    print(f"Method: {req.method}")
    print(f"Headers: {dict(req.headers)}")
    print(f"Query params: {dict(req.params)}")

    try:
        body = req.get_json()
        print(f"Body: {body}")
    except ValueError as e:
        print(f"Invalid JSON: {e}")
        return func.HttpResponse("Invalid JSON", status_code=400)

    # Process request...
    response = {"status": "success"}

    print(f"Returning: {response}")
    return func.JsonResponse(response)
```

### Inspecting Database Queries

Debug data access:

```python
from shared.repositories.organizations_repository import OrganizationsRepository

async def debug_org_lookup(org_id: str):
    repo = OrganizationsRepository()

    # Add debug logging
    print(f"Looking up org: {org_id}")
    org = await repo.get(org_id)
    print(f"Found: {org}")

    if org:
        print(f"Org properties: id={org.id}, name={org.name}")
    else:
        print(f"Org not found!")
```

### Error Stack Traces

When exceptions occur, the full stack trace is printed:

```bash
# Terminal output shows:
Traceback (most recent call last):
  File "functions/http/endpoints.py", line 42, in execute_workflow
    result = await handler.execute(org_id, workflow_name, params)
  File "shared/handlers/workflows_handler.py", line 100, in execute
    workflow_code = self.load_workflow(workflow_name)
  File "shared/handlers/workflows_handler.py", line 55, in load_workflow
    raise WorkflowNotFound(f"Workflow {workflow_name} not found")
WorkflowNotFound: Workflow hello_world not found
```

This tells you:

1. The exception type (`WorkflowNotFound`)
2. Where it occurred (file and line number)
3. The chain of function calls that led to it

### Using pdb (Python Debugger)

Drop into the Python debugger at any point:

```python
@openapi_handler(...)
async def my_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    org_id = req.headers.get("X-Organization-Id")

    # Add breakpoint
    import pdb; pdb.set_trace()

    # Execution pauses here, you can:
    # - Type commands at (Pdb) prompt
    # - View variables: p org_id
    # - Continue: c
    # - Next line: n
```

## Common Debugging Scenarios

### Workflow Not Found

**Symptom:** `WorkflowNotFound: Workflow hello_world not found`

**Debugging steps:**

```bash
# 1. Check if workflow file exists
ls workspace/examples/hello_world.py

# 2. Verify the @workflow decorator
grep -n "@workflow" workspace/examples/hello_world.py

# 3. Check if Functions runtime discovered it
curl -H "x-functions-key: test" \
     http://localhost:7071/api/registry/metadata | jq '.workflows | length'

# 4. Add debug logging
import logging
logger = logging.getLogger(__name__)
logger.debug(f"Discovered workflows: {self.get_workflow_list()}")
```

### Missing Headers

**Symptom:** `401 Unauthorized` or missing org ID

**Debugging steps:**

```bash
# Check headers are being sent
curl -v -X POST \
  -H "x-functions-key: test" \
  -H "X-Organization-Id: test-org-active" \
  http://localhost:7071/api/workflows/hello_world

# Look for "< x-functions-key:" in output

# In code, verify headers
print(f"All headers: {dict(req.headers)}")
print(f"Org ID: {req.headers.get('X-Organization-Id')}")
```

### Storage Connection Issues

**Symptom:** `Connection refused` or tables not found

**Debugging steps:**

```bash
# 1. Verify Azurite is running
curl http://localhost:10000/devstoreaccount1 && echo "OK"

# 2. Check connection string
echo $AzureWebJobsStorage

# 3. Test table access directly
python3 << 'EOF'
from azure.data.tables import TableClient
conn_str = "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;..."
client = TableClient.from_connection_string(conn_str, "organizations")
print("Connection successful")
EOF

# 4. Add logging in repository
logger.debug(f"Connection string: {conn_str}")
```

### Async/Await Issues

**Symptom:** `RuntimeError: Event loop is closed` or hung execution

**Debugging steps:**

```python
# Ensure all async calls use await
async def my_handler():
    # WRONG - missing await
    result = repository.get("org-id")
    print(result)  # Will print coroutine object

    # RIGHT - with await
    result = await repository.get("org-id")
    print(result)  # Will print actual result
```

## Performance Debugging

### Measuring Execution Time

```python
import time

@openapi_handler(...)
async def slow_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    start = time.time()

    # Slow operation
    result = await expensive_operation()

    elapsed = time.time() - start
    print(f"expensive_operation took {elapsed:.2f}s")

    return func.JsonResponse({"result": result, "duration_seconds": elapsed})
```

### Finding Slow Operations

```python
import time
from contextlib import asynccontextmanager

@asynccontextmanager
async def timer(name: str):
    """Context manager to time operations."""
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        print(f"{name} took {elapsed:.3f}s")

# Usage:
async def my_handler():
    async with timer("database query"):
        result = await repository.get("org-id")

    async with timer("external API call"):
        response = await api_client.fetch_data()
```

### Profiling with cProfile

For detailed performance analysis:

```bash
# Run test with profiling
python -m cProfile -s cumulative -m pytest tests/integration/test_slow.py

# Shows:
# ncalls  tottime  cumtime
# 100     0.003   0.150  expensive_function
# 1000    0.001   0.050  helper_function
```

## Troubleshooting

### Debugger Won't Attach

**Issue:** "Failed to attach to port 5678"

**Solution:**

```bash
# 1. Verify Functions runtime started
curl http://localhost:7071/api/health

# 2. Check if port 5678 is in use
lsof -i :5678

# 3. Kill conflicting process
kill -9 <PID>

# 4. Restart Functions
func start
```

### "Cannot find module" During Debugging

**Issue:** Import errors when debugging

**Solution:**

```bash
# 1. Verify imports are correct
python -c "from shared.models import Organization"

# 2. Check PYTHONPATH includes the right directory
echo $PYTHONPATH

# 3. Restart VS Code and Functions runtime
```

### Breakpoints Not Stopping

**Issue:** Code runs past breakpoint without stopping

**Solution:**

```python
# 1. Verify breakpoint is set (red dot visible)
# Click in left margin to set breakpoint

# 2. Check file matches running code
# Ensure you're editing the same file the runtime is using

# 3. Try a different approach
import sys; sys.exit(1)  # Will immediately fail and show traceback
```

### Functions Runtime Crashes

**Issue:** `func start` crashes or exits unexpectedly

**Solution:**

```bash
# 1. Check the full error output
func start 2>&1 | head -50

# 2. Look at logs
tail -f /tmp/func-test.log

# 3. Verify dependencies are installed
pip list | grep -E "azure|pydantic"

# 4. Reinstall if needed
pip install -r requirements.txt
```

## Best Practices

1. **Start with print statements** - Quick and simple for most issues
2. **Use the debugger for complex logic** - When print debugging gets tedious
3. **Add logging to important functions** - Helps with production debugging
4. **Check logs first** - "Did you look at the error message?"
5. **Isolate the problem** - Narrow down which function is failing
6. **Test in isolation** - Write unit tests for the specific function

## Next Steps

- **Test your changes:** See [Test Workflows Locally](./testing.md)
- **Read error reference:** See [Troubleshooting](/troubleshooting/)

---

**Pro tip:** Use `func start --verbose` for more detailed output from the Functions runtime.
