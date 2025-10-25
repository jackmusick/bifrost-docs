---
title: Decorators Reference
description: Complete reference for @workflow, @param, and @data_provider decorators
---

Decorators are the foundation of Bifrost's discovery system. They register workflows and data providers automatically when your modules are imported.

## @workflow Decorator

Registers an async function as a discoverable workflow.

### Syntax

```python
@workflow(
    name: str,
    description: str,
    category: str = "General",
    tags: list[str] | None = None,
    execution_mode: Literal["sync", "async"] = "sync",
    timeout_seconds: int = 300,
    retry_policy: dict[str, Any] | None = None,
    schedule: str | None = None,
    endpoint_enabled: bool = False,
    allowed_methods: list[str] | None = None,
    disable_global_key: bool = False,
    public_endpoint: bool = False
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | - | Unique workflow identifier (URL-friendly, lowercase) |
| `description` | str | - | User-facing description |
| `category` | str | "General" | Category for grouping (e.g., "User Management") |
| `tags` | list | None | Tags for filtering and search |
| `execution_mode` | str | "sync" | "sync" or "async" execution |
| `timeout_seconds` | int | 300 | Maximum execution time in seconds |
| `retry_policy` | dict | None | Retry configuration |
| `schedule` | str | None | Cron schedule for scheduled execution |
| `endpoint_enabled` | bool | False | Expose as HTTP endpoint at /api/endpoints/{name} |
| `allowed_methods` | list | None | HTTP methods allowed (GET, POST, etc) |
| `disable_global_key` | bool | False | Require workflow-specific API key |
| `public_endpoint` | bool | False | Skip authentication for webhooks |

### Examples

**Basic workflow:**

```python
@workflow(
    name="send_email",
    description="Send an email to a user"
)
async def send_email(context, recipient: str):
    # Implementation
    pass
```

**Scheduled workflow:**

```python
@workflow(
    name="daily_report",
    description="Generate daily report",
    execution_mode="async",
    schedule="0 9 * * *"  # Every day at 9 AM
)
async def daily_report(context):
    # Implementation
    pass
```

**With retry policy:**

```python
@workflow(
    name="sync_with_external_api",
    description="Sync data with external API",
    retry_policy={
        "max_attempts": 3,
        "backoff_seconds": 5,
        "backoff_multiplier": 2
    }
)
async def sync_with_external_api(context):
    # Implementation
    pass
```

## @param Decorator

Defines a parameter for a workflow or data provider.

### Syntax

```python
@param(
    name: str,
    type: str,
    label: str | None = None,
    required: bool = False,
    validation: dict | None = None,
    data_provider: str | None = None,
    default_value: Any = None,
    help_text: str | None = None
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | - | Parameter name (must match function argument) |
| `type` | str | - | Field type (string, number, boolean, select, etc.) |
| `label` | str | None | Display label (defaults to name) |
| `required` | bool | False | Whether parameter is required |
| `validation` | dict | None | Validation rules (pattern, min, max, etc.) |
| `data_provider` | str | None | Data provider for dynamic options |
| `default_value` | Any | None | Default value if not provided |
| `help_text` | str | None | Help text shown in UI |

### Parameter Types

- **string** - Text input
- **number** - Numeric input
- **boolean** - Checkbox
- **select** - Single-select dropdown
- **multi_select** - Multiple-select dropdown
- **date** - Date picker (YYYY-MM-DD)
- **datetime** - Date and time picker
- **email** - Email validation
- **textarea** - Multi-line text
- **file** - File upload

### Examples

**Required string with validation:**

```python
@param(
    "email",
    "email",
    label="Email Address",
    required=True,
    help_text="Enter a valid email address"
)
```

**Select with data provider:**

```python
@param(
    "department",
    "select",
    label="Department",
    required=True,
    data_provider="get_departments"
)
```

**Number with validation:**

```python
@param(
    "user_count",
    "number",
    label="Number of Users",
    required=True,
    validation={
        "min": 1,
        "max": 1000,
        "step": 1
    }
)
```

**With default value:**

```python
@param(
    "notify_admin",
    "boolean",
    label="Notify Administrator",
    default_value=True
)
```

**Multi-select:**

```python
@param(
    "permissions",
    "multi_select",
    label="Assign Permissions",
    required=True,
    data_provider="get_available_permissions"
)
```

### Validation Rules

Available validation options:

```python
{
    "pattern": "^[a-zA-Z0-9]+$",  # Regex pattern
    "min": 1,                      # Minimum value/length
    "max": 100,                    # Maximum value/length
    "min_length": 3,               # Minimum string length
    "max_length": 50,              # Maximum string length
    "enum": ["value1", "value2"],  # Allowed values
}
```

## @data_provider Decorator

Registers a function that provides dynamic options for form fields.

### Syntax

```python
@data_provider(
    name: str,
    description: str,
    category: str = "General",
    cache_ttl_seconds: int = 300
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | - | Unique provider identifier |
| `description` | str | - | Description of what data it provides |
| `category` | str | "General" | Category for grouping |
| `cache_ttl_seconds` | int | 300 | Cache duration in seconds (0 = no cache) |

### Examples

**Basic data provider:**

```python
@data_provider(
    name="get_active_users",
    description="Get list of active users",
    cache_ttl_seconds=600
)
async def get_active_users(context):
    return [
        {"label": "Alice Smith", "value": "alice@example.com"},
        {"label": "Bob Johnson", "value": "bob@example.com"}
    ]
```

**With parameters:**

```python
@data_provider(
    name="get_users_by_department",
    description="Get users in a specific department",
    cache_ttl_seconds=300
)
@param("department", "string", required=True)
async def get_users_by_department(context, department: str):
    # Filter users by department
    users = await fetch_users_from_api(department)
    return [
        {"label": user["name"], "value": user["id"]}
        for user in users
    ]
```

**With error handling:**

```python
import logging

logger = logging.getLogger(__name__)

@data_provider(
    name="get_api_endpoints",
    description="Get available API endpoints",
    cache_ttl_seconds=900
)
async def get_api_endpoints(context):
    try:
        endpoints = await fetch_endpoints()
        logger.info(f"Fetched {len(endpoints)} endpoints")
        return [
            {"label": ep["name"], "value": ep["id"]}
            for ep in endpoints
        ]
    except Exception as e:
        logger.error(f"Failed to fetch endpoints: {str(e)}")
        return []  # Return empty list on error
```

## Decorator Stacking

Multiple decorators can be stacked. Decorators are applied from bottom to top:

```python
@workflow(name="create_user", description="Create a new user")
@param("email", "email", required=True)      # Applied third
@param("first_name", "string", required=True) # Applied second
@param("last_name", "string", required=True)  # Applied first
async def create_user(context, email: str, first_name: str, last_name: str):
    pass
```

**Important**: Parameters are processed in reverse order (bottom-to-top), so they appear in the correct order in the workflow.

## Return Values

Workflows and data providers must return specific formats:

### Workflow Return

Any JSON-serializable value:

```python
@workflow(name="example")
async def example(context):
    return {
        "success": True,
        "message": "Operation completed",
        "data": [1, 2, 3]
    }
```

### Data Provider Return

A list of objects with `label` and `value`:

```python
@data_provider(name="example")
async def example(context):
    return [
        {"label": "Option 1", "value": "opt1"},
        {"label": "Option 2", "value": "opt2"},
        {"label": "Option 3", "value": "opt3"}
    ]
```

Optional additional metadata:

```python
return [
    {
        "label": "Option 1",
        "value": "opt1",
        "metadata": {
            "description": "First option",
            "icon": "star"
        }
    }
]
```

## Best Practices

✅ **DO:**
- Use descriptive names and descriptions
- Validate all parameters
- Handle errors gracefully
- Log important operations
- Cache data provider results appropriately
- Add help text for complex parameters
- Use type hints in function signatures

❌ **DON'T:**
- Use generic names like "workflow1" or "param1"
- Forget to add descriptions
- Return inconsistent data structures
- Log sensitive data
- Cache dynamic data too long
- Ignore parameter validation
- Create workflows without timeout constraints

## Complete Example

```python
from bifrost import workflow, param, data_provider, ExecutionContext
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Data provider for departments
@data_provider(
    name="get_departments",
    description="Get available departments",
    category="organization",
    cache_ttl_seconds=600
)
async def get_departments(context: ExecutionContext) -> List[Dict[str, str]]:
    """Fetch departments from external system."""
    departments = [
        {"label": "Engineering", "value": "eng"},
        {"label": "Sales", "value": "sales"},
        {"label": "Support", "value": "support"}
    ]
    logger.info(f"Returning {len(departments)} departments")
    return departments

# Workflow using the data provider
@workflow(
    name="create_user",
    description="Create a new user in the system",
    category="user_management",
    tags=["user-creation", "onboarding"],
    timeout_seconds=60
)
@param("email", "email", label="Email", required=True)
@param("name", "string", label="Full Name", required=True)
@param("department", "select", label="Department",
       required=True, data_provider="get_departments")
@param("send_welcome_email", "boolean",
       label="Send Welcome Email", default_value=True)
async def create_user(
    context: ExecutionContext,
    email: str,
    name: str,
    department: str,
    send_welcome_email: bool = True
) -> Dict[str, Any]:
    """Create a new user with validation and notifications."""

    logger.info("Creating user", extra={
        "email": email,
        "name": name,
        "department": department
    })

    # Validate input
    if not email.endswith("@example.com"):
        raise ValueError("Email must use example.com domain")

    # Create user
    user_id = await create_user_in_system(email, name, department)

    # Send welcome email if requested
    if send_welcome_email:
        await send_welcome_email_to_user(email, name)

    logger.info("User created successfully", extra={
        "user_id": user_id,
        "email": email
    })

    return {
        "success": True,
        "user_id": user_id,
        "email": email,
        "name": name,
        "department": department
    }
```

## See Also

- [Workflow Development Guide](/guides/workflows/writing-workflows/)
- [Context API Reference](/reference/sdk/context-api/)
- [Platform Architecture](/reference/architecture/overview/)
- [Discovery System](/concepts/discovery-system/)
