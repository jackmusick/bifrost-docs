---
title: Bifrost Module Reference
description: Complete API reference for the bifrost module and all exported functions, classes, and decorators
---

The Bifrost SDK is organized into decorators, context objects, SDK modules, and type definitions. This document provides a complete reference for all public APIs.

## Import Structure

```python
# Core decorators and context
from bifrost import workflow, param, data_provider, ExecutionContext

# SDK modules
from bifrost import (
    config, secrets, oauth, files, forms,
    organizations, workflows, executions, roles
)

# Type definitions
from bifrost import (
    Organization, Caller, OAuthCredentials,
    ExecutionStatus, ConfigType, FormFieldType, IntegrationType
)
```

## Decorators

### @workflow Decorator

```python
def workflow(
    name: str,
    description: str,
    category: str = "General",
    tags: list[str] | None = None,
    execution_mode: str = "sync",
    timeout_seconds: int = 300,
    max_duration_seconds: int = 300,
    retry_policy: dict[str, Any] | None = None,
    schedule: str | None = None,
    requires_org: bool = True,
    expose_in_forms: bool = True,
    requires_approval: bool = False,
    required_permission: str = "canExecuteWorkflows"
) -> Callable
```

Registers an async function as a discoverable workflow.

**Parameters:**

- `name` (str, required): Unique workflow identifier (snake_case, URL-friendly)
- `description` (str, required): User-facing description for UI
- `category` (str): Category for grouping workflows (default: "General")
- `tags` (list[str]): Optional tags for filtering/search
- `execution_mode` (str): "sync" for immediate, "async" for long-running (default: "sync")
- `timeout_seconds` (int): Maximum execution time in seconds (default: 300)
- `max_duration_seconds` (int): Additional max duration parameter (default: 300)
- `retry_policy` (dict): Retry configuration, e.g. `{"max_attempts": 3, "backoff_seconds": 5}`
- `schedule` (str): Cron expression for scheduled execution (e.g., "0 9 * * 1" = Monday 9 AM UTC)
- `requires_org` (bool): Whether workflow requires organization context (default: True)
- `expose_in_forms` (bool): Whether workflow can be triggered from forms (default: True)
- `requires_approval` (bool): Whether execution requires approval (default: False)
- `required_permission` (str): Permission required to execute (default: "canExecuteWorkflows")

**Returns:** Decorated function (unchanged for normal Python execution)

**Example:**

```python
@workflow(
    name="create_user",
    description="Create a new user in the system",
    category="User Management",
    tags=["users", "onboarding"],
    timeout_seconds=60
)
@param("email", "email", required=True)
@param("name", "string", required=True)
async def create_user(context: ExecutionContext, email: str, name: str):
    return {"success": True, "user_id": "123"}
```

### @param Decorator

```python
def param(
    name: str,
    type: str,
    label: str | None = None,
    required: bool = False,
    validation: dict[str, Any] | None = None,
    data_provider: str | None = None,
    default_value: Any = None,
    help_text: str | None = None
) -> Callable
```

Defines a parameter for a workflow or data provider.

**Parameters:**

- `name` (str, required): Parameter name (must match function argument)
- `type` (str, required): Parameter type (see supported types below)
- `label` (str): Display label in UI (defaults to title case of name)
- `required` (bool): Whether parameter is required (default: False)
- `validation` (dict): Validation rules:
  - `pattern`: Regex pattern (e.g., `r"^[a-zA-Z0-9]+$"`)
  - `min`: Minimum value/length
  - `max`: Maximum value/length
  - `min_length`: Minimum string length
  - `max_length`: Maximum string length
  - `enum`: List of allowed values
  - `step`: Step size for numbers
- `data_provider` (str): Name of data provider for dynamic options
- `default_value` (Any): Default value if not provided
- `help_text` (str): Help text shown in UI tooltip

**Supported Types:**

- `"string"` - Text input
- `"int"` - Integer input
- `"float"` - Decimal number
- `"bool"` - Checkbox (boolean)
- `"email"` - Email with validation
- `"date"` - Date picker (YYYY-MM-DD format)
- `"datetime"` - Date and time picker
- `"json"` - JSON data
- `"list"` - Array/list
- `"select"` - Single-select dropdown
- `"multi_select"` - Multiple-select dropdown

**Example:**

```python
@param(
    "email",
    "email",
    label="Email Address",
    required=True,
    validation={"pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"},
    help_text="Enter your corporate email address"
)
@param(
    "department",
    "select",
    required=True,
    data_provider="get_departments",
    label="Department"
)
@param(
    "count",
    "int",
    required=False,
    default_value=10,
    validation={"min": 1, "max": 1000}
)
```

### @data_provider Decorator

```python
def data_provider(
    name: str,
    description: str,
    category: str = "General",
    cache_ttl_seconds: int = 300
) -> Callable
```

Registers a function that provides dynamic options for form fields.

**Parameters:**

- `name` (str, required): Unique data provider identifier (snake_case)
- `description` (str, required): Description of what data it provides
- `category` (str): Category for grouping (default: "General")
- `cache_ttl_seconds` (int): Cache duration in seconds (default: 300, use 0 for no cache)

**Returns:** Decorated function (unchanged for normal Python execution)

**Return Format:** Must return a list of dictionaries with this structure:

```python
[
    {
        "label": "Display Text",          # Shown in UI dropdown
        "value": "actual_value",          # Sent to workflow
        "metadata": {                     # Optional metadata
            "description": "Extra info",
            "icon": "star"
        }
    },
    # ... more options
]
```

**Example:**

```python
@data_provider(
    name="get_departments",
    description="Get list of departments",
    category="organization",
    cache_ttl_seconds=600
)
async def get_departments(context: ExecutionContext) -> list[dict]:
    """Called to populate dropdown options."""
    departments = [
        {"label": "Engineering", "value": "eng"},
        {"label": "Sales", "value": "sales"},
        {"label": "Support", "value": "support"}
    ]
    return departments

@data_provider(
    name="get_users_by_dept",
    description="Get users in a specific department",
    category="organization",
    cache_ttl_seconds=300
)
@param("department", "string", required=True)
async def get_users_by_dept(context: ExecutionContext, department: str) -> list[dict]:
    """Data providers can have parameters too!"""
    users = await fetch_users_by_department(department)
    return [
        {
            "label": user["name"],
            "value": user["id"],
            "metadata": {"email": user["email"]}
        }
        for user in users
    ]
```

## ExecutionContext

```python
class ExecutionContext:
    """Context object passed to all workflows and data providers."""

    # Properties
    user_id: str                      # ID of user who triggered workflow
    email: str                        # Email of triggering user
    name: str                         # Display name of triggering user
    scope: str                        # "GLOBAL" or organization ID
    organization: Organization | None # Organization object
    is_platform_admin: bool           # True if user is admin
    is_function_key: bool             # True if called via API key
    execution_id: str                 # Unique execution ID

    # Properties (derived)
    @property
    def org_id(self) -> str | None:
        """Organization ID (None for platform admins in global scope)."""

    @property
    def org_name(self) -> str | None:
        """Organization display name."""

    @property
    def is_global_scope(self) -> bool:
        """True if executing in GLOBAL scope (no organization)."""

    # Backwards compatibility properties
    @property
    def executed_by(self) -> str:
        """Alias for user_id."""

    @property
    def executed_by_email(self) -> str:
        """Alias for email."""

    @property
    def executed_by_name(self) -> str:
        """Alias for name."""
```

### Methods

#### Logging

```python
def log(level: str, message: str, data: dict[str, Any] | None = None) -> None
```

Log a message with context. Data is automatically sanitized to remove sensitive information.

**Log Levels:** `"debug"`, `"info"`, `"warning"`, `"error"`

**Example:**

```python
context.log("info", "User created successfully", {
    "user_id": user["id"],
    "email_domain": email.split("@")[1]
})

context.log("error", "API call failed", {
    "endpoint": "/users",
    "status_code": 500
})
```

#### Configuration

```python
def get_config(key: str, default: Any = None) -> Any
```

Get configuration value with automatic secret resolution. Configuration values can reference Azure Key Vault secrets using `secret_ref` type.

```python
def has_config(key: str) -> bool
```

Check if configuration key exists.

**Example:**

```python
api_url = context.get_config("api_url", default="https://api.example.com")
if context.has_config("slack_webhook"):
    webhook_url = context.get_config("slack_webhook")
```

#### Secrets and OAuth

```python
async def get_secret(key: str) -> str
```

Get a secret from Azure Key Vault. Secrets are organization-scoped: `{org_id}--{key}`.

```python
async def get_oauth_connection(connection_name: str) -> OAuthCredentials
```

Get OAuth credentials for a connection. Automatically handles token refresh.

**Example:**

```python
# Get secret
api_key = await context.get_secret("github_api_key")

# Get OAuth credentials
creds = await context.get_oauth_connection("microsoft_graph")
auth_header = creds.get_auth_header()  # "Bearer {token}"

# Use in API call
headers = {"Authorization": auth_header}
response = await session.get("https://graph.microsoft.com/v1.0/me", headers=headers)
```

#### State Tracking

```python
def save_checkpoint(name: str, data: dict[str, Any]) -> None
```

Save a state checkpoint during workflow execution. Checkpoints appear in execution logs and help debug issues.

```python
async def finalize_execution() -> dict[str, Any]
```

Get final execution state for persistence. Called automatically at workflow completion.

**Example:**

```python
context.save_checkpoint("validation_complete", {
    "email": email,
    "is_valid": True
})

context.save_checkpoint("api_call_complete", {
    "status_code": 201,
    "user_id": user["id"]
})
```

## SDK Modules

### config Module

Configuration management with organization scope.

```python
def get(key: str, default: Any = None) -> Any
```

Get configuration value. Automatically resolves secrets from Key Vault if configured as secret_ref.

```python
def set(key: str, value: Any) -> None
```

Set configuration value.

```python
def list() -> list[dict[str, Any]]
```

List all configuration values.

```python
def delete(key: str) -> None
```

Delete configuration value.

**Example:**

```python
from bifrost import config

# Get config
api_url = config.get("api_url", default="https://example.com")

# Set config
config.set("api_url", "https://api.example.com")

# List all
all_config = config.list()

# Delete
config.delete("old_key")
```

### secrets Module

Azure Key Vault secret management.

```python
def get(key: str) -> str
```

Get secret from Key Vault. Secrets are organization-scoped: `{org_id}--{key}`.

```python
def set(key: str, value: str) -> None
```

Set secret in Key Vault.

```python
def delete(key: str) -> None
```

Delete secret from Key Vault.

**Example:**

```python
from bifrost import secrets

# Get secret
api_key = secrets.get("api_key")

# Set secret
secrets.set("api_key", "secret_value")

# Delete
secrets.delete("old_secret")
```

### oauth Module

OAuth connection management.

```python
def get_connection(connection_name: str) -> OAuthCredentials
```

Get OAuth credentials for a connection.

```python
def create_connection(name: str, provider: str, scopes: list[str]) -> dict
```

Create a new OAuth connection.

```python
def delete_connection(connection_name: str) -> None
```

Delete an OAuth connection.

**Example:**

```python
from bifrost import oauth

# Get credentials
creds = oauth.get_connection("github")

# Create connection
oauth.create_connection("my_github", "github", ["repo", "user"])

# Delete connection
oauth.delete_connection("my_github")
```

### files Module

File operations.

```python
def write(path: str, content: str | bytes) -> None
```

Write file content.

```python
def read(path: str) -> str | bytes
```

Read file content.

```python
def list_dir(path: str) -> list[str]
```

List directory contents.

```python
def delete(path: str) -> None
```

Delete file.

**Example:**

```python
from bifrost import files

# Write file
files.write("data/users.csv", "id,name\n1,Alice\n")

# Read file
content = files.read("data/users.csv")

# List directory
items = files.list_dir("data/")

# Delete
files.delete("data/old.csv")
```

### forms Module

Form management.

```python
def create(name: str, fields: list[dict]) -> dict
```

Create a new form.

```python
def get(form_id: str) -> dict
```

Get form by ID.

```python
def update(form_id: str, **kwargs) -> dict
```

Update form.

```python
def delete(form_id: str) -> None
```

Delete form.

```python
def submit(form_id: str, data: dict) -> str
```

Submit form data (returns execution_id).

**Example:**

```python
from bifrost import forms

# Create form
form = forms.create("User Onboarding", fields=[...])

# Get form
form = forms.get("form_id")

# Update form
forms.update("form_id", name="Updated Name")

# Submit form
execution_id = forms.submit("form_id", data={"email": "alice@example.com"})

# Delete form
forms.delete("form_id")
```

### organizations Module

Organization management.

```python
def get(org_id: str) -> dict
```

Get organization by ID.

```python
def list() -> list[dict]
```

List all organizations.

```python
def create(name: str) -> dict
```

Create new organization.

```python
def update(org_id: str, **kwargs) -> dict
```

Update organization.

```python
def delete(org_id: str) -> None
```

Delete organization.

**Example:**

```python
from bifrost import organizations

# Get org
org = organizations.get("org_id")

# List all
orgs = organizations.list()

# Create
org = organizations.create("Acme Corp")

# Update
organizations.update("org_id", name="New Name")

# Delete
organizations.delete("org_id")
```

### workflows Module

Workflow management and execution.

```python
def get(workflow_name: str) -> dict
```

Get workflow metadata.

```python
def list() -> list[dict]
```

List all workflows.

```python
def trigger(workflow_name: str, parameters: dict) -> str
```

Execute workflow (returns execution_id).

```python
def get_status(execution_id: str) -> str
```

Get execution status.

**Example:**

```python
from bifrost import workflows

# Get workflow
workflow = workflows.get("my_workflow")

# List all
all_workflows = workflows.list()

# Execute workflow
execution_id = workflows.trigger("my_workflow", {"email": "alice@example.com"})

# Get status
status = workflows.get_status(execution_id)
```

### executions Module

Execution history and management.

```python
def list(workflow_name: str | None = None, status: str | None = None, limit: int = 50) -> list[dict]
```

List executions with optional filtering.

```python
def get(execution_id: str) -> dict
```

Get execution details.

```python
def delete(execution_id: str) -> None
```

Delete execution record.

**Example:**

```python
from bifrost import executions

# List recent executions
recent = executions.list(limit=10)

# List by workflow
workflow_executions = executions.list(workflow_name="my_workflow")

# Get execution
execution = executions.get("execution_id")

# Delete
executions.delete("execution_id")
```

### roles Module

Role and permission management.

```python
def get_roles(user_id: str) -> list[str]
```

Get user's roles.

```python
def assign_role(user_id: str, role: str) -> None
```

Assign role to user.

```python
def revoke_role(user_id: str, role: str) -> None
```

Remove role from user.

**Example:**

```python
from bifrost import roles

# Get roles
user_roles = roles.get_roles("user_id")

# Assign role
roles.assign_role("user_id", "editor")

# Revoke role
roles.revoke_role("user_id", "editor")
```

## Type Definitions

### Organization

```python
@dataclass
class Organization:
    """Organization entity."""
    id: str                # Organization ID
    name: str              # Display name
    is_active: bool        # Whether active
```

### Caller

```python
@dataclass
class Caller:
    """User who triggered the workflow execution."""
    user_id: str           # User ID
    email: str             # Email address
    name: str              # Display name
```

### OAuthCredentials

```python
class OAuthCredentials:
    """OAuth credentials for API access."""

    connection_name: str
    access_token: str
    token_type: str
    expires_at: datetime
    refresh_token: str | None
    scopes: str

    def is_expired(self) -> bool:
        """Check if access token is expired."""

    def get_auth_header(self) -> str:
        """Get Authorization header value (e.g., 'Bearer token...')."""
```

### Enums

```python
class ExecutionStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCESS = "Success"
    COMPLETED_WITH_ERRORS = "CompletedWithErrors"
    FAILED = "Failed"

class ConfigType(str, Enum):
    """Configuration value types."""
    STRING = "string"
    SECRET_REF = "secret_ref"
    JSON = "json"

class FormFieldType(str, Enum):
    """Form field types."""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    DATE = "date"
    DATETIME = "datetime"

class IntegrationType(str, Enum):
    """Integration provider types."""
    MSGRAPH = "msgraph"
    HALOPSA = "halopsa"
    OAUTH = "oauth"
```

## Complete Example

```python
from bifrost import (
    workflow, param, data_provider, ExecutionContext,
    config, secrets, oauth
)
from typing import Dict, List, Any
import aiohttp

# Data provider
@data_provider(
    name="get_departments",
    description="Get available departments",
    cache_ttl_seconds=600
)
async def get_departments(context: ExecutionContext) -> List[Dict[str, str]]:
    """Fetch departments from external system."""
    return [
        {"label": "Engineering", "value": "eng"},
        {"label": "Sales", "value": "sales"},
        {"label": "Support", "value": "support"}
    ]

# Workflow using data provider
@workflow(
    name="create_user",
    description="Create a new user in the system",
    category="User Management",
    timeout_seconds=60
)
@param("email", "email", required=True, label="Email Address")
@param("name", "string", required=True, label="Full Name")
@param("department", "select", required=True, data_provider="get_departments")
async def create_user(
    context: ExecutionContext,
    email: str,
    name: str,
    department: str
) -> Dict[str, Any]:
    """Create a new user with validation and API integration."""

    # Log execution start
    context.log("info", "Creating user", {
        "email": email,
        "department": department
    })

    try:
        # Get configuration and secrets
        api_url = context.get_config("api_url", default="https://api.example.com")
        api_key = await context.get_secret("api_key")

        # Get OAuth credentials if needed
        creds = await context.get_oauth_connection("oauth_provider")

        # Make API call
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            payload = {
                "email": email,
                "name": name,
                "department": department
            }

            context.save_checkpoint("api_call_start", {
                "endpoint": "/users",
                "email": email
            })

            async with session.post(
                f"{api_url}/users",
                json=payload,
                headers=headers
            ) as response:
                if response.status == 201:
                    user = await response.json()
                    context.log("info", "User created successfully", {
                        "user_id": user["id"]
                    })
                    return {
                        "success": True,
                        "user_id": user["id"],
                        "email": email
                    }
                else:
                    error = await response.text()
                    context.log("error", "API error", {
                        "status": response.status
                    })
                    raise Exception(f"API error: {response.status}")

    except Exception as e:
        context.log("error", "User creation failed", {
            "error": str(e),
            "email": email
        })
        raise
```

## Best Practices

1. **Use type hints**: Full type hints enable IDE autocomplete and error detection
2. **Add documentation**: Use docstrings to describe workflows and data providers
3. **Validate inputs**: Validate all parameters before using them
4. **Handle errors**: Always catch and log exceptions
5. **Never log secrets**: Use `context.log()` safely without PII or credentials
6. **Use checkpoints**: Mark progress through multi-step workflows
7. **Cache appropriately**: Set `cache_ttl_seconds` based on data freshness needs
8. **Make it async**: Use async/await for I/O operations
9. **Test locally**: Run tests before deployment
10. **Use decorators correctly**: Remember decorators are applied bottom-to-top

## See Also

- [AI Coding Assistant Guide](/reference/sdk/claude/) - Detailed guide for AI code generation
- [ExecutionContext API](/reference/sdk/context-api/) - Full context reference
- [Decorators Reference](/reference/sdk/decorators/) - Decorator parameter details
- [Workflow Development Guide](/guides/workflows/) - Tutorial and examples
