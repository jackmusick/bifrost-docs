---
title: AI Coding Assistant Guide
description: Comprehensive guide for AI coding assistants to build Bifrost workflows, data providers, and integrations
---

This comprehensive guide teaches AI coding assistants (like Claude Code) how to build production-ready workflows and data providers with the Bifrost SDK. It covers decorator patterns, the execution context API, best practices, and real-world patterns for common integration scenarios.

## Core Concepts

### What is Bifrost?

Bifrost is a workflow automation platform that:
- Discovers workflows via Python decorators (`@workflow`, `@param`, `@data_provider`)
- Executes workflows with a unified `ExecutionContext`
- Provides SDK modules for configuration, secrets, OAuth, files, and more
- Supports scheduled execution, error handling, and state tracking

### Key Design Principles

1. **Decorator-based discovery**: Functions are registered via decorators, not explicit imports
2. **Unified context**: All code receives `ExecutionContext` with user, org, and execution data
3. **Async-first**: All integrations and I/O operations are async
4. **Organization-scoped**: Configuration, secrets, and OAuth are scoped to organizations
5. **Type-safe**: Full type stubs (`bifrost.pyi`) for IDE support

## Decorator System

### @workflow Decorator

Registers an async function as a discoverable workflow.

```python
from bifrost import workflow, param, ExecutionContext

@workflow(
    name="my_workflow",
    description="What this workflow does",
    category="Category Name",
    tags=["tag1", "tag2"],
    execution_mode="sync",      # or "async"
    timeout_seconds=300,
    schedule="0 9 * * *",       # Cron for scheduled execution (optional)
    expose_in_forms=True        # Can be triggered from forms
)
@param("email", "email", required=True)
@param("name", "string", required=True)
async def my_workflow(context: ExecutionContext, email: str, name: str):
    """
    Docstring is optional but recommended.
    """
    context.log("info", "Starting workflow", {"email": email})
    return {"success": True}
```

**Key decorator fields:**

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `name` | str | required | Unique identifier (snake_case, URL-friendly) |
| `description` | str | required | User-facing description shown in UI |
| `category` | str | "General" | Groups workflows in UI |
| `tags` | list | None | Optional filtering/search tags |
| `execution_mode` | str | "sync" | "sync" or "async" (for long-running tasks) |
| `timeout_seconds` | int | 300 | Max execution time |
| `schedule` | str | None | Cron expression (e.g., "0 9 * * 1" = Monday 9 AM UTC) |
| `expose_in_forms` | bool | True | Whether users can trigger manually |

### @param Decorator

Defines a parameter for a workflow or data provider.

```python
@param(
    name="email",                   # Must match function parameter
    type="email",                   # See types below
    label="Email Address",          # Display label (auto-generated if omitted)
    required=True,
    validation={
        "pattern": "^[^@]+@[^@]+$"  # Regex pattern
    },
    data_provider="get_departments",  # Optional: dynamic options
    default_value=None,
    help_text="Enter your email"
)
```

**Valid parameter types:**

```python
"string"        # Text input
"int"           # Integer input
"bool"          # Checkbox
"float"         # Decimal number
"email"         # Email with validation
"date"          # Date picker (YYYY-MM-DD)
"datetime"      # Date + time picker
"json"          # JSON data
"list"          # Array/list
"select"        # Dropdown (single select)
"multi_select"  # Multi-select dropdown
```

**Decorator stacking order** (decorators applied bottom-up):

```python
@workflow(name="example")        # Outermost - declares function as workflow
@param("field1", "string")       # Applied third
@param("field2", "string")       # Applied second
@param("field3", "string")       # Applied first
async def example(context, field1, field2, field3):
    pass
```

Parameters appear in UI in declaration order (field3, field2, field1).

### @data_provider Decorator

Registers a function that provides dynamic options for form fields.

```python
from bifrost import data_provider

@data_provider(
    name="get_active_users",
    description="Get list of active users",
    category="organization",
    cache_ttl_seconds=600         # Cache for 10 minutes
)
@param("department", "string", required=False)  # Data providers can have parameters
async def get_active_users(context: ExecutionContext, department: str = None):
    """
    Must return list of dicts with 'label' and 'value' keys.
    """
    users = await fetch_users_from_api(department)

    return [
        {
            "label": user["name"],
            "value": user["id"],
            "metadata": {
                "email": user["email"],
                "department": user["department"]
            }
        }
        for user in users
    ]
```

**Data provider return format:**

```python
[
    {
        "label": "Display Text",      # Shown in UI
        "value": "actual_value",      # Sent to workflow
        "metadata": {...}             # Optional metadata
    }
]
```

## ExecutionContext API

Every workflow and data provider receives `ExecutionContext` as first parameter.

### Properties

```python
# User identity
context.user_id: str              # ID of user who triggered workflow
context.email: str                # Email of triggering user
context.name: str                 # Display name of triggering user

# Organization scope
context.org_id: str | None        # Organization ID (None for global)
context.org_name: str | None      # Organization name
context.scope: str                # "GLOBAL" or organization ID
context.is_global_scope: bool     # True if scope is "GLOBAL"

# Execution metadata
context.execution_id: str         # Unique execution ID
context.is_platform_admin: bool   # True if user is admin
context.is_function_key: bool     # True if called via API key

# Organization object
context.organization: Organization | None
```

### Configuration Methods

```python
# Get configuration (with secret resolution)
value = context.get_config("api_url", default="https://example.com")

# Check if config exists
if context.has_config("slack_webhook"):
    webhook = context.get_config("slack_webhook")
```

**Important**: Configuration values can be secrets (type="secret_ref"). The context automatically resolves these from Azure Key Vault.

### Secrets and OAuth

```python
# Get a secret from Key Vault (org-scoped)
api_key = await context.get_secret("api_key")

# Get OAuth credentials
creds = await context.get_oauth_connection("microsoft_graph")
auth_header = creds.get_auth_header()  # "Bearer {token}"

# Use in API calls
headers = {"Authorization": auth_header}
response = await client.get("https://graph.microsoft.com/v1.0/me", headers=headers)
```

### State Tracking

```python
# Save checkpoints during execution (for debugging)
context.save_checkpoint("validation_complete", {
    "email": email,
    "is_valid": True
})

# Log information (automatically sanitizes sensitive data)
context.log("info", "User created", {
    "user_id": user["id"],
    "email": email  # Non-sensitive data
})

# Finalize execution (called automatically)
final_state = await context.finalize_execution()
```

## SDK Modules

The Bifrost SDK provides module classes for platform operations:

```python
from bifrost import config, secrets, oauth, files, forms, organizations
from bifrost import workflows, executions, roles
```

### config Module

```python
# Get configuration value
api_url = config.get("api_url", default="https://example.com")

# Set configuration (org-scoped)
config.set("api_url", "https://api.example.com")

# List all configuration
all_config = config.list()

# Delete configuration
config.delete("old_key")
```

**Context**: Config is scoped to organization via ExecutionContext.

### secrets Module

```python
# Get secret from Key Vault
api_key = secrets.get("api_key")

# Set secret
secrets.set("api_key", "secret_value")

# Delete secret
secrets.delete("old_secret")
```

**Scoping**: Secrets are org-scoped: `{org_id}--{key}` in Key Vault.

### oauth Module

```python
# Get OAuth token for provider
token = oauth.get_token("microsoft")

# Set OAuth token
oauth.set_token("microsoft", {
    "access_token": "...",
    "refresh_token": "...",
    "expires_at": 1234567890
})

# List providers with tokens
providers = oauth.list_providers()

# Delete token
oauth.delete_token("microsoft")

# Refresh token
new_token = oauth.refresh_token("microsoft")
```

### files Module

```python
# Write file
files.write("data/users.csv", "id,name\n1,Alice\n")

# Read file
content = files.read("data/users.csv")

# List directory
items = files.list_dir("data/")

# Delete file
files.delete("data/old.csv")
```

### forms Module

```python
# Create form
form = forms.create("My Form", fields=[...])

# Get form
form = forms.get("form_id")

# Update form
forms.update("form_id", name="Updated Name")

# Delete form
forms.delete("form_id")

# Submit form
execution_id = forms.submit("form_id", data={...})
```

### organizations Module

```python
# Get organization
org = organizations.get("org_id")

# List all organizations
orgs = organizations.list()

# Create organization
org = organizations.create("Acme Corp")

# Update organization
organizations.update("org_id", name="New Name")

# Delete organization
organizations.delete("org_id")
```

### workflows Module

```python
# Get workflow metadata
workflow = workflows.get("my_workflow")

# List all workflows
all_workflows = workflows.list()

# Execute workflow
execution_id = workflows.trigger("my_workflow", {"email": "alice@example.com"})

# Get execution status
status = workflows.get_status("execution_id")
```

### executions Module

```python
# List executions
recent = executions.list(limit=10)

# List by workflow
workflow_executions = executions.list(workflow_name="my_workflow")

# Get execution
execution = executions.get("execution_id")

# Delete execution
executions.delete("execution_id")
```

### roles Module

```python
# Get user roles
roles = roles.get_roles("user_id")

# Assign role
roles.assign_role("user_id", "editor")

# Revoke role
roles.revoke_role("user_id", "editor")
```

## Form Integration

Workflows can be triggered from forms. When attached to a form:

1. Parameters map to form fields
2. Data providers populate field options
3. Workflow return value can be HTML or JSON

### Workflow Triggered from Form

```python
@workflow(
    name="process_ticket",
    description="Process customer support ticket",
    expose_in_forms=True  # Can be triggered from form
)
@param("ticket_id", "string", required=True)
@param("priority", "select", required=True, data_provider="get_priorities")
@param("assign_to", "select", required=True, data_provider="get_team_members")
async def process_ticket(context, ticket_id: str, priority: str, assign_to: str):
    # Fetch and process ticket
    ticket = await get_ticket(ticket_id)
    ticket["priority"] = priority
    ticket["assigned_to"] = assign_to

    # Save changes
    await update_ticket(ticket)

    context.log("info", "Ticket processed", {"ticket_id": ticket_id})

    # Can return HTML for display
    return {
        "success": True,
        "ticket_id": ticket_id,
        "html": f"<p>Ticket {ticket_id} processed successfully</p>"
    }
```

### Data Provider for Form Field

```python
@data_provider(
    name="get_priorities",
    description="Get ticket priorities",
    cache_ttl_seconds=3600
)
async def get_priorities(context):
    # Called when form loads
    return [
        {"label": "Low", "value": "low"},
        {"label": "Medium", "value": "medium"},
        {"label": "High", "value": "high"},
        {"label": "Critical", "value": "critical"}
    ]

@data_provider(
    name="get_team_members",
    description="Get available team members",
    cache_ttl_seconds=1800
)
async def get_team_members(context):
    # Called when form loads
    members = await fetch_team_members(context.org_id)
    return [
        {"label": member["name"], "value": member["id"]}
        for member in members
    ]
```

## Common Patterns

### Pattern 1: OAuth Integration

```python
from bifrost import workflow, ExecutionContext
import aiohttp

@workflow(name="sync_github", description="Sync GitHub data")
@param("repo", "string", required=True)
async def sync_github(context: ExecutionContext, repo: str):
    # Get OAuth credentials
    creds = await context.get_oauth_connection("github")

    # Use in API call
    headers = {
        "Authorization": creds.get_auth_header(),
        "Accept": "application/vnd.github.v3+json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://api.github.com/repos/{repo}",
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                context.log("info", "GitHub repo fetched", {"repo": repo})
                return {"success": True, "data": data}
            else:
                error = await response.text()
                context.log("error", "GitHub API error", {"status": response.status})
                raise Exception(f"GitHub API error: {response.status}")
```

### Pattern 2: Configuration with Secret Resolution

```python
from bifrost import workflow, ExecutionContext

@workflow(name="send_email", description="Send email via SMTP")
@param("to", "email", required=True)
@param("subject", "string", required=True)
@param("body", "string", required=True)
async def send_email(context: ExecutionContext, to: str, subject: str, body: str):
    # Configuration can be references to Key Vault
    smtp_host = context.get_config("SMTP_HOST")
    smtp_port = context.get_config("SMTP_PORT", default=587)

    # Get secret from Key Vault
    smtp_password = await context.get_secret("smtp_password")

    # Use in email sending
    import smtplib
    server = smtplib.SMTP(smtp_host, smtp_port)
    server.starttls()
    server.login(smtp_user, smtp_password)
    server.send_message(email_message)
    server.quit()

    context.log("info", "Email sent", {"to": to})
    return {"success": True}
```

### Pattern 3: Error Handling with Checkpoints

```python
from bifrost import workflow, ExecutionContext

@workflow(
    name="multi_step_process",
    description="Process with multiple steps",
    timeout_seconds=600
)
async def multi_step(context: ExecutionContext):
    try:
        # Step 1
        context.save_checkpoint("step1_start", {})
        result1 = await step1()
        context.save_checkpoint("step1_complete", {"result": result1})

        # Step 2
        context.save_checkpoint("step2_start", {})
        result2 = await step2(result1)
        context.save_checkpoint("step2_complete", {"result": result2})

        # Step 3
        context.save_checkpoint("step3_start", {})
        result3 = await step3(result2)
        context.save_checkpoint("step3_complete", {"result": result3})

        context.log("info", "Process completed successfully")
        return {"success": True, "result": result3}

    except Exception as e:
        context.log("error", "Process failed", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise
```

### Pattern 4: Parameterized Data Provider

```python
from bifrost import data_provider, param, ExecutionContext

@data_provider(
    name="get_users_by_role",
    description="Get users filtered by role",
    cache_ttl_seconds=300
)
@param("role", "string", required=True)
@param("limit", "int", required=False, default_value=50)
async def get_users_by_role(context: ExecutionContext, role: str, limit: int = 50):
    """
    Data providers can have parameters!
    Called with inputs from form field configuration.
    """
    users = await fetch_users(role=role, limit=limit)

    return [
        {"label": user["name"], "value": user["id"]}
        for user in users
    ]
```

### Pattern 5: Batch Processing

```python
from bifrost import workflow, ExecutionContext
import asyncio

@workflow(
    name="process_large_dataset",
    description="Process large data in batches",
    execution_mode="async",  # For long-running workflows
    timeout_seconds=3600      # 1 hour max
)
@param("dataset_id", "string", required=True)
async def process_batch(context: ExecutionContext, dataset_id: str):
    batch_size = 50
    processed = 0

    context.log("info", "Starting batch processing", {"dataset_id": dataset_id})

    while True:
        # Fetch batch
        batch = await fetch_batch(dataset_id, offset=processed, limit=batch_size)
        if not batch:
            break

        # Process batch in parallel
        results = await asyncio.gather(
            *[process_item(item) for item in batch]
        )

        # Save results
        await save_results(results)

        processed += len(batch)
        context.save_checkpoint("batch_processed", {"count": processed})
        context.log("info", "Batch processed", {"count": processed})

    context.log("info", "All batches processed", {"total": processed})
    return {"success": True, "total_processed": processed}
```

## Best Practices for AI Code Generation

### 1. Function Naming and Description

**Good:**
```python
@workflow(
    name="create_microsoft_365_user_with_license",
    description="Create a new user in Microsoft 365 and assign license",
    category="User Management"
)
```

**Bad:**
```python
@workflow(
    name="user_proc1",
    description="User processing",
)
```

### 2. Parameter Documentation

**Good:**
```python
@param("email", "email",
       label="Email Address",
       required=True,
       help_text="User's corporate email address")
```

**Bad:**
```python
@param("email", "email")  # Missing label and help text
```

### 3. Error Handling

**Good:**
```python
try:
    result = await api_call()
except ValueError as e:
    context.log("error", "Validation failed", {"error": str(e)})
    raise  # Re-raise for caller to handle
```

**Bad:**
```python
try:
    result = await api_call()
except Exception:
    pass  # Silent failure - unacceptable
```

### 4. Logging Sensitive Data

**Good:**
```python
context.log("info", "User created", {
    "user_id": user["id"],
    "email_domain": email.split("@")[1]  # Only domain, not full email
})
```

**Bad:**
```python
context.log("info", "User created", {
    "email": email,        # PII!
    "password": password,  # Secret!
    "api_key": api_key     # Credential!
})
```

### 5. Async Operations

**Good:**
```python
# Parallel operations
users, groups = await asyncio.gather(
    fetch_users(),
    fetch_groups()
)
```

**Bad:**
```python
# Sequential (slow)
users = await fetch_users()
groups = await fetch_groups()
```

### 6. Checkpoint Placement

**Good:**
```python
context.save_checkpoint("validation_complete", {"email": email})
context.save_checkpoint("api_call_complete", {"status_code": 201})
```

**Bad:**
```python
# No checkpoints - hard to debug failures
```

## Type Safety

Use type hints for IDE support:

```python
from bifrost import workflow, param, ExecutionContext
from typing import Dict, List, Any

@workflow(
    name="typed_example",
    description="Example with full type hints"
)
@param("email", "email", required=True)
async def typed_example(
    context: ExecutionContext,
    email: str
) -> Dict[str, Any]:
    """
    Full type hints enable:
    - IDE autocomplete
    - Type checking
    - Better error messages
    """
    users: List[Dict[str, str]] = await fetch_users()
    filtered: List[Dict[str, str]] = [
        u for u in users if u["email"] == email
    ]

    return {
        "success": True,
        "users": filtered
    }
```

Copy `bifrost.pyi` to your workspace for IDE support.

## Import Rules

Workflows can only import from public API:

**Allowed:**
```python
from bifrost import workflow, param, data_provider, ExecutionContext
from bifrost import config, secrets, oauth, files, workflows
```

**Not allowed:**
```python
from shared.decorators import workflow  # Use bifrost import instead
from shared.storage import TableStorageService  # Private module
```

## Testing Patterns

### Test with Mock Context

```python
from unittest.mock import AsyncMock, MagicMock
import pytest

from my_workflows import my_workflow

@pytest.mark.asyncio
async def test_my_workflow():
    # Create mock context
    context = MagicMock()
    context.user_id = "test_user"
    context.org_id = "test_org"
    context.get_config = MagicMock(return_value="config_value")
    context.log = MagicMock()
    context.save_checkpoint = MagicMock()

    # Execute workflow
    result = await my_workflow(context, "test_param")

    # Assertions
    assert result["success"] is True
    context.log.assert_called()
```

## Security Considerations

- Never hardcode secrets or API keys
- Use `context.get_secret()` for sensitive data
- Never log passwords, tokens, or PII
- Check `context.is_platform_admin` for sensitive operations
- Validate all user inputs
- Use HTTPS for all external API calls
- Set appropriate timeouts

## Debugging

1. **Check logs**: `context.log()` calls appear in execution logs
2. **Use checkpoints**: `context.save_checkpoint()` marks progress
3. **Handle errors**: Always catch and log exceptions
4. **Test locally**: Run tests before deployment
5. **Check configuration**: Ensure all required config exists

## See Also

- [ExecutionContext API](/reference/sdk/context-api/) - Complete context reference
- [Decorators Reference](/reference/sdk/decorators/) - Decorator details
- [Bifrost Module Reference](/reference/sdk/bifrost-module/) - SDK modules
- [Workflow Development Guide](/guides/workflows/) - Detailed tutorials
