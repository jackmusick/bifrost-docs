---
title: Build Your First Workflow
description: Step-by-step tutorial for creating your first Bifrost workflow with decorators, testing, and debugging
---

## Introduction

In this tutorial, we'll build a complete workflow from scratch, starting with the simplest example and progressively adding complexity. By the end, you'll understand how to:

- Define workflows with the `@workflow` decorator
- Add parameters with validation using `@param`
- Access the execution context
- Log and debug workflow execution
- Test workflows locally
- Save checkpoints for state tracking

Let's get started!

## Prerequisites

- Python 3.11 or higher
- Basic understanding of async/await patterns
- A text editor or IDE (VS Code recommended)
- Access to a Bifrost deployment or local development environment

## Part 1: Your First Workflow (5 minutes)

### Step 1: Create the Workflow File

Create a new file named `hello_world.py` in your workflows directory:

```python
from bifrost import workflow, param, ExecutionContext

@workflow(
    name="hello_world",
    description="A simple greeting workflow",
    category="Examples"
)
@param("name", type="string", label="Your Name", required=True)
async def hello_world(context: ExecutionContext, name: str):
    """Generate a personalized greeting."""

    # Log the execution
    context.log("info", f"Generating greeting for {name}")

    # Create the greeting
    greeting = f"Hello, {name}! Welcome to Bifrost."

    # Return the result
    return {"greeting": greeting, "name": name}
```

### Step 2: Test via Web Interface

1. Open the Bifrost web interface (http://localhost:5173 for local development)
2. Navigate to **Workflows** → **Examples**
3. Find "Hello World" in the list
4. Click **Execute**
5. Enter your name in the form
6. Click **Run Workflow**

You'll see:
- The greeting message in the result
- Execution metadata (duration, execution ID)
- Your name echoed back

**Expected Output:**
```json
{
  "greeting": "Hello, Alice! Welcome to Bifrost.",
  "name": "Alice"
}
```

### Step 3: Test via API

From your terminal, test the workflow using curl:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org" \
  -H "x-functions-key: test" \
  -d '{"name": "Alice"}' \
  http://localhost:7071/api/workflows/hello_world
```

**Response:**
```json
{
  "executionId": "exec-12345",
  "status": "Success",
  "result": {
    "greeting": "Hello, Alice! Welcome to Bifrost.",
    "name": "Alice"
  },
  "durationMs": 45
}
```

## Part 2: Adding Parameters & Validation

Now let's create a workflow that validates user input:

```python
from bifrost import workflow, param, ExecutionContext

@workflow(
    name="validate_email",
    description="Validate and process an email address",
    category="Examples"
)
@param(
    name="email",
    type="email",
    label="Email Address",
    required=True,
    help_text="Enter a valid email address"
)
@param(
    name="domain",
    type="string",
    label="Expected Domain",
    required=False,
    default_value="example.com",
    help_text="Optional: Domain email must belong to"
)
async def validate_email(context: ExecutionContext, email: str, domain: str = "example.com"):
    """Validate email address against domain."""

    context.log("info", f"Validating email: {email} against domain: {domain}")

    # Extract domain from email
    email_domain = email.split("@")[1] if "@" in email else None

    # Check if domain matches
    domain_match = email_domain == domain if email_domain else False

    return {
        "email": email,
        "domain_expected": domain,
        "domain_actual": email_domain,
        "valid": domain_match,
        "message": "Domain matches!" if domain_match else f"Domain mismatch: got {email_domain}, expected {domain}"
    }
```

### Testing Validation

**Test 1: Matching Domain**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-functions-key: test" \
  -d '{"email": "user@example.com", "domain": "example.com"}' \
  http://localhost:7071/api/workflows/validate_email
```

**Test 2: Mismatched Domain**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-functions-key: test" \
  -d '{"email": "user@company.com", "domain": "example.com"}' \
  http://localhost:7071/api/workflows/validate_email
```

**Test 3: Invalid Email (should be rejected by email validation)**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-functions-key: test" \
  -d '{"email": "not-an-email", "domain": "example.com"}' \
  http://localhost:7071/api/workflows/validate_email
```

The email validation happens automatically because we specified `type="email"` in the `@param` decorator.

## Part 3: State Tracking with Checkpoints

Checkpoints let you save state during execution for debugging:

```python
from bifrost import workflow, param, ExecutionContext

@workflow(
    name="process_batch",
    description="Process a batch of items with progress tracking",
    category="Examples"
)
@param(
    name="items",
    type="list",
    label="Items to Process",
    required=True,
    help_text="Comma-separated list of items"
)
async def process_batch(context: ExecutionContext, items: list):
    """Process multiple items with checkpoint tracking."""

    context.log("info", f"Starting to process {len(items)} items")

    # Save checkpoint at the start
    context.save_checkpoint("batch_start", {
        "total_items": len(items),
        "items": items
    })

    results = []
    errors = []

    for i, item in enumerate(items):
        try:
            context.log("info", f"Processing item {i+1}/{len(items)}: {item}")

            # Simulate processing
            processed = {
                "original": item,
                "processed": item.upper(),
                "length": len(item)
            }
            results.append(processed)

            # Save checkpoint every 5 items
            if (i + 1) % 5 == 0:
                context.save_checkpoint(f"progress_item_{i+1}", {
                    "processed_count": i + 1,
                    "total_items": len(items)
                })

        except Exception as e:
            context.log("error", f"Failed to process {item}: {str(e)}")
            errors.append({"item": item, "error": str(e)})

    # Save final checkpoint
    context.save_checkpoint("batch_complete", {
        "processed_count": len(results),
        "error_count": len(errors),
        "success_rate": len(results) / len(items) * 100
    })

    context.log("info", f"Batch processing complete: {len(results)} successful, {len(errors)} failed")

    return {
        "total": len(items),
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }
```

### Understanding Checkpoints

When you view the execution in the web UI, you'll see all saved checkpoints in the execution detail view. This is invaluable for debugging! If your workflow fails at item #12, you can see exactly which items processed successfully and which failed.

## Part 4: Using Data Providers for Dynamic Dropdowns

Data providers make forms interactive by providing dynamic options:

```python
# First, create the data provider
from bifrost import data_provider, ExecutionContext

@data_provider(
    name="get_greeting_languages",
    description="Available greeting languages",
    category="Examples",
    cache_ttl_seconds=3600
)
async def get_greeting_languages(context: ExecutionContext):
    """Return available greeting languages for the workflow."""

    return [
        {
            "label": "English",
            "value": "en",
            "metadata": {"flag": "🇺🇸"}
        },
        {
            "label": "Spanish",
            "value": "es",
            "metadata": {"flag": "🇪🇸"}
        },
        {
            "label": "French",
            "value": "fr",
            "metadata": {"flag": "🇫🇷"}
        },
        {
            "label": "German",
            "value": "de",
            "metadata": {"flag": "🇩🇪"}
        }
    ]

# Now use the data provider in a workflow
@workflow(
    name="multilingual_greeting",
    description="Greet someone in their preferred language",
    category="Examples"
)
@param("name", type="string", label="Your Name", required=True)
@param(
    name="language",
    type="string",
    label="Preferred Language",
    data_provider="get_greeting_languages",
    required=True
)
async def multilingual_greeting(context: ExecutionContext, name: str, language: str):
    """Greet in the selected language."""

    greetings = {
        "en": f"Hello, {name}!",
        "es": f"¡Hola, {name}!",
        "fr": f"Bonjour, {name}!",
        "de": f"Hallo, {name}!"
    }

    greeting = greetings.get(language, greetings["en"])

    return {
        "greeting": greeting,
        "language": language,
        "name": name
    }
```

### How Data Providers Work

1. When the form is loaded, Bifrost calls your data provider
2. The data provider returns a list of options
3. The form displays these options in a dropdown
4. When the user submits, the `value` from the selected option is passed to the workflow

### Caching

Data providers cache results based on `cache_ttl_seconds`. In the example above:
- First call to `get_greeting_languages()` executes the function
- For the next 1 hour (3600 seconds), the cached result is used
- After 1 hour, the cache expires and the function runs again

## Part 5: Logging and Debugging

Logging is critical for understanding what happened during execution:

```python
from bifrost import workflow, param, ExecutionContext

@workflow(
    name="debug_workflow",
    description="Example showing different log levels",
    category="Examples"
)
@param("value", type="int", label="Value", required=True)
async def debug_workflow(context: ExecutionContext, value: int):
    """Demonstrate logging at different levels."""

    # INFO: General progress
    context.log("info", "Workflow started", {
        "value": value,
        "org_id": context.org_id
    })

    # DEBUG: Detailed information (use sparingly)
    if value < 0:
        context.log("warning", "Value is negative", {
            "value": value,
            "action": "continuing anyway"
        })

    try:
        # Do some work
        result = 100 / value  # Intentional error if value=0

        context.log("info", "Calculation successful", {
            "input": value,
            "result": result
        })

        return {"success": True, "result": result}

    except ZeroDivisionError as e:
        # ERROR: Something went wrong
        context.log("error", "Division by zero", {
            "value": value,
            "error": str(e),
            "error_type": type(e).__name__
        })

        # Return error state (not raising, so workflow completes)
        return {
            "success": False,
            "error": "Cannot divide by zero",
            "value": value
        }
```

### Log Levels

- **info**: General workflow progress
- **warning**: Something unexpected but recoverable
- **error**: Something failed

## Part 6: Error Handling Best Practices

Handle errors gracefully by returning meaningful error states:

```python
from bifrost import workflow, param, ExecutionContext

@workflow(
    name="user_lookup",
    description="Look up a user with error handling",
    category="Examples"
)
@param("user_id", type="string", label="User ID", required=True)
async def user_lookup(context: ExecutionContext, user_id: str):
    """Look up user with comprehensive error handling."""

    # Validate input
    if not user_id or len(user_id) == 0:
        context.log("error", "Invalid user_id", {"user_id": user_id})
        return {
            "success": False,
            "error": "user_id cannot be empty",
            "error_type": "ValidationError"
        }

    try:
        # Simulate database lookup
        context.log("info", f"Looking up user: {user_id}")

        # Mock: user doesn't exist
        if user_id == "nonexistent":
            context.log("warning", f"User not found: {user_id}")
            return {
                "success": False,
                "error": f"User {user_id} not found",
                "error_type": "NotFoundError"
            }

        # Mock: successful lookup
        user = {
            "id": user_id,
            "email": f"{user_id}@example.com",
            "name": user_id.title()
        }

        context.log("info", f"User found: {user['email']}")

        return {
            "success": True,
            "user": user
        }

    except Exception as e:
        # Unexpected error
        context.log("error", "Unexpected error during lookup", {
            "user_id": user_id,
            "error": str(e),
            "error_type": type(e).__name__
        })

        return {
            "success": False,
            "error": "Internal server error",
            "error_type": "InternalError"
        }
```

## Common Patterns

### Pattern 1: Map and Filter

Process a list of items:

```python
@workflow(name="map_filter", description="Map and filter example")
@param("items", type="list", label="Items")
async def map_filter(context: ExecutionContext, items: list):
    # Filter: keep only items starting with 'a'
    filtered = [item for item in items if item.lower().startswith('a')]

    # Map: convert to uppercase
    mapped = [item.upper() for item in filtered]

    return {"original": items, "filtered": filtered, "mapped": mapped}
```

### Pattern 2: Conditional Logic

Different behavior based on input:

```python
@workflow(name="conditional", description="Conditional logic example")
@param("action", type="string", label="Action", required=True)
async def conditional(context: ExecutionContext, action: str):
    if action == "create":
        return {"result": "Created new item"}
    elif action == "update":
        return {"result": "Updated existing item"}
    elif action == "delete":
        return {"result": "Deleted item"}
    else:
        return {"error": f"Unknown action: {action}"}
```

## Troubleshooting

### Workflow not showing up in UI

1. Verify decorator is applied: `@workflow(...)`
2. Check workflow is in the correct directory
3. Look for startup errors in function app logs
4. Verify workflow name is unique across your instance

### Parameters not validating

1. Check parameter type is valid: `string`, `int`, `float`, `bool`, `json`, `list`, `email`
2. For custom validation, implement in workflow code
3. Test with curl to see validation errors

### Checkpoint data not appearing

1. Ensure you're calling `context.save_checkpoint()`
2. Workflow must complete successfully
3. View checkpoints in execution detail view in UI

## Next Steps

- Read the [Writing Workflows](/docs/guides/workflows/writing-workflows) guide for comprehensive reference
- Learn about [Using Decorators](/docs/guides/workflows/using-decorators) in depth
- Explore [Error Handling](/docs/guides/workflows/error-handling) patterns
- Check out the [Concepts: Workflows](/docs/concepts/workflows) for deeper understanding

Congratulations on completing your first Bifrost workflow tutorial!
