---
title: "Integrate Custom APIs"
description: "Learn how to integrate any HTTP API or custom service with Bifrost"
---

Not every API you need is pre-built into Bifrost. This guide shows how to integrate custom APIs and third-party services that don't have native OAuth support.

## Making HTTP Requests

Bifrost provides HTTP client methods for all request types.

### GET Request

Fetch data from an API:

```python
from bifrost import workflow, context

@workflow(
    name="fetch_json_api",
    description="Fetch data from custom JSON API"
)
async def fetch_json_api(ctx: context.WorkflowContext):
    """Get data from any REST API."""
    
    response = await ctx.http_get(
        "https://api.example.com/data",
        headers={"Authorization": "Bearer your-token"},
        params={"page": 1, "limit": 100}
    )
    
    if response.status_code == 200:
        data = response.json()
        ctx.log("info", f"Retrieved {len(data)} items")
        return data
    else:
        ctx.log("error", f"API error: {response.status_code}")
        raise Exception(f"Failed to fetch data: {response.status_code}")
```

### POST Request

Send data to an API:

```python
import json

async def create_item(ctx, name: str, description: str):
    """Create item via API."""
    
    body = {
        "name": name,
        "description": description
    }
    
    response = await ctx.http_post(
        "https://api.example.com/items",
        headers={
            "Authorization": "Bearer your-token",
            "Content-Type": "application/json"
        },
        body=json.dumps(body)
    )
    
    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"Creation failed: {response.status_code}")
```

### PUT/PATCH Requests

Update existing data:

```python
# Full update (PUT)
response = await ctx.http_put(
    "https://api.example.com/items/123",
    headers={"Authorization": "Bearer token"},
    body=json.dumps({"name": "New Name"})
)

# Partial update (PATCH)
response = await ctx.http_patch(
    "https://api.example.com/items/123",
    headers={"Authorization": "Bearer token"},
    body=json.dumps({"status": "completed"})
)
```

### DELETE Request

Remove resources:

```python
response = await ctx.http_delete(
    "https://api.example.com/items/123",
    headers={"Authorization": "Bearer token"}
)

if response.status_code == 204:
    ctx.log("info", "Item deleted successfully")
```

## Authentication Patterns

### API Key in Header

```python
async def with_api_key(ctx):
    api_key = await ctx.get_secret("api_key")
    
    response = await ctx.http_get(
        "https://api.example.com/data",
        headers={"X-API-Key": api_key}
    )
```

### Bearer Token

```python
async def with_bearer_token(ctx):
    token = await ctx.get_secret("api_token")
    
    response = await ctx.http_get(
        "https://api.example.com/data",
        headers={"Authorization": f"Bearer {token}"}
    )
```

### Basic Auth

```python
import base64

async def with_basic_auth(ctx):
    username = await ctx.get_secret("api_username")
    password = await ctx.get_secret("api_password")
    
    # Encode credentials
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    
    response = await ctx.http_get(
        "https://api.example.com/data",
        headers={"Authorization": f"Basic {credentials}"}
    )
```

### Custom Headers

```python
async def with_custom_headers(ctx):
    api_key = await ctx.get_secret("api_key")
    timestamp = time.time()
    
    response = await ctx.http_get(
        "https://api.example.com/data",
        headers={
            "X-API-Key": api_key,
            "X-Request-Id": str(uuid.uuid4()),
            "X-Timestamp": str(timestamp)
        }
    )
```

## Handling Responses

### JSON Responses

```python
response = await ctx.http_get("https://api.example.com/users")

if response.status_code == 200:
    # Parse JSON automatically
    users = response.json()
    
    for user in users["data"]:
        print(user["name"])
```

### Text/Plain Responses

```python
response = await ctx.http_get("https://api.example.com/export/csv")

if response.status_code == 200:
    # Get raw text
    csv_content = response.text
    
    # Save or process
    with open("export.csv", "w") as f:
        f.write(csv_content)
```

### Binary Responses

```python
response = await ctx.http_get("https://api.example.com/file/document.pdf")

if response.status_code == 200:
    # Get raw bytes
    pdf_data = response.content
    
    # Save binary file
    with open("document.pdf", "wb") as f:
        f.write(pdf_data)
```

### Error Responses

```python
response = await ctx.http_get("https://api.example.com/data")

if response.status_code >= 400:
    error_body = response.json()
    error_message = error_body.get("error", {}).get("message", "Unknown error")
    ctx.log("error", f"API error: {error_message}")
    raise Exception(error_message)
```

## Pagination

APIs often paginate results. Handle different pagination styles:

### Offset/Limit Pagination

```python
async def get_all_items_offset(ctx):
    """Paginate with offset and limit."""
    all_items = []
    limit = 100
    offset = 0
    
    while True:
        response = await ctx.http_get(
            "https://api.example.com/items",
            params={"limit": limit, "offset": offset}
        )
        
        items = response.json()["data"]
        if not items:
            break
        
        all_items.extend(items)
        offset += limit
    
    return all_items
```

### Cursor Pagination

```python
async def get_all_items_cursor(ctx):
    """Paginate with cursor tokens."""
    all_items = []
    cursor = None
    
    while True:
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        
        response = await ctx.http_get(
            "https://api.example.com/items",
            params=params
        )
        
        data = response.json()
        all_items.extend(data["items"])
        
        # Check for next page
        cursor = data.get("next_cursor")
        if not cursor:
            break
    
    return all_items
```

### Link Header Pagination

```python
import re

async def get_all_items_link_header(ctx):
    """Paginate using Link header (GitHub style)."""
    all_items = []
    url = "https://api.example.com/items?per_page=100"
    
    while url:
        response = await ctx.http_get(url, headers={"Authorization": "Bearer token"})
        
        all_items.extend(response.json())
        
        # Parse Link header for next page
        link_header = response.headers.get("Link", "")
        url = None
        
        for link in link_header.split(","):
            if 'rel="next"' in link:
                # Extract URL from: <https://api.example.com/...>; rel="next"
                match = re.search(r'<(.+?)>', link)
                if match:
                    url = match.group(1)
    
    return all_items
```

## Rate Limiting

Respect API rate limits:

```python
import asyncio
import time

class RateLimiter:
    def __init__(self, requests_per_second: float = 10):
        self.requests_per_second = requests_per_second
        self.min_interval = 1 / requests_per_second
        self.last_request_time = 0
    
    async def wait(self):
        """Wait if necessary to maintain rate limit."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

# Usage
async def process_items(ctx):
    rate_limiter = RateLimiter(requests_per_second=5)
    
    for item_id in item_ids:
        await rate_limiter.wait()
        
        response = await ctx.http_get(
            f"https://api.example.com/items/{item_id}"
        )
```

## Retry Logic

Handle temporary failures gracefully:

```python
import asyncio

async def make_request_with_retry(ctx, url: str, max_retries: int = 3):
    """Make request with exponential backoff retry."""
    
    for attempt in range(max_retries):
        try:
            response = await ctx.http_get(url)
            
            # Retry on 429 (rate limit) or 5xx errors
            if response.status_code in [429, 500, 502, 503, 504]:
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2 ** attempt
                    ctx.log("warning", f"Retrying after {wait_time}s", {
                        "status_code": response.status_code,
                        "attempt": attempt + 1
                    })
                    await asyncio.sleep(wait_time)
                    continue
            
            # Success or non-retryable error
            return response
            
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                ctx.log("warning", f"Request failed, retrying: {str(e)}")
                await asyncio.sleep(wait_time)
            else:
                raise
    
    raise Exception(f"Failed after {max_retries} retries")
```

## Data Transformation

Transform API responses to your needs:

```python
async def transform_api_response(ctx):
    """Get data from API and transform format."""
    
    response = await ctx.http_get("https://api.example.com/users")
    api_users = response.json()["data"]
    
    # Transform to our format
    transformed_users = [
        {
            "id": user["id"],
            "email": user["email_address"],  # Map field names
            "name": f"{user['first']} {user['last']}",  # Combine fields
            "active": user["status"] == "active"  # Convert values
        }
        for user in api_users
    ]
    
    return transformed_users
```

## Batch Operations

Process multiple items efficiently:

```python
async def batch_create_items(ctx, items: list):
    """Create multiple items, batching requests."""
    
    results = {"created": [], "failed": []}
    batch_size = 10
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        # Process batch in parallel
        tasks = [
            create_single_item(ctx, item)
            for item in batch
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for item, response in zip(batch, responses):
            if isinstance(response, Exception):
                results["failed"].append({
                    "item": item,
                    "error": str(response)
                })
            else:
                results["created"].append(response)
        
        # Rate limiting between batches
        await asyncio.sleep(0.5)
    
    return results

async def create_single_item(ctx, item):
    """Create single item (called in parallel)."""
    response = await ctx.http_post(
        "https://api.example.com/items",
        headers={"Authorization": "Bearer token"},
        body=json.dumps(item)
    )
    return response.json()
```

## Caching API Responses

Cache expensive API calls:

```python
from datetime import datetime, timedelta

async def get_with_cache(ctx, cache_key: str, api_url: str, ttl_seconds: int = 300):
    """Get data with caching."""
    
    # Try to get from cache
    cached = ctx.get_variable(f"cache_{cache_key}")
    
    if cached:
        cache_time = cached.get("timestamp", 0)
        age = (datetime.now().timestamp() - cache_time)
        
        if age < ttl_seconds:
            ctx.log("info", "Using cached data", {"key": cache_key, "age_seconds": age})
            return cached["data"]
    
    # Cache miss - fetch from API
    response = await ctx.http_get(api_url)
    data = response.json()
    
    # Store in cache
    ctx.set_variable(f"cache_{cache_key}", {
        "data": data,
        "timestamp": datetime.now().timestamp()
    })
    
    return data
```

## Error Handling Examples

```python
async def robust_api_call(ctx, url: str):
    """Example with comprehensive error handling."""
    
    try:
        response = await ctx.http_get(url, headers={"Authorization": "Bearer token"})
        
        # Handle HTTP errors
        if response.status_code == 404:
            ctx.log("warning", "Resource not found")
            return None
        
        if response.status_code == 401:
            ctx.log("error", "Authentication failed - check token")
            raise Exception("Invalid authentication")
        
        if response.status_code == 429:
            ctx.log("warning", "Rate limited - retry later")
            raise Exception("API rate limit exceeded")
        
        if response.status_code >= 500:
            ctx.log("error", "Server error - retry later")
            raise Exception("API server error")
        
        if response.status_code >= 400:
            error_msg = response.json().get("message", "Unknown error")
            raise Exception(f"API error: {error_msg}")
        
        return response.json()
    
    except Exception as e:
        ctx.log("error", "API request failed", {"error": str(e), "url": url})
        raise
```

## References

- HTTP Status Codes: [MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)
- REST API Best Practices: [Microsoft REST API Guidelines](https://github.com/microsoft/api-guidelines)
- Pagination Patterns: [Common API Pagination Patterns](https://www.moesif.com/blog/api-guide/api-pagination/)
