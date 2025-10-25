---
title: "Scopes: Global vs Organization"
description: "Understanding scope in Bifrost: what makes data global vs organization-specific"
---

Scope determines whether something is platform-wide (Global) or tenant-specific (Organization). This is fundamental to Bifrost's multi-tenant architecture.

## What is Scope?

Scope is the "level" at which a resource exists:

- **Global**: Applies platform-wide, available to all organizations
- **Organization**: Specific to one organization, isolated from others

## Global Scope

Global resources apply to the entire platform:

### Global OAuth Connections

OAuth connections that all organizations can use:

```
Name: shared-graph-connection
Scope: GLOBAL
Accessible to: All organizations
Purpose: Centralized Microsoft Graph connection
```

Use case: Your platform manages Microsoft Graph connection centrally, all customers use the same credentials.

### Global Configuration

Platform-wide settings:

```
Global Config:
- smtp_server: mail.example.com
- default_timezone: UTC
- api_rate_limit: 1000/minute
```

Accessible to: All workflows and organizations

### Global Secrets

Secrets available platform-wide:

```
Secret: shared_api_key (GLOBAL)
Accessible to: All organizations
Purpose: Third-party service key
```

## Organization Scope

Organization resources are isolated per tenant:

### Organization OAuth Connections

OAuth connections specific to one organization:

```
Name: microsoft-graph
Org: ACME Corp
Credentials: ACME's own Azure AD app
Scope: ACME only - not visible to other orgs
```

Each organization has their own Microsoft Graph connection with their own credentials.

### Organization Configuration

Settings specific to an organization:

```
Config for ACME Corp:
- smtp_server: mail.acme.local
- default_timezone: America/Denver
- api_rate_limit: 5000/minute

Config for TechCorp:
- smtp_server: mail.tech.local
- default_timezone: America/New_York
- api_rate_limit: 2000/minute
```

### Organization Secrets

Secrets isolated per organization:

```
Secret: api_key (Organization: ACME Corp)
Secret: api_key (Organization: TechCorp)

These are completely separate secrets!
ACME's api_key ≠ TechCorp's api_key
```

Naming: `{org_id}--{secret_name}`

Example: `acme-corp--api_key`, `techcorp--api_key`

## Scope in Workflows

### Accessing Global vs Organization Data

```python
from bifrost import workflow, context

@workflow(name="scope_example")
async def scope_example(ctx: context.WorkflowContext):
    """Show how scope resolution works."""
    
    # Get config with fallback: org → global
    # First tries ACME's config
    # If not found, tries GLOBAL config
    smtp = ctx.get_config("smtp_server")
    
    # Get OAuth connection with fallback: org → global
    # First tries ACME's "microsoft-graph"
    # If not found, tries GLOBAL "microsoft-graph"
    oauth = await ctx.get_oauth_connection("microsoft-graph")
    
    # Get secret with org scope only
    # Only ACME's secrets, not global
    api_key = await ctx.get_secret("api_key")
```

### Scope Resolution Order

When accessing a resource, Bifrost checks in order:

```
1. Organization-specific
   └─ Is there an org-level version?
      
2. Global fallback
   └─ If not found in org, check global
      
3. Error
   └─ If not found in either, error
```

Example for OAuth connection:

```python
# Looking for "microsoft-graph"
oauth = await ctx.get_oauth_connection("microsoft-graph")

# Bifrost checks:
# 1. "microsoft-graph" in ACME Corp org? YES → use it
# 2. "microsoft-graph" in GLOBAL? (skipped)
# 3. Use ACME's org-level connection

# OR if org doesn't have it:
# 1. "microsoft-graph" in TechCorp org? NO
# 2. "microsoft-graph" in GLOBAL? YES → use it
# 3. Use global connection as fallback
```

## When to Use Each Scope

### Use Global Scope When

1. **Shared Infrastructure**
   ```
   OAuth Connection: Vendor's API
   Scope: GLOBAL
   Reason: Bifrost platform manages vendor relationship
   ```

2. **Platform Standards**
   ```
   Config: SMTP server, logging level, timezone
   Scope: GLOBAL
   Reason: Same for all organizations
   ```

3. **Central Services**
   ```
   Secret: Master API key for platform service
   Scope: GLOBAL
   Reason: One key for all organizations
   ```

### Use Organization Scope When

1. **Customer-Specific Integrations**
   ```
   OAuth Connection: Customer's Microsoft Graph
   Scope: Organization
   Reason: Each customer has their own credentials
   ```

2. **Tenant-Specific Configuration**
   ```
   Config: Customer's timezone, department names
   Scope: Organization
   Reason: Different for each customer
   ```

3. **Customer Secrets**
   ```
   Secret: API key from customer's third-party service
   Scope: Organization
   Reason: Each customer has own credentials
   ```

## Real-World Examples

### Example 1: Multi-Tenant SaaS

```
Platform: Bifrost Integration Service (MSP)

Global Resources:
├─ OAuth: "stripe-payments" (Bifrost's Stripe account)
├─ Config: smtp_server = "mail.bifrost.com"
└─ Secret: "platform_key" (Bifrost's internal key)

Organization: ACME Corp
├─ OAuth: "microsoft-graph" (ACME's own Azure AD)
├─ OAuth: "slack-workspace" (ACME's Slack workspace)
├─ Config: acme_timezone = "America/Denver"
└─ Secret: "acme_api_key" (ACME's Hubspot API key)

Organization: TechCorp
├─ OAuth: "microsoft-graph" (TechCorp's own Azure AD)
├─ Config: techcorp_timezone = "America/New_York"
└─ Secret: "techcorp_api_key" (TechCorp's Salesforce API key)
```

Workflow execution:

```python
# Same workflow runs for both organizations

@workflow(name="sync_crm_data")
async def sync_crm_data(ctx):
    # For ACME Corp execution:
    crm_key = await ctx.get_secret("acme_api_key")
    timezone = ctx.get_config("acme_timezone")
    
    # For TechCorp execution:
    crm_key = await ctx.get_secret("techcorp_api_key")
    timezone = ctx.get_config("techcorp_timezone")
    
    # Each organization uses its own secrets/config!
```

### Example 2: Shared vs Custom OAuth

```
Global OAuth: "platform-audit-log-service"
├─ Purpose: All orgs send logs to shared logging service
├─ Credentials: Bifrost's service account
└─ Used by: All organizations automatically

Organization OAuth: "microsoft-graph"
├─ Purpose: Sync users with customer's Azure AD
├─ Credentials: Customer's own Azure AD app
└─ Used by: That organization only
```

## Scope in Forms

Forms can use scoped data:

```python
@data_provider(name="get_departments")
async def get_departments(ctx: context.WorkflowContext):
    """Get departments for this organization."""
    
    # Automatically uses org context
    org_id = ctx.org_id
    
    # Gets org-specific departments
    departments = await ctx.get_config("org.departments")
    
    return [
        {"label": dept, "value": dept}
        for dept in departments
    ]

@workflow(name="user_provisioning")
@param("department", data_provider="get_departments")
async def user_provisioning(ctx, department: str):
    """Form shows this org's departments."""
    pass
```

When ACME Corp uses the form, they see ACME's departments.
When TechCorp uses the form, they see TechCorp's departments.

## Security Implications

### Complete Isolation

Organization scope provides security isolation:

```python
# This is secure:
# Even if the code is the same,
# each org only accesses its own data

# Org A workflow:
secret = await ctx.get_secret("api_key")  # Gets Org A's key

# Org B workflow:
secret = await ctx.get_secret("api_key")  # Gets Org B's key

# Never can leak between organizations
```

### No Cross-Org Leakage

Organization scope prevents accidental data leaks:

```python
# Even if developer tries to access other org:
# ctx.org_id is ACME
# Can only access ACME's secrets and config

# Cannot do this:
secret = await ctx.get_secret("api_key", org_id="other-org")
# Returns: error - cannot access other organization
```

### Audit Trail

All access is tracked with organization context:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "organization_id": "acme-corp",
  "action": "get_secret",
  "secret_name": "api_key",
  "user_id": "user-123",
  "result": "success"
}
```

## Best Practices

### 1. Default to Organization Scope

```python
# Good: org-specific secrets
org_secret = await ctx.get_secret("api_key")

# Only use global if explicitly needed
global_secret = await ctx.get_global_secret("platform_key")
```

### 2. Clear Naming

```python
# Global: descriptive, uppercase pattern
GLOBAL_CONFIG: "smtp_server"

# Organization: org name included or obvious context
ORG_CONFIG: "office_location"  # specific to this org
```

### 3. Document Scope Decisions

```python
@workflow(name="sync_data")
async def sync_data(ctx):
    """
    Sync data with CRM.
    
    Uses:
    - Organization OAuth "crm_oauth" (org-specific)
    - Global config "crm_base_url" (shared platform config)
    """
    oauth = await ctx.get_oauth_connection("crm_oauth")
    url = ctx.get_config("crm_base_url")
```

### 4. Test with Multiple Organizations

```python
# Test workflow with:
# - Organization A data
# - Organization B data
# - Verify no data leakage
```

## Troubleshooting

### "Secret Not Found"

Check:
1. Is secret name correct?
2. Is secret at right scope?
   - Organization level? (check org-prefixed name)
   - Global level? (check without org prefix)
3. Does your org have this secret?

### "Cannot Access Other Organization's Data"

This is correct behavior:
- Organization isolation is working properly
- You can only access your org's data
- Ask OrgAdmin to add you to other org if needed

### Global Config Not Applied

Check:
1. Organization has its own config (overrides global)
2. Delete org config to use global fallback
3. Verify global config exists

## Reference

- [Getting Started](/tutorials/quickstart) - Basic scope concepts
- [Platform Overview](/guides/platform-overview) - Multi-tenant architecture
- [Security Model](/reference/architecture/security) - Isolation guarantees
