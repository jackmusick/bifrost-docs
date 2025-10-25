---
title: OAuth Troubleshooting
description: Diagnose and fix common OAuth connection issues
---

# OAuth Troubleshooting

OAuth connections enable Bifrost to securely access external APIs like Microsoft Graph, HaloPSA, and custom services. This guide helps you diagnose and resolve common OAuth issues.

## Common OAuth Issues

### Authorization Failed

**Symptom**: "Authorization failed" error when trying to connect to a service

#### Step 1: Verify Provider Configuration

Check that the OAuth provider is properly configured:

```bash
# In the Bifrost admin UI:
1. Navigate to Settings → OAuth Providers
2. Select the provider (e.g., "HaloPSA", "Microsoft Graph")
3. Verify:
   - Client ID is set
   - Client Secret is configured
   - Redirect URI matches your deployment URL
```

**Common redirect URI mistakes:**

```
❌ https://bifrost.example.com       (missing /api/oauth/callback)
✅ https://bifrost.example.com/api/oauth/callback

❌ http://localhost:7071/            (HTTP in production)
✅ https://bifrost.example.com/api/oauth/callback (HTTPS only)

❌ https://api.bifrost.example.com   (different domain)
✅ https://bifrost.example.com/api/oauth/callback
```

#### Step 2: Check User Permissions

Ensure the user initiating OAuth has authorization:

- **At least** a "User" role in Bifrost
- Permission to create OAuth connections for their organization
- Not blocked by IP restrictions or MFA policies

#### Step 3: Verify OAuth Provider is Accessible

Test connectivity to the OAuth provider:

```bash
# For Microsoft (Graph)
curl -I https://login.microsoftonline.com/common/oauth2/v2.0/authorize

# For HaloPSA
curl -I https://oauth.halotechnologies.com/oauth2/authorize

# For other providers
curl -I <provider-oauth-url>
```

All should return `2xx` status (not `5xx` or `0` responses).

#### Step 4: Check Browser Console

During authorization, browser console may show errors:

1. Open **Developer Tools** (F12)
2. Go to **Console** tab
3. Look for error messages about:
   - Cross-origin requests (CORS)
   - Popup blocked
   - Redirect issues
4. Check **Network** tab to see actual redirect responses

### Token Expired Error

**Symptom**: "OAuth token expired" when executing a workflow

#### Understanding Token Expiration

OAuth tokens have lifetimes:

```
├── Access Token
│   ├── Lifetime: 1 hour (typical)
│   ├── Status: Used to make API calls
│   └── When expired: Need refresh
│
└── Refresh Token
    ├── Lifetime: 90 days - indefinite
    ├── Status: Used to get new access tokens
    └── When expired: Re-authorize required
```

#### Solution: Automatic Token Refresh

Bifrost automatically refreshes tokens before they expire. If you see a token expired error:

**For sync workflows** (execute immediately):
```python
from bifrost import ExecutionContext

async def my_workflow(context: ExecutionContext):
    # Token is automatically refreshed here if needed
    creds = await context.get_oauth_connection("HaloPSA")
    # creds.access_token is guaranteed to be fresh
```

**For scheduled workflows** (run in background):
```python
@workflow(execution_mode="scheduled", schedule="0 9 * * 1")
async def nightly_sync(context: ExecutionContext):
    # Even with automatic refresh, long workflows might hit timeout
    # Recommendation: Split into smaller pieces
    creds = await context.get_oauth_connection("HaloPSA")
```

**If token refresh fails:**

1. **Check refresh token is valid**:
   - Re-authorize the connection
   - Go to Settings → OAuth Connections
   - Click the refresh icon next to the connection
   - Complete the authorization flow again

2. **Check token wasn't revoked**:
   - User may have revoked access in their provider account
   - In Microsoft 365: Settings → Connected apps and websites
   - In HaloPSA: Account → Connected Apps

### Scope Mismatch Error

**Symptom**: "Requested scopes not available" or "Insufficient permissions"

#### Understanding OAuth Scopes

Scopes define what data an app can access:

```
Microsoft Graph scopes:
- user.read          → Read user profile
- user.readwrite     → Modify user profile
- mail.send          → Send emails
- calendars.readwrite → Manage calendar

HaloPSA scopes:
- read:tickets       → Read ticket data
- write:tickets      → Create/modify tickets
- read:clients       → Read client data
```

#### Solution: Check Requested Scopes

1. **In Bifrost settings:**
   ```
   Settings → OAuth Providers → [Provider] → Scopes
   ```

2. **Verify required scopes are included**

3. **Re-authorize with new scopes:**
   - If you add scopes, users must re-authorize
   - Click "Reconnect" to start authorization flow again

4. **Common scope issues:**

   ```
   ❌ Typo in scope name
   ✅ Exact scope as documented by provider

   ❌ Requesting retired/removed scope
   ✅ Use current scope names from provider docs

   ❌ Requesting scopes not available for your app type
   ✅ Check app registration (some scopes need admin consent)
   ```

### Redirect URI Mismatch

**Symptom**: "redirect_uri mismatch" or "invalid redirect URL" during authorization

This is one of the most common OAuth errors.

#### Solution

The redirect URI must match **exactly** (including protocol, domain, and path):

```
# In OAuth Provider Settings:
Authorized Redirect URLs:
  https://your-bifrost.com/api/oauth/callback

# Your Bifrost deployment URL:
  https://your-bifrost.com

# These must be the same for authorization to work!
```

**Update redirect URI:**

**For Azure Function App:**

```bash
# 1. Find your Function App URL
echo "Your Bifrost URL is:"
az functionapp show --resource-group <rg> --name <name> \
  --query "hostNames" -o json

# Expected output:
# "bifrost-prod.azurewebsites.net"

# 2. Construct full redirect URI
# https://bifrost-prod.azurewebsites.net/api/oauth/callback

# 3. Update OAuth provider settings
#    - Go to provider (e.g., Microsoft Entra, HaloPSA)
#    - Update "Redirect URI" or "Reply URL"
#    - Save

# 4. Test authorization flow
```

**For local development:**

```
http://localhost:7071/api/oauth/callback
```

Note: Local development uses HTTP (not HTTPS).

### Connection Lost Error

**Symptom**: "Connection lost" or "Failed to authenticate" during authorization

#### Check 1: Network Connectivity

```bash
# Test connection to OAuth provider
ping oauth.halotechnologies.com
ping login.microsoftonline.com

# Test from your network
curl https://oauth.halotechnologies.com/oauth2/authorize
```

#### Check 2: Firewall/Network Rules

If your organization has network restrictions:

```
Bifrost → OAuth Provider

Verify firewall allows outbound:
  ✓ Port 443 (HTTPS)
  ✓ Domains for OAuth providers
  ✓ Not blocked by VPN/proxy
```

#### Check 3: Browser Issues

```
❌ Using old browser without TLS 1.2 support
✅ Use modern browser (Chrome, Edge, Firefox 60+)

❌ Browser cookies/cache issue
✅ Try incognito mode

❌ Browser extension blocking requests
✅ Try disabling extensions temporarily
```

### Invalid Client Error

**Symptom**: "invalid_client" or "client authentication failed"

#### Solution

This means the Client ID or Client Secret is incorrect or expired:

**Check 1: Verify Client ID and Secret**

```bash
# In Bifrost:
Settings → OAuth Providers → [Provider]

# Paste Client ID:
✅ Starts with correct format (e.g., GUID for Microsoft)
❌ Accidentally includes "Client ID: " prefix
❌ Includes newlines or extra spaces

# Paste Client Secret:
✅ Full secret (not truncated)
❌ Expired secret (check expiration date)
```

**Check 2: Regenerate Credentials**

If secret has expired:

1. Go to your OAuth provider account
2. Find app registration (e.g., Azure Entra, HaloPSA developer portal)
3. Generate new secret
4. Update in Bifrost

**Check 3: Check for Special Characters**

Some special characters in Client Secret can cause issues:

```
✅ Alphanumeric, dash, underscore, tilde
❌ If secret contains special chars, ensure they're correctly escaped
```

## Advanced Troubleshooting

### Check OAuth Token Status

**View token details:**

```python
# In a workflow
from bifrost import ExecutionContext

async def check_token(context: ExecutionContext):
    try:
        creds = await context.get_oauth_connection("HaloPSA")

        # Check expiration
        if creds.is_expired():
            context.log("warning", "Token is expired")
        else:
            context.log("info", "Token is valid")
            context.log("info", f"Expires in: {creds.expires_in} seconds")

        # Check scope
        context.log("info", f"Granted scopes: {creds.scopes}")

    except Exception as e:
        context.log("error", f"Failed to get credentials: {str(e)}")
```

### Test API Call with Token

**Verify token works:**

```python
import aiohttp
from bifrost import ExecutionContext

async def test_api_call(context: ExecutionContext):
    creds = await context.get_oauth_connection("HaloPSA")

    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": creds.get_auth_header(),
            "Accept": "application/json"
        }

        async with session.get(
            "https://api.halopsa.com/api/me",
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                context.log("info", f"API call succeeded: {data}")
            elif response.status == 401:
                context.log("error", "Token is invalid or expired")
            elif response.status == 403:
                context.log("error", "Insufficient scope for this API")
            else:
                context.log("error", f"API error: {response.status}")
```

### Check Connection in Production

**View stored tokens:**

```bash
# Connect to Azure Key Vault (where tokens are stored)
az keyvault secret list --vault-name <your-vault>

# Look for secrets with names like:
# bifrost-oauth-halopsa-org-id-12345
# bifrost-oauth-msgraph-org-id-12345

# View expiration info
az keyvault secret show \
  --vault-name <vault> \
  --name bifrost-oauth-halopsa-org-id-12345
```

## Common Provider-Specific Issues

### Microsoft Graph (Azure AD/Microsoft 365)

**Issue: "AADSTS*" error codes**

These are Azure AD-specific errors. Common ones:

```
AADSTS65001  → User denied consent
Fix: User needs to approve scopes during auth

AADSTS7000112 → App disabled or consent disabled
Fix: Check app is enabled in Azure Entra

AADSTS9002313 → Rate limiting
Fix: Wait a bit, retry with exponential backoff
```

**Issue: Microsoft 365 license check fails**

```python
# Some operations require specific licenses
# Example: Assigning E5 features when user has E3

# Check license before operation
from bifrost import ExecutionContext

async def assign_e5_feature(context: ExecutionContext, user_id: str):
    # First verify user has E5 license
    graph = context.get_integration("msgraph")
    user = await graph.users.get(user_id)

    if "SPE_E5" not in user.get("assignedLicenses", []):
        raise Exception("User must have E5 license for this feature")

    # Safe to proceed with E5-only operations
```

### HaloPSA

**Issue: "Authentication failed"**

HaloPSA OAuth often requires additional setup:

1. Check client IP is whitelisted (HaloPSA → Settings)
2. Verify OAuth user has appropriate permissions
3. Check token wasn't revoked in HaloPSA admin

**Issue: API returns 429 (Rate Limited)**

HaloPSA has strict rate limits:

```python
# Implement exponential backoff
import asyncio
import aiohttp

async def api_call_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 429:
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                        continue
                    return await response.json()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
```

## Testing OAuth Connections

### Local Development Setup

For testing OAuth locally:

1. **Update OAuth provider settings:**
   - Add redirect URI: `http://localhost:7071/api/oauth/callback`
   - Note: HTTP (not HTTPS) for local development only

2. **Test in local environment:**
   ```bash
   # Start local Function App
   func start

   # Visit Bifrost admin
   http://localhost:5173

   # Settings → OAuth Connections → Connect
   ```

### Integration Testing

**Automated OAuth tests:**

```python
# tests/integration/test_oauth.py
import pytest
from bifrost import ExecutionContext

@pytest.mark.integration
async def test_oauth_token_refresh():
    """Verify token auto-refresh works"""
    context = await get_test_context()

    # Should not raise, even if token is near expiration
    creds = await context.get_oauth_connection("HaloPSA")
    assert creds is not None
    assert creds.access_token is not None
    assert not creds.is_expired()
```

## Quick Reference

| Issue | Most Likely Cause | Fix |
|-------|---|---|
| Authorization fails | Provider unreachable or config wrong | Verify redirect URI, client ID, secret |
| Token expired | Token lifetime exceeded | Automatic refresh; if fails, re-authorize |
| Invalid scope | App doesn't have requested scopes | Update provider app registration |
| Redirect URI mismatch | URI doesn't match exactly | Update provider OAuth settings |
| Connection lost | Network/firewall issue | Test connectivity, check firewall |
| Invalid client | Wrong credentials | Verify client ID/secret, regenerate if expired |
| Rate limited | Too many API calls | Add backoff/retry logic to workflows |
| Permission denied | Token lacks required scope | Re-authorize with new scopes |

## Getting Help

- **OAuth Provider Docs**:
  - [Microsoft Graph OAuth](https://learn.microsoft.com/en-us/graph/auth-v2-oauth2-auth-code-flow)
  - [HaloPSA OAuth](https://haloapidocs.halotechnologies.com/)

- **Check Bifrost Logs**:
  - Azure Portal → Function App → Monitoring → Log Stream
  - Look for messages about OAuth refresh, token validation

- **Debug Mode**: Enable debug logging in settings (if available)

## Related Topics

- **[OAuth Configuration](/docs/guides/oauth-setup)** - How to set up OAuth connections
- **[Security](/docs/concepts/security)** - How Bifrost secures tokens
- **[Azure Functions Troubleshooting](/docs/troubleshooting/azure-functions)** - Infrastructure issues
