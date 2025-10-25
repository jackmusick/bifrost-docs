---
title: Workflows
description: Conceptual understanding of workflows, execution models, context, and lifecycle
---

## What is a Workflow?

A workflow is an executable automation task in Bifrost. It's a Python async function decorated with `@workflow` that:

- Accepts input parameters
- Performs business logic (API calls, data processing, etc.)
- Returns results
- Has access to organization context, configuration, logging, and integrations
- Can be executed manually via forms, scheduled on a cron, or triggered via HTTP endpoints

### Example Workflow

```python
from bifrost import workflow, param, ExecutionContext

@workflow(
    name="create_user",
    description="Create new user in Microsoft 365",
    category="user_management"
)
@param("email", type="email", required=True)
@param("first_name", type="string", required=True)
async def create_user(context: ExecutionContext, email: str, first_name: str):
    """Create a new user with the provided email."""

    # Log the start
    context.log("info", f"Creating user: {email}")

    # Your business logic
    user = await create_m365_user(email, first_name)

    # Return results
    return {
        "success": True,
        "user_id": user.id,
        "email": user.email
    }
```

When executed:
1. User enters parameters (email, first_name) via form
2. Bifrost validates inputs
3. Workflow function executes
4. Results returned to user

## Execution Models

### Synchronous Execution (sync)

Executes immediately and blocks until complete:

```python
@workflow(
    name="quick_lookup",
    execution_mode="sync",
    timeout_seconds=30
)
async def quick_lookup(context: ExecutionContext, user_id: str):
    # Executes immediately
    user = await lookup_user(user_id)
    # Returns to caller
    return {"user": user}
```

Timeline:
```
T+0s: User submits form
T+0.1s: Workflow starts
T+0.5s: API call completes
T+0.6s: Result returned to user
```

Use for:
- Quick operations (< 10 seconds)
- Form submissions
- API endpoints
- Real-time interactions

### Asynchronous Execution (async)

Queues for background execution and returns immediately:

```python
@workflow(
    name="bulk_import",
    execution_mode="async",
    timeout_seconds=1800
)
async def bulk_import(context: ExecutionContext, csv_url: str):
    # Queued, doesn't block caller
    items = await fetch_csv(csv_url)
    for item in items:
        await import_item(item)  # Could take minutes
    return {"imported": len(items)}
```

Timeline:
```
T+0s: User submits form
T+0.1s: Workflow queued, execution ID returned (status: "Pending")
T+0.2s: User can close form immediately
T+1m: Workflow actually starts executing
T+15m: Workflow completes, result stored
T+15m+1s: User checks status, sees "Success"
```

Use for:
- Long-running operations (> 30 seconds)
- Bulk processing
- Batch imports/exports
- Background jobs

### Scheduled Execution (scheduled)

Runs automatically on a schedule:

```python
@workflow(
    name="daily_report",
    execution_mode="scheduled",
    schedule="0 9 * * *"  # Every day at 9 AM
)
async def daily_report(context: ExecutionContext):
    # Runs automatically every day at 9 AM
    report = await generate_daily_report()
    await send_report(report)
    return {"status": "sent"}
```

Timeline:
```
9:00 AM: Scheduler triggers workflow
9:00:01 AM: Workflow starts
9:05 AM: Report generated
9:05:30 AM: Report sent
9:05:31 AM: Execution recorded
```

Use for:
- Recurring tasks
- Scheduled reports
- Automated maintenance
- Cleanup operations

## Execution Lifecycle

Every workflow execution goes through a lifecycle:

```
1. PENDING
   ↓ (workflow queued, waiting to start)
2. RUNNING
   ↓ (workflow executing)
3. SUCCESS or FAILED
   (workflow completed)
```

### Detailed Lifecycle

#### 1. Submission
- User submits form or API request
- Parameters validated
- Execution record created
- For sync: Execution starts immediately
- For async: Execution queued

#### 2. Execution
- Workflow function runs
- Has access to context (org, user, logging, config, etc.)
- Can call integrations, make API calls, process data
- Logs are captured
- Checkpoints are saved
- Variables are tracked

#### 3. Completion
- Workflow function returns result
- For sync: Result returned immediately to user
- For async: Result stored in database, user can poll
- Execution record updated with status, duration, logs, checkpoints

#### 4. Persistence
- Entire execution record stored
- Visible in execution history UI
- Can be queried via API
- Logs and checkpoints preserved for debugging

### State During Execution

Each execution has state that persists:

```
Execution Record:
├── Metadata
│   ├── execution_id: unique ID
│   ├── workflow_name: which workflow
│   ├── org_id: which organization
│   ├── started_at: when it started
│   └── completed_at: when it finished
├── Input
│   ├── parameters: what was passed in
│   └── user_context: who triggered it
├── Output
│   ├── result: what was returned
│   ├── status: Success/Failed
│   └── duration_ms: how long it took
├── Logs
│   ├── info: "User created successfully"
│   ├── warning: "License count low"
│   └── error: "API returned 500"
├── Checkpoints
│   ├── "user_created": {user_id: "123"}
│   ├── "license_assigned": {sku: "E3"}
│   └── "email_sent": {timestamp: "..."}
└── Variables
    ├── processed: 45
    ├── failed: 2
    └── success_rate: 95.7%
```

### Execution Status

- **Pending**: Workflow queued (async only)
- **Running**: Currently executing
- **Success**: Completed with no errors, returned result
- **Failed**: Encountered error, could not complete
- **CompletedWithErrors**: Completed but returned error state

## Context and Access

Every workflow receives an `ExecutionContext` parameter providing access to:

### Organization Information

```python
context.org_id        # Which organization
context.org_name      # Organization display name
```

### User Information

```python
context.user_id       # Who triggered this
context.email         # Their email
context.name          # Their display name
context.is_platform_admin  # Are they a platform admin?
```

### Execution Information

```python
context.execution_id  # Unique ID for this execution
context.scope         # Global vs organization scope
```

### Configuration Access

```python
api_url = context.get_config("api_url", default="...")
api_key = context.get_config("api_key")  # Secrets auto-resolved
```

### State Tracking

```python
context.log("info", "Message", {"data": "value"})
context.save_checkpoint("name", {"state": "data"})
context.set_variable("counter", 42)
context.get_variable("counter", default=0)
```

### Integrations

```python
graph = context.get_integration("msgraph")  # Microsoft Graph
halo = context.get_integration("halopsa")   # HaloPSA
```

## Parameters and Validation

Workflows accept input parameters defined with `@param`:

```python
@param("email", type="email", required=True)
@param("count", type="int", validation={"min": 1, "max": 100})
@param("team", type="string", data_provider="get_teams")
async def example(context, email, count, team):
    pass
```

### Parameter Types

| Type | Validation | Example |
|------|-----------|---------|
| `string` | pattern, min_length, max_length | "John Doe" |
| `int` | min, max | 42 |
| `float` | min, max | 3.14 |
| `bool` | none | True/False |
| `email` | email format | "user@example.com" |
| `json` | none (any JSON) | {"key": "value"} |
| `list` | none | ["item1", "item2"] |

### Automatic Validation

Parameters are validated **before** your workflow executes:

```python
@param("email", type="email")  # Validates email format
@param("count", type="int", validation={"min": 1, "max": 100})  # Validates range
```

If validation fails, Bifrost returns 400 Bad Request. Invalid requests never reach your workflow code.

## Return Values

Workflows must return a dictionary (JSON-serializable):

```python
# Simple success
return {"success": True}

# With data
return {
    "success": True,
    "user_id": "123",
    "email": "user@example.com"
}

# Error response (still returns 200 status)
return {
    "success": False,
    "error": "User not found",
    "error_code": "NOT_FOUND"
}

# Partial success
return {
    "total": 100,
    "successful": 95,
    "failed": 5,
    "errors": [...]
}
```

## Error Handling Philosophy

Bifrost distinguishes between two types of errors:

### Workflow Errors (Infrastructure)

When the workflow **cannot execute**:
- Code syntax error
- Module import failure
- Unexpected exception not caught
- Timeout
- Out of memory

Result: Execution fails, returns 500 status, shows error in UI

### Workflow Failures (Business Logic)

When the workflow **executes but indicates failure**:
- Input validation failed
- User not found
- Permission denied
- API call failed but handled gracefully

Result: Execution succeeds (status: "Failed"), returns 200 status, result shows error details

Best practice: **Always catch and handle errors gracefully**

```python
# Good - handles error gracefully
try:
    user = await get_user(user_id)
except UserNotFoundError:
    return {"success": False, "error": "User not found"}

# Bad - unhandled exception
user = await get_user(user_id)  # Crashes if user not found
```

## Logging and Debugging

Logging serves multiple purposes:

### Operational Monitoring

Track what happens during execution:

```python
context.log("info", "Starting user creation", {"email": email})
context.log("info", "User created", {"user_id": user_id})
context.log("info", "License assigned", {"sku": license_sku})
```

### Issue Investigation

When something goes wrong:

```python
context.log("error", "Failed to create user", {
    "email": email,
    "error": str(e),
    "error_type": type(e).__name__
})
```

Logs are searchable and visible in execution history.

### Checkpoints for State Tracking

Save state snapshots during execution:

```python
context.save_checkpoint("processing_start", {
    "total_items": 1000,
    "timestamp": datetime.utcnow().isoformat()
})

# Process items...

context.save_checkpoint("processing_complete", {
    "processed": 1000,
    "duration_seconds": 45
})
```

Checkpoints let you understand exactly what happened at each step.

### Variables for Metrics

Track metrics visible in execution record:

```python
context.set_variable("processed_count", 100)
context.set_variable("failed_emails", ["user1@example.com"])
context.set_variable("success_rate", 98.5)
```

Variables appear in execution detail view.

## Sync vs Async Decision

### Choose Sync When

- Operation < 10 seconds
- User needs immediate feedback
- Simple form submissions
- API calls with quick response
- User is waiting for result

### Choose Async When

- Operation > 30 seconds
- Processing large datasets
- Multiple API calls
- Workflow calls other workflows
- User doesn't need immediate result

### Real-World Examples

**Sync:**
- `create_user` (30-50ms)
- `validate_email` (5-10ms)
- `lookup_license_availability` (100-200ms)

**Async:**
- `import_csv_users` (5-15 minutes)
- `bulk_license_assignment` (30+ minutes)
- `generate_monthly_report` (10-60 seconds)

## Workflows vs Forms

**Workflows:**
- Executable automation logic
- Can be triggered from forms, API, schedules
- Can access org context, secrets, integrations
- Can save checkpoints, logs, variables

**Forms:**
- User interface for submitting workflow inputs
- Calls workflows to perform actions
- Displays workflow results

Relationship:
```
User → Form → Workflow → Result
                ↓
        (context, secrets, logs)
```

## Scoping

Workflows operate in an organization scope:

```python
@workflow(name="create_user")
async def create_user(context: ExecutionContext, email: str):
    # context.org_id = "acme-corp"
    # Automatically scoped to this organization
    # Cannot access other organization's data
    pass
```

### Global vs Organization Scope

- **Organization scope**: Most workflows
  - Isolated per organization
  - Access to org config, secrets, OAuth connections
  - Cannot access other orgs' data

- **Global scope**: Platform admin only
  - Not isolated
  - Access to global configuration
  - Rarely needed

## Execution Limits

Plan-dependent limits:

| Aspect | Limit |
|--------|-------|
| Max execution time (sync) | 5-30 minutes (depends on plan) |
| Max execution time (async) | 1-24 hours (depends on plan) |
| Max request size | 100 KB |
| Max response size | 10 MB |
| Concurrent executions | 100+ (auto-scaled) |
| Timeout behavior | Times out with error |

## Multi-Tenancy

Bifrost supports multiple organizations (tenants) on a single platform:

```python
# Organization A's execution
context.org_id = "org-a"
await context.get_config("api_key")  # Gets org-a's key

# Organization B's execution  
context.org_id = "org-b"
await context.get_config("api_key")  # Gets org-b's key

# Same workflow code, different organizations' data
```

Each organization:
- Has isolated configuration
- Has isolated OAuth connections
- Has isolated execution history
- Cannot access other organizations' data

## Workflow Composition

Workflows can call other workflows:

```python
@workflow(name="user_onboarding")
async def user_onboarding(context, email):
    # Create user
    user = await create_user_workflow(context, email)
    
    # Assign license
    await assign_license_workflow(context, user.id, "E3")
    
    # Add to team
    await add_to_team_workflow(context, user.id, "engineering")
    
    return {"status": "onboarded", "user_id": user.id}
```

This pattern allows:
- Code reuse
- Separation of concerns
- Easier testing
- Composable automation

## Performance Characteristics

Typical workflow performance:

```
Simple workflow (1 API call):      10-100 ms
Complex workflow (5 API calls):    500-2000 ms
Batch operation (1000 items):      30-60 seconds
Scheduled report generation:       5-15 minutes
```

Optimization tips:
- Use async operations for I/O
- Batch database operations
- Cache results when appropriate
- Use `async for` for streaming

## Best Practices

### 1. Single Responsibility

```python
# Good - one task
@workflow(name="create_user")
async def create_user(...): ...

# Good - another task
@workflow(name="assign_license")
async def assign_license(...): ...

# Bad - too much
@workflow(name="user_onboarding")
async def user_onboarding(...):
    # Creates, assigns, adds to group, sends email...
```

### 2. Clear Naming

```python
# Good
@workflow(name="create_m365_user", description="Create Microsoft 365 user")

# Bad
@workflow(name="proc1", description="Do something")
```

### 3. Comprehensive Logging

```python
context.log("info", "Starting operation", {"inputs": {...}})
# ... work ...
context.log("info", "Operation complete", {"results": {...}})
```

### 4. Graceful Error Handling

```python
try:
    result = await operation()
except Exception as e:
    context.log("error", "Operation failed", {"error": str(e)})
    return {"success": False, "error": str(e)}
```

### 5. Use Appropriate Execution Mode

```python
# < 10 seconds → sync
@workflow(name="quick_lookup", execution_mode="sync")

# > 30 seconds → async
@workflow(name="bulk_import", execution_mode="async")
```

## Next Steps

- Read [Build Your First Workflow](/docs/tutorials/first-workflow) tutorial
- Explore [Write Workflows](/docs/guides/workflows/writing-workflows) guide
- Learn [Use Decorators](/docs/guides/workflows/using-decorators) guide
- Check [Handle Errors](/docs/guides/workflows/error-handling) guide
