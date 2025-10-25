---
title: "Set Up OAuth Integration"
description: "Learn how to set up and use OAuth connections for secure API integration in Bifrost"
---

OAuth (Open Authorization) is a secure way to authorize applications to access external services without storing passwords. Bifrost simplifies OAuth management by handling token refresh, secure storage, and multi-tenant isolation automatically.

## What is OAuth?

OAuth 2.0 is an open standard that allows secure delegation of access. Instead of storing credentials, you exchange an authorization code for access tokens that grant limited, specific permissions.

### Key Concepts

- **Authorization Code**: A temporary code from the OAuth provider that proves you've been authorized
- **Access Token**: Used to make API calls on your behalf (expires periodically)
- **Refresh Token**: Used to get a new access token when the old one expires
- **Scope**: Specifies what permissions the token grants (e.g., `User.ReadWrite.All`)

## Set Up Your First OAuth Connection

This tutorial shows how to set up an OAuth connection with Microsoft Graph, then use it in a workflow.

### Step 1: Create an OAuth Application

First, create an OAuth application with your provider:

#### For Microsoft Graph (Azure AD)

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure AD** → **App registrations**
3. Click **+ New registration**
4. Fill in the details:
   - **Name**: "Bifrost Integration"
   - **Supported account types**: Select appropriate option
   - **Redirect URI**: Leave blank for now (we'll add it later)
5. Click **Register**

On the next screen:
- Copy the **Application (client) ID** - you'll need this
- Copy the **Tenant ID** - you'll need this

Add a client secret:
1. Go to **Certificates & secrets**
2. Click **+ New client secret**
3. Set expiration to 24 months
4. Copy the secret value immediately (you won't see it again)

Configure API permissions:
1. Go to **API permissions**
2. Click **+ Add a permission**
3. Select **Microsoft Graph**
4. Select **Delegated permissions** (for user context)
5. Add required scopes (e.g., `User.ReadWrite.All`, `Group.ReadWrite.All`)
6. Click **Grant admin consent**

### Step 2: Get Your Redirect URI

Bifrost automatically provides a redirect URI for OAuth callbacks:

```
https://your-bifrost-domain.com/oauth/callback/{connection_name}
```

For local development, use:
```
https://localhost:5173/oauth/callback/{connection_name}
```

Add this to your OAuth application:

**For Microsoft Graph:**
1. Go to **Authentication**
2. Click **+ Add a platform**
3. Select **Web**
4. Enter your redirect URI
5. Under **Implicit grant and hybrid flows**, check **Access tokens** and **ID tokens**
6. Click **Save**

### Step 3: Create OAuth Connection in Bifrost

Navigate to the Bifrost admin UI and go to **Integrations → OAuth Connections**.

Click **+ Create Connection** and fill in:

```
Connection Name: microsoft-graph
Provider Type: Microsoft Graph
Client ID: [your-client-id]
Client Secret: [your-client-secret]
Tenant ID: [your-tenant-id]
Scopes: User.ReadWrite.All Group.ReadWrite.All
```

Click **Create Connection**.

### Step 4: Authorize the Connection

The connection is now created but not yet authorized.

1. Click the connection to open its details
2. Click **Authorize**
3. You'll be redirected to Microsoft's login page
4. Sign in and grant permissions
5. You'll be redirected back to Bifrost
6. The connection status should show **Connected**

If authorization fails, check:
- Client ID and secret are correct
- Redirect URI matches exactly (including protocol and trailing slash)
- Permissions are properly configured in Azure AD

### Step 5: Use in a Workflow

Now use the OAuth connection in your workflow:

```python
from bifrost import context, workflow, param

@workflow(
    name="list_users",
    description="List all users from Microsoft Graph",
    category="user_management"
)
async def list_users(ctx: context.WorkflowContext):
    """Get all users from Microsoft Graph using OAuth."""

    # Get OAuth credentials
    oauth = await ctx.get_oauth_connection("microsoft-graph")

    # Make API call with token
    headers = {
        "Authorization": f"Bearer {oauth['access_token']}",
        "Content-Type": "application/json"
    }

    response = await ctx.http_get(
        "https://graph.microsoft.com/v1.0/users",
        headers=headers
    )

    if response.status_code == 200:
        users = response.json()
        ctx.log("info", f"Retrieved {len(users['value'])} users")
        return {"users": users['value']}
    else:
        ctx.log("error", f"Failed to get users: {response.status_code}")
        raise Exception(f"Microsoft Graph API error: {response.status_code}")
```

Bifrost automatically handles:
- Token refresh when tokens expire
- Secure token storage in Azure Key Vault
- Token expiration checking
- Per-organization credential isolation

## Understanding OAuth Flows

Bifrost supports different OAuth 2.0 flows depending on your needs:

### Authorization Code Flow (User Login)

Use this when:
- Users need to authorize your app to access their account
- You're building workflows that act on behalf of a user

Example: Workflows that create users, manage licenses, send emails on behalf of admins.

**Flow:**
1. User clicks "Authorize" in Bifrost
2. Redirected to provider's login page
3. User grants permissions
4. Provider redirects back with authorization code
5. Bifrost exchanges code for access + refresh tokens
6. Tokens stored in Key Vault, workflow can use them

### Client Credentials Flow (Service Account)

Use this when:
- Your app authenticates as itself (not a user)
- You need consistent credentials that don't require user interaction
- You're running scheduled workflows

Example: Scheduled reports, automated user sync, system maintenance tasks.

**Flow:**
1. You provide client ID and secret
2. Bifrost directly exchanges for access token (no user login needed)
3. Token stored in Key Vault, workflow can use it
4. Bifrost automatically refreshes when token expires

## Common OAuth Providers

### Microsoft Graph

**Setup time:** 15 minutes

Use for:
- User and group management
- License management
- Exchange Online
- SharePoint Online
- Teams management

**Common Scopes:**
```
User.ReadWrite.All           # Create, update, delete users
Group.ReadWrite.All          # Manage groups
Directory.ReadWrite.All      # Full directory access
Mail.Send                     # Send emails
Calendar.ReadWrite            # Manage calendars
```

### Google Workspace

**Setup time:** 15 minutes

Use for:
- Gmail management
- Google Drive access
- Calendar integration
- Workspace user management

### HaloPSA

**Setup time:** 20 minutes

Use for:
- Ticket management
- Time tracking
- Billing integration
- Client synchronization

### Custom OAuth Providers

Bifrost supports any OAuth 2.0 compliant provider. During setup, you provide:
- Authorization URL
- Token URL
- Client ID and Secret
- Required scopes
- Redirect URI

## Troubleshooting OAuth Setup

### "Invalid redirect URI"

Make sure the redirect URI in Bifrost exactly matches what's registered with your provider:
- Check protocol (http vs https)
- Check trailing slashes
- Check connection name spelling
- Make sure it's not just the domain, but the full path

### "Authorization failed - Invalid client"

- Verify client ID is correct
- Verify client secret is correct (if required by provider)
- Check that the OAuth application is enabled

### "Token exchange failed"

- Verify the authorization code is still valid (codes expire quickly)
- Verify redirect URI used during token exchange matches the authorization URL
- Check that scopes haven't changed since authorization

### "No refresh token returned"

Some OAuth providers don't return refresh tokens. This means:
- The connection will work until the access token expires
- After expiration, you'll need to re-authorize
- If this is a problem, check the provider's settings for "offline access" or "consent" options

## Best Practices

### 1. Use Service Accounts for Scheduled Workflows

For background jobs, use client credentials flow with a service account:

```python
# Good: Uses dedicated service account credentials
@workflow(
    name="nightly_user_sync",
    execution_mode="scheduled",
    schedule="0 2 * * *"  # 2 AM daily
)
async def sync_users(ctx):
    oauth = await ctx.get_oauth_connection("service-account-graph")
    # ...
```

### 2. Limit OAuth Scopes

Only request the permissions you need:

```python
# Good: Minimal scopes
scopes = ["User.Read", "Group.Read"]

# Bad: Excessive permissions
scopes = ["Directory.AccessAsUser.All"]
```

### 3. Handle Token Refresh Errors

Always handle the case where token refresh might fail:

```python
async def get_users(ctx):
    try:
        oauth = await ctx.get_oauth_connection("microsoft-graph")
    except Exception as e:
        ctx.log("error", "OAuth connection failed", {
            "error": str(e),
            "action": "Re-authorize the connection"
        })
        raise
```

### 4. Store Sensitive Configuration

Use secrets for client IDs and secrets:

```python
# In configuration: store reference to secret
config = {
    "client_secret": {"secret_ref": "oauth_client_secret"}
}

# In workflow: automatically resolved from Key Vault
async def workflow(ctx):
    secret = ctx.get_config("client_secret")  # Fetched from Key Vault
```

### 5. Monitor Token Expiration

Check if tokens are about to expire:

```python
import asyncio
from datetime import datetime, timedelta

async def list_users(ctx):
    oauth = await ctx.get_oauth_connection("microsoft-graph")

    expires_at = datetime.fromisoformat(oauth.get("expires_at", ""))
    time_until_expiry = (expires_at - datetime.utcnow()).total_seconds()

    if time_until_expiry < 300:  # Less than 5 minutes
        ctx.log("warning", "Token expiring soon", {
            "seconds_until_expiry": time_until_expiry
        })
```

## Next Steps

- [OAuth Setup Guide](/guides/integrations/oauth-setup) - Detailed setup instructions
- [Microsoft Graph Integration](/guides/integrations/microsoft-graph) - Graph-specific examples
- [Custom APIs](/guides/integrations/custom-apis) - Integrating other APIs
- [Secrets Management](/guides/integrations/secrets-management) - Securing sensitive data
