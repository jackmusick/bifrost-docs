---
title: Handle Errors in Workflows
description: Comprehensive guide to error handling, logging, and debugging in Bifrost workflows
---

## Overview

Error handling in Bifrost workflows involves:

1. **Validating inputs** - Catch problems early
2. **Handling exceptions** - Catch and recover from errors
3. **Logging errors** - Track what went wrong
4. **Returning error states** - Indicate failure gracefully
5. **Debugging failed executions** - Use checkpoints and logs

This guide covers all these aspects.

## Input Validation

Validate parameters early before doing any work:

```python
@workflow(name="validate_example")
@param("email", type="email", required=True)
@param("count", type="int", required=True)
async def validate_example(context: ExecutionContext, email: str, count: int):
    """Validate inputs early."""

    # Validate count
    if count < 1:
        context.log("error", "Invalid count", {"count": count})
        return {
            "success": False,
            "error": "count must be >= 1",
            "error_code": "INVALID_COUNT"
        }

    if count > 1000:
        context.log("warning", "Large count requested", {"count": count})

    # Email validation happens automatically because type="email"
    # But you can add custom validation:
    if not email.endswith("@company.com"):
        context.log("error", "Invalid email domain", {"email": email})
        return {
            "success": False,
            "error": "Email must use company domain",
            "error_code": "INVALID_DOMAIN"
        }

    # All validations passed
    return {"success": True, "email": email, "count": count}
```

### Parameter Type Validation

Bifrost automatically validates parameters based on their type:

```python
@param("email", type="email")      # Automatically validates email format
@param("quantity", type="int",
    validation={"min": 1, "max": 100})  # Validates range
@param("url", type="string",
    validation={"pattern": r"^https?://"})  # Validates pattern
```

These validations happen **before** your workflow function executes. Invalid inputs are rejected with 400 Bad Request.

## Try-Catch Patterns

Catch expected exceptions and handle them gracefully:

```python
@workflow(name="safe_api_call")
@param("user_id", type="string", required=True)
async def safe_api_call(context: ExecutionContext, user_id: str):
    """API call with error handling."""

    try:
        context.log("info", f"Fetching user: {user_id}")

        # Make API call (could fail in many ways)
        user = await fetch_user_from_api(user_id)

        context.log("info", f"User found: {user['email']}")

        return {
            "success": True,
            "user": user
        }

    except UserNotFoundError as e:
        # Known error type - handle specifically
        context.log("warning", f"User not found: {user_id}")

        return {
            "success": False,
            "error": "User not found",
            "error_code": "USER_NOT_FOUND",
            "user_id": user_id
        }

    except APITimeoutError as e:
        # Network/timeout error
        context.log("error", "API timeout during user fetch", {
            "user_id": user_id,
            "error": str(e)
        })

        return {
            "success": False,
            "error": "API timeout - please try again",
            "error_code": "TIMEOUT",
            "retryable": True
        }

    except Exception as e:
        # Unexpected error
        context.log("error", "Unexpected error during user fetch", {
            "user_id": user_id,
            "error": str(e),
            "error_type": type(e).__name__
        })

        return {
            "success": False,
            "error": "Internal error",
            "error_code": "INTERNAL_ERROR",
            "details": str(e) if context.is_platform_admin else None
        }
```

### Exception Hierarchy

Catch specific exceptions before general ones:

```python
try:
    # Your code
    pass

except ValueError:
    # Handle ValueError (most specific)
    pass

except TypeError:
    # Handle TypeError
    pass

except Exception:
    # Handle any other exception (most general)
    pass

# Don't do this:
# except Exception:
#     pass
# except ValueError:  # Unreachable - already caught by Exception
#     pass
```

## Error Response Format

Return structured error responses so callers understand what happened:

```python
{
    "success": False,
    "error": "Human-readable error message",
    "error_code": "ERROR_CODE",        # For programmatic handling
    "error_type": "ValidationError",   # Exception type (optional)
    "details": {...},                  # Additional context (optional)
    "retryable": False                 # Can caller retry? (optional)
}
```

### Error Codes

Use consistent error codes for different failure modes:

```python
# Validation errors
{"error_code": "INVALID_INPUT", "error": "Email is invalid"}
{"error_code": "MISSING_FIELD", "error": "name is required"}
{"error_code": "OUT_OF_RANGE", "error": "quantity must be 1-100"}

# Not found errors
{"error_code": "USER_NOT_FOUND", "error": "User does not exist"}
{"error_code": "RESOURCE_NOT_FOUND", "error": "Resource not found"}

# Permission errors
{"error_code": "FORBIDDEN", "error": "You don't have permission"}
{"error_code": "UNAUTHORIZED", "error": "Authentication required"}

# Dependency errors
{"error_code": "DEPENDENCY_ERROR", "error": "Service unavailable"}
{"error_code": "TIMEOUT", "error": "Operation timed out"}

# Business logic errors
{"error_code": "BUSINESS_RULE_VIOLATION", "error": "Cannot delete active user"}
{"error_code": "DUPLICATE_ENTRY", "error": "User already exists"}

# System errors
{"error_code": "INTERNAL_ERROR", "error": "Internal server error"}
```

## Logging Errors

Always log errors with enough context to debug:

```python
@workflow(name="logging_example")
async def logging_example(context: ExecutionContext):
    """Show proper error logging."""

    try:
        # Do something that might fail
        result = await risky_operation()

    except ValueError as e:
        # Good - log with context
        context.log("error", "Value error in operation", {
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Bad - log with minimal info
        # context.log("error", "Error occurred")

    except Exception as e:
        # Good - log complete exception info
        import traceback
        context.log("error", "Unexpected error", {
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        })
```

### Log Levels

- **error**: Something failed and workflow cannot continue
- **warning**: Something unexpected but recoverable (e.g., retry attempt 2 of 3)
- **info**: Normal progress (e.g., "Step 1 complete")

## Checkpoints for Debugging

Save checkpoints to understand where failures occur:

```python
@workflow(name="checkpoint_debugging")
@param("items", type="list", required=True)
async def checkpoint_debugging(context: ExecutionContext, items: list):
    """Process items with checkpoint tracking."""

    # Save checkpoint at start
    context.save_checkpoint("start", {
        "total_items": len(items),
        "timestamp": datetime.utcnow().isoformat()
    })

    successful = 0
    failed = 0

    for i, item in enumerate(items):
        try:
            # Process item
            result = await process_item(item)
            successful += 1

            # Save checkpoint every 10 items
            if (i + 1) % 10 == 0:
                context.save_checkpoint(f"progress_{i+1}", {
                    "processed": i + 1,
                    "successful": successful,
                    "failed": failed
                })

        except Exception as e:
            failed += 1
            context.log("error", f"Failed to process item {i}", {
                "item": item,
                "error": str(e),
                "index": i
            })

            # Save checkpoint on failure
            context.save_checkpoint(f"failure_{i}", {
                "failed_item": item,
                "index": i,
                "error": str(e),
                "successful_so_far": successful
            })

    # Final checkpoint
    context.save_checkpoint("complete", {
        "total": len(items),
        "successful": successful,
        "failed": failed,
        "success_rate": successful / len(items) * 100 if items else 0
    })

    return {
        "total": len(items),
        "successful": successful,
        "failed": failed
    }
```

When debugging in the UI:
1. Open execution detail view
2. Scroll through checkpoints
3. See exact state at each checkpoint
4. Identify where failure occurred
5. Understand data at failure point

## Handling Specific Error Types

### Validation Errors

```python
if not email or "@" not in email:
    context.log("error", "Invalid email", {"email": email})
    return {
        "success": False,
        "error": "Email format is invalid",
        "error_code": "INVALID_EMAIL"
    }
```

### Not Found Errors

```python
user = await get_user(user_id)
if not user:
    context.log("warning", f"User not found: {user_id}")
    return {
        "success": False,
        "error": f"User {user_id} not found",
        "error_code": "NOT_FOUND"
    }
```

### Permission Errors

```python
if not context.is_platform_admin:
    context.log("warning", f"Unauthorized access attempt: {context.user_id}")
    return {
        "success": False,
        "error": "You don't have permission to perform this action",
        "error_code": "FORBIDDEN"
    }
```

### Business Logic Errors

```python
if user["status"] == "deleted":
    context.log("warning", f"Cannot modify deleted user: {user_id}")
    return {
        "success": False,
        "error": "Cannot perform operation on deleted user",
        "error_code": "BUSINESS_RULE_VIOLATION"
    }
```

### Timeout Errors

```python
import asyncio

try:
    result = await asyncio.wait_for(
        long_operation(),
        timeout=30.0
    )
except asyncio.TimeoutError:
    context.log("error", "Operation timed out after 30 seconds")
    return {
        "success": False,
        "error": "Operation timed out",
        "error_code": "TIMEOUT",
        "retryable": True
    }
```

## Async/Await Error Handling

Handle errors in async operations:

```python
import asyncio

async def safe_gather():
    """Gather results from multiple operations."""

    results = await asyncio.gather(
        operation1(),
        operation2(),
        operation3(),
        return_exceptions=True  # Important: return exceptions instead of raising
    )

    successful = []
    failed = []

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            failed.append({
                "operation": i,
                "error": str(result)
            })
        else:
            successful.append(result)

    return {
        "successful": len(successful),
        "failed": len(failed),
        "results": successful,
        "errors": failed
    }
```

## Partial Success Handling

When some items succeed and others fail:

```python
@workflow(name="bulk_operation")
@param("items", type="list", required=True)
async def bulk_operation(context: ExecutionContext, items: list):
    """Process multiple items, track successes and failures."""

    successful = []
    failed = []

    for item in items:
        try:
            result = await process_item(item)
            successful.append(result)
        except Exception as e:
            failed.append({
                "item": item,
                "error": str(e)
            })

    # Return partial success
    return {
        "total": len(items),
        "successful_count": len(successful),
        "failed_count": len(failed),
        "success_rate": len(successful) / len(items) * 100,
        "successful": successful,
        "failed": failed
    }
```

## Debugging Tips

### 1. Add Detailed Logging

```python
context.log("info", "Starting operation", {
    "input": param_value,
    "org_id": context.org_id,
    "user_id": context.user_id
})
```

### 2. Save State at Key Points

```python
context.save_checkpoint("before_api_call", {
    "prepared_data": data,
    "timestamp": datetime.utcnow().isoformat()
})

result = await api_call(data)

context.save_checkpoint("after_api_call", {
    "response": result,
    "status_code": result.get("status")
})
```

### 3. Use Meaningful Error Messages

```python
# Good - explains what went wrong
"Email must use company domain (@company.com)"

# Bad - too vague
"Invalid email"
```

### 4. Include Context in Errors

```python
# Good - includes details
{
    "error": "Cannot create user",
    "reason": "Email already exists",
    "email": email,
    "existing_user_id": existing_user["id"]
}

# Bad - missing context
{
    "error": "Cannot create user"
}
```

### 5. Test Error Cases

```python
# Test file error handling
import pytest

@pytest.mark.asyncio
async def test_handles_missing_user():
    context = MagicMock()
    result = await my_workflow(context, user_id="nonexistent")
    assert result["success"] is False
    assert result["error_code"] == "NOT_FOUND"
```

## Common Error Patterns

### Pattern: Validate or Return Error

```python
def validate_or_return(value, name):
    if not value:
        return {
            "success": False,
            "error": f"{name} is required",
            "error_code": "MISSING_FIELD"
        }
    return None

# Usage:
error = validate_or_return(email, "email")
if error:
    return error
```

### Pattern: Retry with Backoff

```python
async def retry_with_backoff(func, max_attempts=3, backoff=2):
    for attempt in range(max_attempts):
        try:
            return await func()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            delay = backoff ** attempt
            await asyncio.sleep(delay)

# Usage:
result = await retry_with_backoff(api_call)
```

### Pattern: Fallback Value

```python
# Try primary source, fallback to secondary
result = await fetch_from_primary_api()
if not result:
    context.log("warning", "Primary API unavailable, using fallback")
    result = await fetch_from_fallback_api()

if not result:
    return {"error": "All sources unavailable"}
```

## Best Practices

### 1. Fail Fast

```python
# Good - validate immediately
if not email:
    return {"error": "email required"}

# Bad - fail later after doing work
user = await create_user(email, name)  # Fails if email invalid
```

### 2. Log and Return (Don't Swallow Errors Silently)

```python
# Good
except Exception as e:
    context.log("error", "Failed", {"error": str(e)})
    return {"error": "Operation failed"}

# Bad - silent failure
except Exception:
    pass  # No one knows what went wrong
```

### 3. Distinguish Between Errors and Failures

```python
# Workflow error (infrastructure/code problem)
# → Raises exception, returns 500

# Business logic failure (validation, not found, permission denied)
# → Returns {"success": False, "error": "..."}, returns 200
```

### 4. Hide Sensitive Details in Production

```python
# Good
return {
    "error": "Database error occurred",
    "details": str(e) if context.is_platform_admin else None
}

# Bad - exposes sensitive info
return {
    "error": str(e)  # Might contain connection strings, passwords
}
```

## Troubleshooting

### Error logs don't appear

1. Verify you're calling `context.log()`
2. Check execution completed (errors in pending executions don't show logs)
3. Look in execution detail view, not just summary

### Checkpoint data not showing

1. Ensure `context.save_checkpoint()` is called
2. Workflow must complete (even with errors)
3. View in execution detail → Checkpoints tab

### Exception not caught

1. Import the correct exception type
2. Verify exception type matches (e.g., `except ValueError:` won't catch `TypeError`)
3. Check order - specific exceptions before general ones

## Next Steps

- Read [Writing Workflows](/docs/guides/workflows/writing-workflows) for complete examples
- Explore [Concepts: Workflows](/docs/concepts/workflows) for deeper understanding
- Check [Using Decorators](/docs/guides/workflows/using-decorators) for parameter validation
