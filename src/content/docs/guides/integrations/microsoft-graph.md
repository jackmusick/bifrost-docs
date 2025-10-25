---
title: "Integrate Microsoft Graph"
description: "Complete guide to using Microsoft Graph API for user and organization management"
---

Microsoft Graph is the unified API for Microsoft 365 services. This guide shows how to set up Graph integration and implement common operations.

## What is Microsoft Graph?

Microsoft Graph provides access to:
- **Azure AD** - User and group management, authentication
- **Exchange Online** - Email, calendar, contacts
- **SharePoint Online** - Sites, documents, lists
- **OneDrive** - Cloud storage
- **Teams** - Chat, meetings, team management
- **Outlook** - Email and calendar
- And many more Microsoft 365 services

All through a single unified REST API.

## Setup

See [OAuth Setup Guide](/guides/integrations/oauth-setup#microsoft-graph-setup) for detailed setup instructions.

Quick version:
1. Create app registration in Azure AD
2. Add Microsoft Graph permissions
3. Create OAuth connection in Bifrost named `microsoft-graph`
4. Authorize the connection

## Common Operations

### List Users

Get all users in your organization:

```python
from bifrost import workflow, context

@workflow(
    name="list_all_users",
    description="List all users in organization",
    category="user_management"
)
async def list_all_users(ctx: context.WorkflowContext):
    """Get all users using Microsoft Graph."""
    
    oauth = await ctx.get_oauth_connection("microsoft-graph")
    
    headers = {
        "Authorization": f"Bearer {oauth['access_token']}",
        "Content-Type": "application/json"
    }
    
    # Paginate through all users
    all_users = []
    url = "https://graph.microsoft.com/v1.0/users"
    
    while url:
        response = await ctx.http_get(url, headers=headers)
        
        if response.status_code != 200:
            ctx.log("error", f"Graph API error: {response.status_code}")
            raise Exception(f"Failed to list users: {response.status_code}")
        
        data = response.json()
        all_users.extend(data.get("value", []))
        
        # Check if more pages exist
        url = data.get("@odata.nextLink")
    
    ctx.log("info", f"Retrieved {len(all_users)} total users")
    return {"users": all_users, "count": len(all_users)}
```

### Create User

Create a new user in Azure AD:

```python
import json

async def create_user(ctx, email: str, first_name: str, last_name: str):
    """Create new user in Azure AD."""
    
    oauth = await ctx.get_oauth_connection("microsoft-graph")
    
    headers = {
        "Authorization": f"Bearer {oauth['access_token']}",
        "Content-Type": "application/json"
    }
    
    # Get tenant ID from config
    tenant_id = ctx.get_config("microsoft_tenant_id")
    domain = tenant_id.split('.')[0] if '.' in tenant_id else "yourdomain"
    
    body = {
        "accountEnabled": True,
        "displayName": f"{first_name} {last_name}",
        "mailNickname": email.split("@")[0],
        "userPrincipalName": f"{email}@{domain}.onmicrosoft.com",
        "givenName": first_name,
        "surname": last_name,
        "passwordProfile": {
            "forceChangePasswordNextSignIn": True,
            "password": "Temp@Pass123!"  # User must change on first login
        }
    }
    
    response = await ctx.http_post(
        "https://graph.microsoft.com/v1.0/users",
        headers=headers,
        body=json.dumps(body)
    )
    
    if response.status_code == 201:
        user = response.json()
        ctx.log("info", f"Created user: {email}", {"user_id": user["id"]})
        return {"status": "created", "user_id": user["id"], "email": email}
    else:
        error = response.json()
        ctx.log("error", f"Failed to create user: {error}")
        raise Exception(f"User creation failed: {error}")
```

### Assign License

Assign Microsoft 365 license to user:

```python
async def assign_license(ctx, user_id: str, sku_id: str):
    """Assign M365 license to user."""
    
    oauth = await ctx.get_oauth_connection("microsoft-graph")
    
    headers = {
        "Authorization": f"Bearer {oauth['access_token']}",
        "Content-Type": "application/json"
    }
    
    # Get list of subscribed SKUs to find the ID
    response = await ctx.http_get(
        "https://graph.microsoft.com/v1.0/subscribedSkus",
        headers=headers
    )
    
    skus = response.json()["value"]
    target_sku = None
    
    for sku in skus:
        if sku["skuPartNumber"] == sku_id:  # e.g., "ENTERPRISEPACK"
            target_sku = sku["skuId"]
            break
    
    if not target_sku:
        raise ValueError(f"SKU not found: {sku_id}")
    
    body = {
        "addLicenses": [
            {
                "skuId": target_sku
            }
        ],
        "removeLicenses": []
    }
    
    response = await ctx.http_post(
        f"https://graph.microsoft.com/v1.0/users/{user_id}/assignLicense",
        headers=headers,
        body=json.dumps(body)
    )
    
    if response.status_code == 200:
        ctx.log("info", f"License assigned: {sku_id}", {"user_id": user_id})
        return {"status": "assigned", "sku": sku_id}
    else:
        error = response.json()
        raise Exception(f"License assignment failed: {error}")
```

### Get User Details

Retrieve specific user information:

```python
async def get_user(ctx, user_email: str):
    """Get user details by email."""
    
    oauth = await ctx.get_oauth_connection("microsoft-graph")
    
    headers = {
        "Authorization": f"Bearer {oauth['access_token']}",
        "Content-Type": "application/json"
    }
    
    # URL encode the email
    user_id = user_email.replace("#", "%23")
    
    response = await ctx.http_get(
        f"https://graph.microsoft.com/v1.0/users/{user_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        user = response.json()
        return {
            "id": user["id"],
            "email": user["userPrincipalName"],
            "display_name": user["displayName"],
            "given_name": user.get("givenName"),
            "surname": user.get("surname"),
            "job_title": user.get("jobTitle"),
            "office_location": user.get("officeLocation"),
            "mobile_phone": user.get("mobilePhone")
        }
    else:
        raise Exception(f"User not found: {user_email}")
```

### Create Group

Create a Microsoft 365 group:

```python
async def create_group(ctx, group_name: str, description: str = ""):
    """Create Microsoft 365 security group."""
    
    oauth = await ctx.get_oauth_connection("microsoft-graph")
    
    headers = {
        "Authorization": f"Bearer {oauth['access_token']}",
        "Content-Type": "application/json"
    }
    
    body = {
        "displayName": group_name,
        "description": description,
        "groupTypes": ["Unified"],  # Microsoft 365 group
        "mailEnabled": True,
        "securityEnabled": False,  # Or True for security group
        "mailNickname": group_name.replace(" ", "").lower()
    }
    
    response = await ctx.http_post(
        "https://graph.microsoft.com/v1.0/groups",
        headers=headers,
        body=json.dumps(body)
    )
    
    if response.status_code == 201:
        group = response.json()
        ctx.log("info", f"Created group: {group_name}", {"group_id": group["id"]})
        return {"group_id": group["id"], "name": group_name}
    else:
        error = response.json()
        raise Exception(f"Group creation failed: {error}")
```

### Add User to Group

Add a user to a group:

```python
async def add_user_to_group(ctx, user_id: str, group_id: str):
    """Add user to group."""
    
    oauth = await ctx.get_oauth_connection("microsoft-graph")
    
    headers = {
        "Authorization": f"Bearer {oauth['access_token']}",
        "Content-Type": "application/json"
    }
    
    body = {
        "@odata.id": f"https://graph.microsoft.com/v1.0/users/{user_id}"
    }
    
    response = await ctx.http_post(
        f"https://graph.microsoft.com/v1.0/groups/{group_id}/members/$ref",
        headers=headers,
        body=json.dumps(body)
    )
    
    if response.status_code == 204:
        ctx.log("info", "User added to group", {
            "user_id": user_id,
            "group_id": group_id
        })
        return {"status": "added"}
    else:
        error = response.json()
        raise Exception(f"Failed to add user to group: {error}")
```

## Graph Query Optimization

### Filtering and Searching

Use OData filters to get only what you need:

```python
# Filter active users
response = await ctx.http_get(
    "https://graph.microsoft.com/v1.0/users?$filter=accountEnabled eq true",
    headers=headers
)

# Search by display name
response = await ctx.http_get(
    "https://graph.microsoft.com/v1.0/users?$search=\"displayName:John\"",
    headers=headers
)

# Select specific properties only
response = await ctx.http_get(
    "https://graph.microsoft.com/v1.0/users?$select=id,displayName,mail",
    headers=headers
)
```

### Pagination

Handle large result sets:

```python
# Graph returns 100 items by default
# For 10,000 users, you need pagination

all_results = []
url = "https://graph.microsoft.com/v1.0/users?$top=100"

while url:
    response = await ctx.http_get(url, headers=headers)
    data = response.json()
    
    all_results.extend(data["value"])
    
    # Check for next page
    url = data.get("@odata.nextLink")
    
    # Optional: Add delay to avoid rate limiting
    await asyncio.sleep(0.1)
```

## Error Handling

Microsoft Graph returns specific error codes:

```python
async def make_graph_request(ctx, url: str, method: str = "GET", body: str = ""):
    """Make Graph request with error handling."""
    
    oauth = await ctx.get_oauth_connection("microsoft-graph")
    
    headers = {
        "Authorization": f"Bearer {oauth['access_token']}",
        "Content-Type": "application/json"
    }
    
    if method == "GET":
        response = await ctx.http_get(url, headers=headers)
    elif method == "POST":
        response = await ctx.http_post(url, headers=headers, body=body)
    
    # Handle specific error codes
    if response.status_code == 404:
        raise ValueError("Resource not found")
    elif response.status_code == 409:
        raise ValueError("Resource already exists (conflict)")
    elif response.status_code == 429:
        raise Exception("Rate limited - too many requests")
    elif response.status_code == 503:
        raise Exception("Service temporarily unavailable - retry later")
    elif response.status_code >= 500:
        raise Exception(f"Server error: {response.status_code}")
    elif response.status_code >= 400:
        error = response.json()
        raise ValueError(f"Client error: {error.get('error', {}).get('message')}")
    
    return response
```

## Rate Limiting

Microsoft Graph has rate limits:
- 2,000 requests per 20 seconds per app
- 4,000 requests per 20 seconds per user

Implement throttling:

```python
import asyncio
import time

class GraphThrottler:
    def __init__(self, requests_per_second: float = 5):
        self.requests_per_second = requests_per_second
        self.min_interval = 1 / requests_per_second
        self.last_request = 0
    
    async def wait(self):
        elapsed = time.time() - self.last_request
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self.last_request = time.time()

# Usage
throttler = GraphThrottler(requests_per_second=5)

for user_email in user_emails:
    await throttler.wait()
    user = await get_user(ctx, user_email)
```

## Common Issues

### "Invalid Redirect URI"

Make sure redirect URI matches exactly:
- Domain must match
- Protocol must be https (except localhost)
- Path must match

### "Insufficient Privileges"

User performing operation doesn't have permission. Solutions:
- Use service account with delegated admin rights
- Add required permission scopes
- Grant admin consent in Azure AD

### "User Not Found"

When user doesn't exist:
- Check user email format
- Ensure user isn't in deleted state
- Try searching instead of using exact ID

### "Throttled (429)"

Too many requests too quickly:
- Reduce request rate
- Implement exponential backoff
- Batch operations where possible

## References

- [Microsoft Graph API Reference](https://docs.microsoft.com/graph/api/overview)
- [Azure AD Concepts](https://docs.microsoft.com/azure/active-directory/fundamentals/)
- [Graph Explorer](https://developer.microsoft.com/graph/graph-explorer) - Test API calls
- [Graph SDKs](https://docs.microsoft.com/graph/sdks/sdks-overview)
