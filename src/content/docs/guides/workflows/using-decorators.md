---
title: Use Decorators
description: Deep dive into Bifrost decorators and how they work together to define workflows
---

## Overview

Bifrost uses three main decorators to define workflows and their inputs:

- **`@workflow`**: Registers a function as an executable workflow
- **`@param`**: Defines input parameters with validation and options
- **`@data_provider`**: Returns dynamic options for form dropdowns

This guide explains each decorator in detail and shows how to use them effectively.

## The @workflow Decorator

The `@workflow` decorator is the foundation of every Bifrost workflow.

### Required Parameters

```python
@workflow(
    name="create_user",              # Unique identifier (required)
    description="Create new user"    # Display text (required)
)
async def create_user(context, email):
    pass
```

- **name** (str): Unique identifier for your workflow
  - Must be lowercase with underscores (snake_case)
  - Used in URLs and API calls
  - Example: `create_m365_user`, `assign_license`, `generate_report`

- **description** (str): Human-readable description
  - Shown in workflow UI
  - Should explain what the workflow does
  - Example: "Create new user in Microsoft 365 with email address"

### Categorization Parameters

```python
@workflow(
    name="my_workflow",
    description="...",
    category="user_management",          # Category for grouping
    tags=["m365", "automation", "user"]  # Tags for searching
)
```

- **category** (str): Category for organizing workflows
  - Standard categories: `user_management`, `automation`, `reporting`, `integration`, `administration`
  - Custom categories allowed
  - Workflows grouped by category in UI

- **tags** (list[str]): Optional tags for filtering
  - Useful for filtering workflows in UI
  - Examples: `["m365", "async", "long-running"]`

### Execution Control Parameters

```python
@workflow(
    name="my_workflow",
    description="...",
    execution_mode="sync",           # How to execute
    timeout_seconds=300              # Max execution time
)
```

- **execution_mode** (str): How the workflow executes
  - `"sync"` (default): Execute immediately, block until complete, return result
  - `"async"`: Queue for background execution, return execution ID immediately
  - Use `sync` for: quick operations, form submissions, API calls
  - Use `async` for: bulk operations, long-running tasks, background jobs

- **timeout_seconds** (int): Maximum execution time
  - Default: 300 (5 minutes)
  - Recommended range: 30-1800 seconds
  - Azure Functions hard limit: varies by plan
  - Tip: Use `async` mode for operations > 30 seconds

### Retry Configuration

```python
@workflow(
    name="my_workflow",
    description="...",
    retry_policy={
        "max_attempts": 3,      # Total attempts
        "backoff": 2,           # Exponential backoff multiplier
        "initial_delay": 1      # Initial delay in seconds
    }
)
```

- **retry_policy** (dict): Automatic retry configuration
  - `max_attempts`: Total attempts (including initial) before giving up
  - `backoff`: Multiplier for exponential backoff (2 = 1s, 2s, 4s, 8s...)
  - `initial_delay`: First retry delay in seconds
  - Only applies to `async` mode

Example:
```python
# This will retry on failure with exponential backoff
# Attempts: 0s (initial), 1s, 2s, 4s (if max_attempts=4)
retry_policy={"max_attempts": 4, "backoff": 2, "initial_delay": 1}
```

### Scheduling Parameters

```python
@workflow(
    name="daily_report",
    description="...",
    execution_mode="async",          # Use "async" for scheduled workflows
    schedule="0 9 * * *"             # Cron expression
)
```

- **schedule** (str): Cron expression for when to run
  - Format: `minute hour day month day_of_week`
  - Examples:
    - `"0 9 * * *"` = Every day at 9:00 AM
    - `"0 */6 * * *"` = Every 6 hours
    - `"0 9 * * 1"` = Mondays at 9:00 AM
    - `"0 0 1 * *"` = First day of month at midnight
  - Reference: [crontab.guru](https://crontab.guru) for help

### HTTP Endpoint Parameters

```python
@workflow(
    name="my_webhook",
    description="...",
    endpoint_enabled=True,                  # Enable HTTP endpoint
    allowed_methods=["GET", "POST"],        # HTTP methods
    disable_global_key=False,               # Require specific API key
    public_endpoint=False                   # Skip authentication
)
```

- **endpoint_enabled** (bool): Expose as HTTP endpoint
  - Default: False
  - When True: Accessible at `/api/endpoints/{workflow_name}`
  - Requires API key unless `public_endpoint=True`

- **allowed_methods** (list[str]): HTTP methods to allow
  - Default: ["POST"]
  - Options: ["GET", "POST", "PUT", "DELETE"]
  - Example: `["GET", "POST"]` for both read and write

- **disable_global_key** (bool): Require workflow-specific API key
  - Default: False
  - When True: Global platform keys don't work, only workflow-specific keys
  - Use for: sensitive operations, audit compliance

- **public_endpoint** (bool): Skip authentication for webhooks
  - Default: False
  - When True: No API key required, endpoint is public
  - Use for: external webhooks, third-party integrations
  - Important: Validate requests in workflow code

### Complete Example

```python
@workflow(
    name="create_m365_user",
    description="Create new user in Microsoft 365 with license assignment",
    category="user_management",
    tags=["m365", "user", "onboarding"],
    execution_mode="sync",
    timeout_seconds=60,
    endpoint_enabled=True,
    allowed_methods=["POST"],
    disable_global_key=False,
    public_endpoint=False
)
@param("email", type="email", required=True)
@param("first_name", type="string", required=True)
async def create_m365_user(context, email, first_name):
    """Create new M365 user with basic setup."""
    # Implementation...
    pass
```

## The @param Decorator

Parameters define workflow inputs and generate form fields automatically.

### Basic Syntax

```python
@param(
    name="email",                      # Parameter name (required)
    type="email",                      # Parameter type (required)
    label="Email Address",             # Display label (optional)
    required=True,                     # Is this required? (optional)
    default_value=None,                # Default value (optional)
    help_text="User's email",          # Help text (optional)
    validation={"min_length": 5},      # Validation rules (optional)
    data_provider="get_users"          # Dynamic options (optional)
)
```

### Parameter Type Details

| Type | Python Type | Use Case | Example |
|------|-------------|----------|---------|
| `string` | str | Text input | "John Doe", "description" |
| `int` | int | Integer number | 42, 100, -5 |
| `float` | float | Decimal number | 3.14, 99.99 |
| `bool` | bool | Checkbox (true/false) | True, False |
| `email` | str | Email (with validation) | "user@example.com" |
| `json` | dict | JSON object | {"key": "value"} |
| `list` | list | Array of values | ["item1", "item2"] |

### Validation Rules

Validation rules vary by type:

#### String Validation

```python
@param("username", type="string",
    validation={
        "min_length": 3,               # Minimum characters
        "max_length": 50,              # Maximum characters
        "pattern": r"^[a-zA-Z0-9_]+$"  # Regex pattern
    }
)
```

Common patterns:
- Alphanumeric: `^[a-zA-Z0-9]+$`
- Email domain: `^[^@]+@example\.com$`
- URL: `^https?://`

#### Number Validation

```python
@param("quantity", type="int",
    validation={
        "min": 1,      # Minimum value
        "max": 1000    # Maximum value
    }
)
```

#### Enum (Limited Choices)

```python
@param("status", type="string",
    validation={
        "enum": ["active", "inactive", "pending"]
    }
)
```

### Data Providers

Use data providers for dynamic dropdown options:

```python
@param("department", type="string",
    label="Select Department",
    data_provider="get_departments",  # Name of data provider
    required=True
)
```

The data provider returns options:

```python
@data_provider(name="get_departments", description="...")
async def get_departments(context):
    return [
        {"label": "IT", "value": "it"},
        {"label": "HR", "value": "hr"},
        {"label": "Finance", "value": "finance"}
    ]
```

### Optional vs Required

```python
# Required parameter - user must provide a value
@param("email", type="email", required=True)

# Optional parameter - user can skip
@param("phone", type="string", required=False)

# Optional with default value
@param("country", type="string", 
    required=False, 
    default_value="US"
)
```

### Label and Help Text

```python
@param("birth_date", type="string",
    label="Date of Birth",           # Display label
    help_text="Format: YYYY-MM-DD",  # Help text under field
    required=True
)
```

### Parameter Ordering

Decorators are applied bottom-to-top, but parameters are reversed for display:

```python
@workflow(name="example")
@param("z", type="string")  # Displayed LAST
@param("y", type="string")  # Displayed SECOND
@param("x", type="string")  # Displayed FIRST
async def example(context, x, y, z):
    pass
```

Form field order: x → y → z

### Complete Parameter Example

```python
@param(
    name="user_email",
    type="email",
    label="User Email Address",
    required=True,
    help_text="Corporate email address (user@company.com)",
    validation={
        "pattern": r"^[^@]+@company\.com$"  # Must use company domain
    }
)
```

## The @data_provider Decorator

Data providers supply dynamic options for form dropdowns.

### Basic Syntax

```python
@data_provider(
    name="get_teams",                    # Unique identifier (required)
    description="Get teams for org",     # Display text (required)
    category="organization",             # Category (optional)
    cache_ttl_seconds=300                # Cache duration (optional)
)
async def get_teams(context: ExecutionContext):
    # Fetch data...
    teams = await fetch_teams(context.org_id)
    
    # Return options list
    return [
        {
            "label": "Engineering",      # Display in dropdown
            "value": "eng",              # Passed to workflow
            "metadata": {                # Optional metadata
                "members": 12,
                "active": True
            }
        },
        # ...
    ]
```

### Required Structure

Data providers must return a list of dicts with `label` and `value`:

```python
[
    {"label": "Display Text", "value": "actual_value"},
    {"label": "Another One", "value": "another_value"},
    # ...
]
```

- **label** (str): Text shown in dropdown
- **value** (str): Value passed to workflow when selected
- **metadata** (dict, optional): Extra info (shown in UI tooltips)

### Caching

Data providers cache results based on `cache_ttl_seconds`:

```python
@data_provider(
    name="get_users",
    description="...",
    cache_ttl_seconds=3600  # Cache for 1 hour
)
async def get_users(context):
    # First call: executes this function
    # Subsequent calls (within 1 hour): returns cached result
    # After 1 hour: cache expires, function runs again
    return [...]
```

When to set cache TTL:
- **Static data** (countries, statuses): 3600 (1 hour) or more
- **Semi-static** (departments, teams): 300 (5 minutes)
- **Dynamic data** (user availability, license count): 30 (30 seconds)
- **Real-time data** (current status): 0 (no caching)

### Data Provider Parameters

Data providers can accept parameters for filtering:

```python
@data_provider(name="get_users_in_department", description="...")
@param("department", type="string", label="Department", required=True)
async def get_users_in_department(context, department):
    users = await fetch_users(context.org_id, department)
    return [
        {"label": u["name"], "value": u["id"]}
        for u in users
    ]
```

Use in workflow:

```python
@param("department", type="string", label="Select Department",
    data_provider="get_departments", required=True)
@param("user", type="string", label="Select User",
    data_provider="get_users_in_department", required=True)
async def assign_user(context, department, user):
    pass
```

### Organization-Scoped Data

Data providers have access to organization context:

```python
@data_provider(name="get_org_teams", description="...")
async def get_org_teams(context: ExecutionContext):
    # Get teams for the current organization
    org_id = context.org_id
    teams = await fetch_teams(org_id)
    
    return [
        {"label": t["name"], "value": t["id"]}
        for t in teams
    ]
```

## Decorator Stacking Order

When using multiple decorators, the order matters:

```python
@workflow(name="my_workflow", description="...")  # Outermost - applied last
@param("third", type="string")                    # Applied third
@param("second", type="string")                   # Applied second
@param("first", type="string")                    # Innermost - applied first
async def my_workflow(context, first, second, third):
    pass
```

Execution order:
1. `@param("first")` decorates the function
2. `@param("second")` decorates the result
3. `@param("third")` decorates that result
4. `@workflow` decorates everything and registers it

The form displays parameters in order: first → second → third

## Common Patterns

### Pattern: Multi-Step Form

```python
@workflow(name="onboard_user")
@param("email", type="email", label="User Email")
@param("first_name", type="string", label="First Name")
@param("last_name", type="string", label="Last Name")
@param("department", type="string", data_provider="get_departments")
@param("team", type="string", data_provider="get_teams")
@param("license", type="string", data_provider="get_licenses")
async def onboard_user(context, email, first_name, last_name, department, team, license):
    pass
```

### Pattern: Dynamic Filtering

```python
@data_provider(name="get_available_actions")
async def get_available_actions(context):
    actions = ["create", "update", "delete"]
    return [{"label": a.title(), "value": a} for a in actions]

@workflow(name="resource_action")
@param("resource_type", type="string", 
    data_provider="get_resource_types")
@param("action", type="string",
    data_provider="get_available_actions")
async def resource_action(context, resource_type, action):
    pass
```

### Pattern: Conditional Parameters

Use validation to make parameters conditionally required:

```python
@workflow(name="conditional_params")
@param("action", type="string", 
    validation={"enum": ["create", "update", "delete"]})
@param("resource_id", type="string",
    help_text="Required for update/delete, ignored for create")
async def conditional_params(context, action, resource_id):
    if action == "create":
        # Create new resource, ignore resource_id
        pass
    else:
        # Update or delete requires resource_id
        if not resource_id:
            return {"error": "resource_id required for this action"}
```

## Best Practices

### Naming Conventions

```python
# Good - Clear, descriptive
@workflow(name="create_m365_user", description="Create new Microsoft 365 user")
@param("email", type="email", label="User Email Address")

# Bad - Vague, unclear
@workflow(name="proc1", description="Process something")
@param("data", type="string", label="Data")
```

### Parameter Validation

```python
# Good - Tight validation
@param("username", type="string",
    validation={
        "min_length": 3,
        "max_length": 20,
        "pattern": r"^[a-zA-Z0-9_]+$"
    }
)

# Bad - No validation
@param("username", type="string")
```

### Help Text

```python
# Good - Clear instructions
@param("date", type="string",
    label="Start Date",
    help_text="Format: YYYY-MM-DD (e.g., 2024-01-15)")

# Bad - Cryptic
@param("date", type="string",
    label="Date")
```

### Data Provider Caching

```python
# Good - Reasonable cache
@data_provider(name="get_departments", cache_ttl_seconds=300)

# Bad - Always fresh (expensive)
@data_provider(name="get_departments", cache_ttl_seconds=0)

# Bad - Stale (never refreshes)
@data_provider(name="get_departments", cache_ttl_seconds=86400)
```

## Troubleshooting

### Decorator not recognized

```
Error: NameError: name 'workflow' is not defined
```

Solution: Import from bifrost

```python
from bifrost import workflow, param  # Correct

# Wrong:
# from shared.decorators import workflow
# from my_module import workflow
```

### Parameters not appearing

1. Verify `@param` comes AFTER `@workflow`
2. Check parameter names match function arguments
3. Verify parameter types are valid

### Validation not working

1. Check validation dict syntax
2. Verify field type matches validation type
3. Test with curl to see actual validation error

### Data provider returning wrong format

Data provider must return list of dicts:

```python
# Correct
return [
    {"label": "Option 1", "value": "opt1"},
    {"label": "Option 2", "value": "opt2"}
]

# Wrong - returns string
return "option1, option2"

# Wrong - missing label or value
return [
    {"name": "Option 1", "id": "opt1"}
]
```

## Next Steps

- Read [Writing Workflows](/docs/guides/workflows/writing-workflows) for comprehensive examples
- Explore [Error Handling](/docs/guides/workflows/error-handling) patterns
- Check [Concepts: Workflows](/docs/concepts/workflows) for deeper understanding
