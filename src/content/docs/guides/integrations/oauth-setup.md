---
title: "Configure OAuth Connections"
description: "Step-by-step guide to setting up OAuth connections with popular providers"
---

This guide covers setting up OAuth connections in Bifrost for different providers and use cases.

## Understanding Connection Setup

Every OAuth connection in Bifrost has these steps:

1. **Create OAuth Application** - Register your app with the provider
2. **Gather Credentials** - Get client ID, secret, and other identifiers
3. **Configure Redirect URI** - Tell provider where to send the auth code
4. **Create Connection in Bifrost** - Set up the connection record
5. **Authorize Connection** - Complete OAuth flow to get tokens
6. **Test and Monitor** - Verify it works and monitor status

## Microsoft Graph Setup

Microsoft Graph is the API for Microsoft 365 services (Azure AD, Exchange, SharePoint, Teams).

### Prerequisites

- Azure subscription with admin access
- Microsoft 365 tenant

### Step 1: Register Application

1. Go to [Azure Portal](https://portal.azure.com)
2. Search for "Azure Active Directory" or "Entra"
3. Select **App registrations** → **+ New registration**
4. Fill in form:
   - **Name**: "Bifrost Integration" (or your naming convention)
   - **Supported account types**: 
     - "Accounts in this organizational directory only" (single tenant)
     - "Accounts in any organizational directory" (multi-tenant)
   - **Redirect URI**: Leave blank for now
5. Click **Register**
6. Save these values:
   - **Application (client) ID**
   - **Directory (tenant) ID**

### Step 2: Configure Secrets

1. In app registration, select **Certificates & secrets**
2. Click **+ New client secret**
3. Fill in:
   - **Description**: "Bifrost API Key"
   - **Expires**: "24 months" or longer
4. Click **Add**
5. Copy the secret value immediately (hidden after page reload)

### Step 3: Configure API Permissions

1. Select **API permissions**
2. Click **+ Add a permission**
3. Select **Microsoft Graph**
4. Choose permission type:
   - **Delegated permissions** - Act on behalf of signed-in user
   - **Application permissions** - Act as the app itself

5. Add required permissions based on your use case:

**User Management:**
```
User.ReadWrite.All           # Create, update, delete users
Directory.ReadWrite.All      # Full directory access
```

**Group Management:**
```
Group.ReadWrite.All          # Create, update, delete groups
GroupMember.ReadWrite.All    # Manage group members
```

**License Management:**
```
User.ReadWrite.All           # Required for license assignment
```

**Mail:**
```
Mail.Send                     # Send emails
Mail.ReadWrite                # Read and manage mail
```

6. After adding permissions, click **Grant admin consent** (required for application permissions)

### Step 4: Configure Redirect URI

1. Select **Authentication** in your app registration
2. Under **Platform configurations**, click **+ Add a platform**
3. Select **Web**
4. Add Redirect URI: `https://your-domain.com/oauth/callback/microsoft-graph`
   - For development: `https://localhost:5173/oauth/callback/microsoft-graph`
5. Under **Implicit grant and hybrid flows**, check:
   - Access tokens
   - ID tokens
6. Click **Save**

### Step 5: Create Connection in Bifrost

In Bifrost admin panel, go to **Integrations → OAuth Connections**:

```
Connection Name: microsoft-graph (or custom name)
OAuth Flow Type: authorization_code
Client ID: [your-application-id]
Client Secret: [your-client-secret-value]
Authorization URL: https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize
Token URL: https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
Scopes: User.ReadWrite.All Group.ReadWrite.All (space-separated)
Redirect URI: https://your-domain.com/oauth/callback/microsoft-graph
```

Replace `{tenant}` with your actual tenant ID.

### Step 6: Authorize Connection

1. In Bifrost, click the connection to open details
2. Click **Authorize**
3. Sign in with admin account
4. Grant permissions when prompted
5. Confirm successful connection

### Scopes by Use Case

**User Lifecycle Management:**
```
User.ReadWrite.All          # Create/update/delete users
Directory.ReadWrite.All     # Access all directory APIs
```

**License Management:**
```
User.ReadWrite.All          # Required for license assignment
```

**Group Management:**
```
Group.ReadWrite.All         # Create/update/delete groups
GroupMember.ReadWrite.All   # Manage memberships
```

**Email/Calendar:**
```
Mail.Send                    # Send emails
Mail.ReadWrite               # Full mail access
Calendar.ReadWrite           # Manage calendars
```

**Teams Management:**
```
Team.ReadWrite.All          # Manage teams
TeamMember.ReadWrite.All    # Manage team members
```

## HaloPSA Setup

HaloPSA is a Professional Services Automation (PSA) platform.

### Prerequisites

- HaloPSA tenant with admin access
- HaloPSA API credentials

### Step 1: Create API Integration

In HaloPSA:

1. Go to **Settings → API → OAuth Applications**
2. Click **Add New**
3. Fill in:
   - **Name**: "Bifrost"
   - **Redirect URLs**: `https://your-domain.com/oauth/callback/halopsa`
4. Save
5. Note the **Client ID** and **Client Secret**

### Step 2: Gather Connection Details

From HaloPSA:
- **Client ID**: From OAuth application
- **Client Secret**: From OAuth application
- **Authorization URL**: `https://your-halopsa-instance.halopsa.com/oauth/authorize`
- **Token URL**: `https://your-halopsa-instance.halopsa.com/oauth/token`
- **Scopes**: Based on HaloPSA documentation (e.g., `tickets:read tickets:write`)

### Step 3: Create Connection in Bifrost

In Bifrost:

```
Connection Name: halopsa
OAuth Flow Type: authorization_code
Client ID: [halopsa-client-id]
Client Secret: [halopsa-client-secret]
Authorization URL: https://your-instance.halopsa.com/oauth/authorize
Token URL: https://your-instance.halopsa.com/oauth/token
Scopes: tickets:read tickets:write clients:read clients:write
Redirect URI: https://your-domain.com/oauth/callback/halopsa
```

### Step 4: Authorize Connection

Follow the standard authorization flow.

### Common Scopes

```
tickets:read                 # Read tickets
tickets:write                # Create/update/delete tickets
clients:read                 # Read client information
clients:write                # Create/update/delete clients
time_entries:read            # Read time tracking
time_entries:write           # Create/update/delete time entries
```

## Google Workspace Setup

### Prerequisites

- Google Cloud Project
- Google Workspace domain

### Step 1: Create OAuth Application

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project or select existing
3. Go to **APIs & Services → Credentials**
4. Click **+ Create Credentials → OAuth client ID**
5. Application type: **Web application**
6. Fill in:
   - **Name**: "Bifrost"
   - **Authorized JavaScript origins**: `https://your-domain.com`
   - **Authorized redirect URIs**: `https://your-domain.com/oauth/callback/google-workspace`
7. Click **Create**
8. Save **Client ID** and **Client Secret**

### Step 2: Enable Required APIs

1. Go to **APIs & Services → Library**
2. Search for and enable:
   - Google Calendar API
   - Gmail API
   - Google Drive API
   - Google Workspace Directory API
   - (Others as needed)

### Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services → OAuth consent screen**
2. User type: "Internal" or "External"
3. Fill in:
   - **App name**: "Bifrost"
   - **User support email**: your email
   - **Scopes**: Select the ones you need
4. Save

### Step 4: Create Connection in Bifrost

```
Connection Name: google-workspace
OAuth Flow Type: authorization_code
Client ID: [your-client-id]
Client Secret: [your-client-secret]
Authorization URL: https://accounts.google.com/o/oauth2/v2/auth
Token URL: https://oauth2.googleapis.com/token
Scopes: https://www.googleapis.com/auth/admin.directory.user https://www.googleapis.com/auth/calendar
Redirect URI: https://your-domain.com/oauth/callback/google-workspace
```

## Custom OAuth Provider Setup

For any OAuth 2.0 compliant provider:

### Information You Need

From your provider's OAuth documentation:

- **Client ID** - Unique identifier for your app
- **Client Secret** - Secret key (keep this private)
- **Authorization URL** - Where users sign in
- **Token URL** - Where you exchange codes for tokens
- **Scopes** - What permissions to request
- **Redirect URI** - Where to send users after auth

### Creating Connection

In Bifrost:

```
Connection Name: [custom-name]
OAuth Flow Type: authorization_code (or client_credentials)
Client ID: [from-provider]
Client Secret: [from-provider]
Authorization URL: [from-provider-docs]
Token URL: [from-provider-docs]
Scopes: [space-separated-scopes]
Redirect URI: https://your-domain.com/oauth/callback/[custom-name]
```

### Client Credentials Flow

For server-to-server authentication (no user involved):

```
Connection Name: [service-name]
OAuth Flow Type: client_credentials
Client ID: [from-provider]
Client Secret: [from-provider]
Token URL: [from-provider-docs]
Scopes: [required-scopes]
```

With client credentials, no redirect URI is needed. Bifrost automatically exchanges credentials for tokens.

## Monitoring OAuth Connections

### Check Connection Status

In Bifrost admin panel, each connection shows:

- **Status**: 
  - `not_connected` - Initial state
  - `waiting_callback` - Authorization in progress
  - `completed` - Ready to use
  - `failed` - Authorization failed

- **Last Updated**: When token was last refreshed
- **Expires At**: When access token expires
- **Status Message**: Details about current state

### Manual Token Refresh

If a token expires or becomes invalid:

1. Click the connection
2. Click **Refresh Token**
3. Bifrost attempts to refresh using the refresh token
4. If refresh fails, you may need to re-authorize

### Troubleshooting Connection Issues

**"Connection failed" status:**
- Check Client ID and Secret are correct
- Verify scopes are valid for provider
- Ensure redirect URI matches provider configuration

**"Waiting for callback" stuck:**
- Authorization code may have expired (typically 10 minutes)
- Try authorizing again
- Check redirect URI configuration

**Token refresh failing:**
- Provider may have revoked refresh token
- User may have changed password or revoked app access
- Re-authorize the connection

## Security Best Practices

### 1. Secure Secret Storage

Never commit client secrets to version control:

```bash
# Bad: Secrets in code
HALOPSA_SECRET="abc123xyz"

# Good: Use Key Vault reference
config = {"client_secret": {"secret_ref": "halopsa-secret"}}
```

### 2. Rotate Secrets Regularly

- Plan to rotate OAuth secrets every 12-24 months
- Create new secret before old one expires
- Update in Bifrost
- Delete old secret from provider

### 3. Minimal Scopes

Request only the permissions you need:

```python
# Good: Minimal
scopes = ["User.Read"]

# Bad: Excessive
scopes = ["Directory.AccessAsUser.All", "Mail.Send", "*"]
```

### 4. Separate Accounts for Different Purposes

- User-level connections: Use a shared service account
- Service workflows: Use separate service accounts per workflow

### 5. Monitor Access

- Review connection access logs regularly
- Alert on unexpected connection usage
- Revoke connections that are no longer needed

## Reference

- [Microsoft Graph Documentation](https://docs.microsoft.com/graph)
- [HaloPSA API Documentation](https://haloPSA.com/api-docs)
- [Google Workspace API Documentation](https://developers.google.com/workspace)
- [OAuth 2.0 Specification](https://tools.ietf.org/html/rfc6749)
