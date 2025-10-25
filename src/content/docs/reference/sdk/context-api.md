---
title: ExecutionContext API
description: Complete reference for the ExecutionContext object passed to workflows
---

The `ExecutionContext` object provides access to organization data, user information, secrets, configuration, and execution state. Every workflow receives this object as its first parameter.

## Properties

### Organization Properties

```python
context.org_id: str
```
The ID of the organization executing the workflow. None for global scope.

```python
context.org_name: str
```
The display name of the organization.

### User Properties

```python
context.user_id: str
```
The ID of the user who triggered the workflow.

```python
context.email: str
```
The email address of the user who triggered the workflow.

```python
context.name: str
```
The display name of the user who triggered the workflow.

### Execution Properties

```python
context.execution_id: str
```
Unique identifier for this workflow execution. Useful for logging and tracking.

```python
context.scope: str
```
The scope of the execution (typically the organization ID or "GLOBAL").

```python
context.is_platform_admin: bool
```
Whether the user is a platform administrator.

```python
context.is_function_key: bool
```
Whether the request was authenticated via function key (vs user authentication).

## Methods

### Logging

Use Python's built-in logging module for logging in workflows:

```python
import logging

logger = logging.getLogger(__name__)
```

**Example:**

```python
import logging

logger = logging.getLogger(__name__)

# Log with context information
logger.info("User creation started", extra={
    "email": "alice@example.com",
    "department": "engineering",
    "org_id": context.org_id
})

logger.error("API call failed", extra={
    "endpoint": "/users",
    "status_code": 500,
    "org_id": context.org_id
})
```

**Important**: Never log sensitive data like passwords, API keys, or tokens.

### Configuration

```python
context.get_config(key: str, default: Any = None) -> Any
```

Get configuration value with automatic secret resolution.

Configuration values can reference secrets using the `secret_ref` pattern:

```python
# Get a simple config value
api_base_url = context.get_config("api_base_url")

# Get a secret (stored as {org_id}--secret_name in Key Vault)
api_key = context.get_config("api_key_ref")

# Get with default value
timeout = context.get_config("timeout", default=30)
```

```python
context.has_config(key: str) -> bool
```

Check if configuration key exists.

```python
if context.has_config("slack_webhook_url"):
    slack_url = context.get_config("slack_webhook_url")
```

### Secrets and Credentials

```python
async def get_secret(key: str) -> str
```

Get a secret from Azure Key Vault. Secrets are org-scoped: `{org_id}--{key}`.

```python
# Get API key from Key Vault
api_key = await context.get_secret("github_api_key")

# Key Vault retrieves: {org_id}--github_api_key
```

```python
async def get_oauth_connection(connection_name: str) -> OAuthCredentials
```

Get OAuth credentials for a connection. Automatically handles token refresh.

```python
# Get Microsoft Graph OAuth credentials
graph_creds = await context.get_oauth_connection("microsoft_graph")
auth_header = graph_creds.get_auth_header()  # "Bearer {access_token}"

# Use in API call
headers = {"Authorization": auth_header}
response = await client.get("https://graph.microsoft.com/v1.0/me", headers=headers)
```

### State Tracking

```python
context.save_checkpoint(name: str, data: dict[str, Any]) -> None
```

Save a state checkpoint during workflow execution. Useful for debugging and understanding execution flow.

```python
# Track progress through different steps
context.save_checkpoint("validation_complete", {
    "email": email,
    "status": "valid"
})

context.save_checkpoint("api_call_complete", {
    "status_code": 201,
    "user_id": "123"
})

context.save_checkpoint("notification_sent", {
    "recipient": email,
    "timestamp": datetime.now().isoformat()
})
```

Checkpoints appear in execution logs and help debug issues.

```python
async def finalize_execution() -> dict[str, Any]
```

Get final execution state for persistence. Called automatically at workflow completion.

## Usage Examples

### Basic Workflow

```python
import logging

logger = logging.getLogger(__name__)

@workflow(name="example")
async def example(context: ExecutionContext):
    # Access user and organization
    logger.info("Executing workflow", extra={
        "user_id": context.user_id,
        "org_id": context.org_id
    })

    # Get configuration
    api_base_url = context.get_config("api_base_url")

    # Get secret
    api_key = await context.get_secret("api_key")

    # Use in API call
    headers = {"Authorization": f"Bearer {api_key}"}

    return {
        "success": True,
        "executed_by": context.user_id,
        "organization": context.org_id
    }
```

### With Checkpoints

```python
@workflow(name="multi_step_workflow")
async def multi_step(context: ExecutionContext):
    # Step 1: Fetch data
    context.save_checkpoint("step_1_start", {})
    data = await fetch_data()
    context.save_checkpoint("step_1_complete", {
        "records": len(data)
    })

    # Step 2: Transform data
    context.save_checkpoint("step_2_start", {})
    transformed = transform_data(data)
    context.save_checkpoint("step_2_complete", {
        "records": len(transformed)
    })

    # Step 3: Upload results
    context.save_checkpoint("step_3_start", {})
    result = await upload_results(transformed)
    context.save_checkpoint("step_3_complete", {
        "upload_id": result["id"]
    })

    return {"success": True}
```

### Error Handling with Context

```python
import logging

logger = logging.getLogger(__name__)

@workflow(name="resilient_workflow")
async def resilient(context: ExecutionContext):
    try:
        logger.info("Starting operation")
        result = await risky_operation()
        logger.info("Operation succeeded")
        return result

    except ValueError as e:
        logger.warning("Invalid input", extra={
            "error": str(e),
            "user": context.user_id
        })
        raise

    except Exception as e:
        logger.error("Operation failed", extra={
            "error": str(e),
            "error_type": type(e).__name__,
            "user": context.user_id,
            "org": context.org_id
        })
        raise
```

### OAuth Integration

```python
import logging

logger = logging.getLogger(__name__)

@workflow(name="sync_with_graph")
async def sync_with_graph(context: ExecutionContext):
    try:
        # Get OAuth credentials
        creds = await context.get_oauth_connection("microsoft_graph")

        # Check if credentials are valid
        if creds.is_expired():
            logger.warning("OAuth token expired, refreshing")
            # Token refresh happens automatically

        # Use in API call
        headers = {"Authorization": creds.get_auth_header()}

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://graph.microsoft.com/v1.0/me",
                headers=headers
            ) as response:
                user = await response.json()

        logger.info("Retrieved user from Graph", extra={
            "user_id": user["id"]
        })

        return {"success": True, "user": user}

    except Exception as e:
        logger.error("Graph sync failed", extra={"error": str(e)})
        raise
```

## Type Annotations

Use the ExecutionContext type hint for IDE autocomplete:

```python
from bifrost import workflow, ExecutionContext

@workflow(name="typed_example")
async def typed_example(context: ExecutionContext, param: str):
    # IDE will autocomplete context methods
    context.get_config(...)
    await context.get_secret(...)
    await context.get_oauth_connection(...)
```

## Security Considerations

**✅ DO:**
- Log only non-sensitive data
- Use `context.get_secret()` for passwords and tokens
- Store organization-scoped secrets
- Check `context.org_id` for authorization
- Use `context.is_platform_admin` for admin checks

**❌ DON'T:**
- Log secrets, tokens, or credentials
- Hardcode sensitive values
- Log PII (personally identifiable information)
- Bypass organization checks
- Access data from other organizations

## Backwards Compatibility

For backwards compatibility, the context also provides:

```python
context.executed_by: str           # Alias for context.user_id
context.executed_by_email: str     # Alias for context.email
context.executed_by_name: str      # Alias for context.name
context.is_global_scope: bool      # True if no organization
```

## Complete Example

```python
from bifrost import workflow, param, ExecutionContext
from datetime import datetime
import aiohttp
import logging

logger = logging.getLogger(__name__)

@workflow(
    name="comprehensive_example",
    description="Demonstrates all context features"
)
@param("email", "email", required=True)
async def comprehensive(context: ExecutionContext, email: str):
    """Complete example using all context features."""

    # Log execution start
    logger.info("Starting comprehensive workflow", extra={
        "user_id": context.user_id,
        "email_param": email,
        "organization": context.org_id,
        "execution_id": context.execution_id
    })

    try:
        # Step 1: Validate configuration
        context.save_checkpoint("step_1_validate_config", {})

        if not context.has_config("api_base_url"):
            raise ValueError("Missing required configuration: api_base_url")

        api_base_url = context.get_config("api_base_url")
        logger.info("Configuration validated", extra={
            "api_base_url": api_base_url
        })

        # Step 2: Get credentials
        context.save_checkpoint("step_2_get_credentials", {})

        api_key = await context.get_secret("api_key")
        headers = {"Authorization": f"Bearer {api_key}"}

        logger.info("Credentials retrieved")

        # Step 3: Make API call
        context.save_checkpoint("step_3_api_call", {})

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_base_url}/users",
                json={"email": email},
                headers=headers
            ) as response:
                if response.status == 201:
                    user = await response.json()
                    user_id = user["id"]
                else:
                    error = await response.text()
                    raise Exception(f"API error: {response.status} - {error}")

        logger.info("User created via API", extra={
            "user_id": user_id,
            "email": email
        })

        # Step 4: Complete
        context.save_checkpoint("step_4_complete", {
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        })

        return {
            "success": True,
            "user_id": user_id,
            "email": email,
            "created_by": context.user_id
        }

    except Exception as e:
        logger.error("Workflow failed", extra={
            "error": str(e),
            "error_type": type(e).__name__,
            "email_param": email
        })
        raise
```

## See Also

- [Workflow Development Guide](/guides/workflows/writing-workflows/)
- [Decorators Reference](/reference/sdk/decorators/)
- [Secrets Management](/guides/integrations/secrets-management/)
