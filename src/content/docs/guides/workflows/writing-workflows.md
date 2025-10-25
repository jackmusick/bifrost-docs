---
title: Write Workflows
description: Comprehensive guide to writing workflows in Bifrost with best practices and advanced patterns
---

## Overview

This guide covers everything you need to know about writing workflows in Bifrost. We'll explore workflow structure, parameters, return values, error handling, and best practices.

## Workflow Anatomy

Every workflow has the same basic structure:

```python
from bifrost import workflow, param, ExecutionContext

# 1. Define with @workflow decorator
@workflow(
    name="unique_name",              # Required: unique identifier
    description="Human-readable",    # Required: displayed in UI
    category="user_management",      # Optional: category for grouping
    tags=["m365", "automation"],     # Optional: for filtering
    execution_mode="sync",           # Optional: "sync" or "async" (default: "sync")
    timeout_seconds=300              # Optional: max execution time
)

# 2. Add parameters with @param (optional, can have zero to many)
@param("param1", type="string", required=True)
@param("param2", type="int", default_value=42)

# 3. Define async function
async def unique_name(context: ExecutionContext, param1: str, param2: int = 42):
    """
    Docstring explaining what this workflow does.
    
    Args:
        context: Execution context with access to org data, config, logging
        param1: Description of parameter 1
        param2: Description of parameter 2
        
    Returns:
        Dictionary with workflow result
    """
    # 4. Implement workflow logic
    context.log("info", f"Processing {param1}")
    
    # 5. Return result
    return {"result": "success", "value": param1}
```

## The @workflow Decorator

The `@workflow` decorator registers your function with the platform and defines its behavior.

### Required Parameters

- **name** (str): Unique workflow identifier (snake_case, lowercase)
- **description** (str): Human-readable description shown in UI

### Optional Parameters

#### Categorization
- **category** (str): Category for organizing workflows (default: "General")
  - Common values: "user_management", "automation", "reporting", "integration"
- **tags** (list[str]): Optional tags for filtering and searching

#### Execution Control
- **execution_mode** (str): How the workflow executes
  - `"sync"` (default): Execute immediately, return result
  - `"async"`: Queue for background execution, return execution ID immediately
- **timeout_seconds** (int): Maximum execution time in seconds (default: 300)

#### Advanced Options
- **retry_policy** (dict): Configuration for automatic retries
  - Example: `{"max_attempts": 3, "backoff": 2}`
- **schedule** (str): Cron expression for scheduled execution
  - Example: `"0 9 * * *"` = Daily at 9 AM
- **endpoint_enabled** (bool): Expose as HTTP endpoint (default: False)
- **allowed_methods** (list): HTTP methods if endpoint_enabled (default: ["POST"])
- **disable_global_key** (bool): Require workflow-specific API key (default: False)
- **public_endpoint** (bool): Skip authentication for webhooks (default: False)

### Execution Modes Explained

#### Synchronous (sync)

Best for operations that complete quickly (< 10 seconds):

```python
@workflow(
    name="quick_lookup",
    description="Quick database lookup",
    execution_mode="sync",
    timeout_seconds=30
)
async def quick_lookup(context: ExecutionContext, user_id: str):
    # Operation completes immediately
    user = await database.get_user(user_id)
    return {"user": user}
```

When executed:
1. User submits form
2. Workflow runs immediately
3. Result returned to user within seconds
4. UI shows completion instantly

#### Asynchronous (async)

Best for long-running operations (> 30 seconds):

```python
@workflow(
    name="bulk_import",
    description="Import large dataset",
    execution_mode="async",
    timeout_seconds=1800  # 30 minutes
)
async def bulk_import(context: ExecutionContext, csv_url: str):
    # Operation queued for background execution
    items = await fetch_csv(csv_url)
    for item in items:
        await import_item(item)
        context.set_variable("processed", len(items))
    return {"imported": len(items)}
```

When executed:
1. User submits form
2. Workflow queued immediately
3. Execution ID returned to user (status: "Pending")
4. User can check status later
5. Workflow runs in background
6. Result stored when complete

### Scheduled Workflows

Run automatically on a schedule:

```python
@workflow(
    name="daily_report",
    description="Generate daily report",
    execution_mode="scheduled",
    schedule="0 9 * * *",  # Daily at 9 AM UTC
    expose_in_forms=False   # Hide from manual execution
)
async def daily_report(context: ExecutionContext):
    # This runs automatically every day at 9 AM
    report = await generate_daily_report()
    await send_report(report)
    return {"status": "sent"}
```

Cron expression format: `minute hour day month day_of_week`
- `0 9 * * *` = Daily at 9 AM
- `0 */6 * * *` = Every 6 hours
- `0 9 * * 1` = Every Monday at 9 AM
- `0 0 1 * *` = First day of every month at midnight

## The @param Decorator

Parameters define workflow inputs and automatically generate form fields.

### Basic Usage

```python
@param(
    name="email",              # Required: parameter name
    type="string",             # Required: parameter type
    label="Email Address",     # Optional: display label
    required=True,             # Optional: is this required? (default: False)
    default_value=None,        # Optional: default value if not provided
    help_text="User email",    # Optional: help text shown in form
    validation={...},          # Optional: validation rules
    data_provider="..."        # Optional: dynamic options
)
```

### Parameter Types

| Type | Use Case | Example |
|------|----------|---------|
| `string` | Text input | name, email, description |
| `int` | Integer number | quantity, age, ID |
| `float` | Decimal number | price, percentage, score |
| `bool` | True/False checkbox | is_active, send_email, notify |
| `email` | Email address (with validation) | user_email, contact_email |
| `json` | JSON object | metadata, config, settings |
| `list` | Array of values | tags, items, emails |

### Validation Rules

#### String Validation

```python
@param("username", type="string",
    validation={
        "min_length": 3,           # Minimum length
        "max_length": 50,          # Maximum length
        "pattern": r"^[a-zA-Z0-9_]+$"  # Regex pattern
    }
)
```

#### Number Validation

```python
@param("quantity", type="int",
    validation={
        "min": 1,           # Minimum value
        "max": 1000         # Maximum value
    }
)

@param("discount", type="float",
    validation={
        "min": 0.0,         # Can't be negative
        "max": 100.0        # Can't exceed 100
    }
)
```

#### Enum (Limited Options)

```python
@param("status", type="string",
    validation={
        "enum": ["active", "inactive", "pending", "deleted"]
    }
)
```

### Custom Validation in Workflow Code

For complex validation that can't be expressed in decorator rules:

```python
@workflow(name="validate_schedule")
@param("start_date", type="string", label="Start Date")
@param("end_date", type="string", label="End Date")
async def validate_schedule(context: ExecutionContext, start_date: str, end_date: str):
    from datetime import datetime
    
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except ValueError:
        return {"error": "Invalid date format (use ISO format)"}
    
    if end <= start:
        return {"error": "End date must be after start date"}
    
    # Continue with valid dates
    return {"valid": True, "days": (end - start).days}
```

## The ExecutionContext

Every workflow receives a context parameter with access to platform features:

```python
@workflow(name="context_example")
async def context_example(context: ExecutionContext):
    # Organization information
    org_id = context.org_id
    org_name = context.org_name
    
    # User information
    user_id = context.user_id
    user_email = context.email
    user_name = context.name
    
    # Execution metadata
    execution_id = context.execution_id
    is_admin = context.is_platform_admin
    
    return {"org": org_id, "user": user_email}
```

### Configuration Access

```python
# Get configuration (org-scoped, falls back to global)
api_url = context.get_config("api_url", default="https://api.example.com")

# Check if configuration exists
if context.has_config("custom_setting"):
    setting = context.get_config("custom_setting")

# Secrets are auto-resolved from Key Vault
api_key = context.get_config("api_key")
```

### Logging

```python
# Log at different levels
context.log("info", "Processing started", {"user_id": "123"})
context.log("warning", "License count low", {"remaining": 5})
context.log("error", "API call failed", {"status": 500})
```

### State Tracking

```python
# Save checkpoints for debugging
context.save_checkpoint("processing_start", {
    "items": 100,
    "batch_size": 10
})

# Store variables (visible in execution record)
context.set_variable("processed", 0)
context.set_variable("failed", [])

# Retrieve variables
processed = context.get_variable("processed", default=0)
```

## Return Values

Workflows must return a dictionary (which gets JSON serialized):

```python
@workflow(name="return_example")
async def return_example(context: ExecutionContext):
    # Simple result
    return {"status": "success"}
    
    # Nested result
    return {
        "status": "success",
        "user": {"id": "123", "email": "user@example.com"},
        "items": [1, 2, 3]
    }
    
    # Error result (still returns 200, but indicates failure)
    return {
        "status": "error",
        "error": "User not found",
        "details": {}
    }
```

### Return Value Guidelines

- **Always return dict** (not list, string, int, etc.)
- **Include status** for clarity: `"success"` or `"error"`
- **Nest data structures** as needed
- **Avoid returning secrets** in results
- **Keep size reasonable** (< 1MB for sync workflows)

## Parameter Decorators

Decorators are applied bottom-up. The parameter defined last appears first in the form:

```python
@workflow(name="parameter_order")
@param("first", type="string")      # Appears LAST
@param("second", type="string")     # Appears SECOND
@param("third", type="string")      # Appears FIRST
async def parameter_order(context, first, second, third):
    pass
```

The form will show fields in this order:
1. `third`
2. `second`
3. `first`

To match declaration order with display order, declare decorators in reverse:

```python
@workflow(name="parameter_order")
@param("third", type="string")      # Appears FIRST
@param("second", type="string")     # Appears SECOND
@param("first", type="string")      # Appears LAST
async def parameter_order(context, first, second, third):
    pass
```

## Data Providers

Data providers return dynamic options for form dropdowns:

```python
from bifrost import data_provider

@data_provider(
    name="get_teams",
    description="Get list of teams",
    category="organization",
    cache_ttl_seconds=300
)
async def get_teams(context: ExecutionContext):
    # Fetch from your data source
    teams = await database.get_teams(context.org_id)
    
    return [
        {
            "label": team["name"],           # Display in dropdown
            "value": team["id"],             # Passed to workflow
            "metadata": {"members": len(team["members"])}
        }
        for team in teams
    ]
```

Use in a workflow:

```python
@workflow(name="assign_to_team")
@param("team", type="string", data_provider="get_teams", required=True)
async def assign_to_team(context: ExecutionContext, team: str):
    # team is the selected team's ID
    return {"assigned_to": team}
```

## Best Practices

### 1. Clear Naming

```python
# Good
@workflow(name="create_m365_user", description="Create new user in Microsoft 365")

# Bad
@workflow(name="proc1", description="Does stuff")
```

### 2. Focused Responsibility

```python
# Good - Single responsibility
@workflow(name="create_user")
async def create_user(context, email, name):
    # Only creates user
    pass

# Bad - Too many responsibilities
@workflow(name="user_onboarding")
async def user_onboarding(context, email, name, license, team, groups, email_template):
    # Creates user, assigns license, adds to team, adds to groups, sends email...
    pass
```

### 3. Comprehensive Logging

```python
# Good
context.log("info", "User creation started", {"email": email})
try:
    user = await create_user(email, name)
    context.log("info", "User created successfully", {"user_id": user.id})
except Exception as e:
    context.log("error", "User creation failed", {"email": email, "error": str(e)})
    raise

# Bad
# No logging - can't debug failures
user = await create_user(email, name)
```

### 4. Input Validation

```python
# Good - Validate early
if not email or "@" not in email:
    return {"error": "Invalid email format"}

if not name or len(name) < 2:
    return {"error": "Name must be at least 2 characters"}

# Bad - No validation, fails later with cryptic error
user = await create_user(email, name)
```

### 5. Error Handling

```python
# Good - Catch and return error state
try:
    result = await api_call()
    return {"success": True, "result": result}
except Exception as e:
    context.log("error", "API call failed", {"error": str(e)})
    return {"success": False, "error": str(e)}

# Bad - Unhandled exception, workflow fails
result = await api_call()
return {"success": True, "result": result}
```

### 6. Use Appropriate Execution Mode

```python
# Good - Async for long operations
@workflow(name="bulk_import", execution_mode="async", timeout_seconds=1800)
async def bulk_import(context, csv_url):
    # Process thousands of items...
    pass

# Bad - Sync for operation that takes 5 minutes
@workflow(name="bulk_import", execution_mode="sync")
async def bulk_import(context, csv_url):
    # Times out after 300 seconds
    pass
```

## Common Patterns

### Pattern: List Processing

```python
@workflow(name="process_items")
@param("items", type="list", label="Items")
async def process_items(context: ExecutionContext, items: list):
    results = []
    errors = []
    
    for item in items:
        try:
            result = await process_item(item)
            results.append(result)
        except Exception as e:
            errors.append({"item": item, "error": str(e)})
    
    return {
        "processed": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }
```

### Pattern: Conditional Logic

```python
@workflow(name="handle_action")
@param("action", type="string")
async def handle_action(context: ExecutionContext, action: str):
    if action == "create":
        return await create_resource()
    elif action == "update":
        return await update_resource()
    elif action == "delete":
        return await delete_resource()
    else:
        return {"error": f"Unknown action: {action}"}
```

### Pattern: Chained Operations

```python
@workflow(name="create_user_with_license")
@param("email", type="email")
@param("license_sku", type="string")
async def create_user_with_license(context: ExecutionContext, email: str, license_sku: str):
    # Step 1: Create user
    context.log("info", "Creating user...")
    user = await create_m365_user(email)
    context.save_checkpoint("user_created", {"user_id": user.id})
    
    # Step 2: Assign license
    context.log("info", "Assigning license...")
    await assign_license(user.id, license_sku)
    context.save_checkpoint("license_assigned", {"sku": license_sku})
    
    return {
        "success": True,
        "user_id": user.id,
        "email": email,
        "license": license_sku
    }
```

## Troubleshooting

### Workflow doesn't appear in UI
- Check `@workflow` decorator is present
- Verify workflow name is unique
- Check file is in correct directory
- Look for import errors in function app logs

### Parameters show validation errors
- Check parameter type is valid (string, int, float, bool, json, list, email)
- Verify validation rules are correct
- Test with curl to see exact error

### Execution fails silently
- Add more logging with `context.log()`
- Save checkpoints to track progress
- Check execution detail view for error messages
- Review function app logs in Application Insights

### Data provider not showing options
- Verify `@data_provider` decorator is correct
- Check provider name matches in `@param`
- Ensure provider returns list of dicts with `label` and `value`
- Verify provider isn't raising exceptions

## Next Steps

- Explore [Using Decorators](/docs/guides/workflows/using-decorators) for advanced decorator features
- Learn [Error Handling](/docs/guides/workflows/error-handling) patterns
- Review [Concepts: Workflows](/docs/concepts/workflows) for deeper understanding
- Check the [Workflow Development](/docs/) guide for API reference
