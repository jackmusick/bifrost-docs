---
title: "Manage Secrets Securely"
description: "Best practices for managing secrets and sensitive data in Bifrost"
---

Secrets are sensitive credentials like API keys, passwords, and tokens. Bifrost provides enterprise-grade secret management through Azure Key Vault integration with organization-level isolation.

## Understanding Secret Management

### What is a Secret?

A secret is any sensitive data that should not be visible in logs or version control:
- OAuth tokens and refresh tokens
- API keys and API secrets
- Database connection strings
- SSH private keys
- Certificates and PEM files
- Service account passwords

### Secret Storage

Bifrost stores secrets in **Azure Key Vault** with these protections:
- Encryption at rest
- Encryption in transit (TLS)
- Access control via managed identity
- Audit logging of all access
- Soft delete and purge protection

### Organization Isolation

Every secret is scoped to an organization using naming convention:

```
{organization_id}--{secret_name}
```

Example: `client-acme--api-key` (secret for ACME organization)

This ensures:
- Users can only access their organization's secrets
- Complete isolation between tenants
- Secrets never leak between organizations

## Creating and Managing Secrets

### Method 1: Bifrost Admin UI

In the Bifrost admin panel:

1. Go to **Configuration → Secrets**
2. Click **+ Create Secret**
3. Fill in:
   - **Secret Name**: `api_key` (no org prefix needed)
   - **Secret Value**: Your actual secret
   - **Description**: What this secret is for
   - **Expires**: Optional expiration date
4. Click **Create**

Bifrost automatically:
- Adds organization prefix
- Encrypts the value
- Stores in Key Vault
- Creates audit log entry

### Method 2: REST API

Create a secret via API:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: client-acme" \
  -H "x-functions-key: your-api-key" \
  -d '{
    "secret_name": "api_key",
    "secret_value": "sk-1234567890abcdef",
    "description": "API key for external service"
  }' \
  https://your-bifrost-domain.com/api/admin/secrets
```

List all secrets for organization:

```bash
curl -X GET \
  -H "X-Organization-Id: client-acme" \
  -H "x-functions-key: your-api-key" \
  https://your-bifrost-domain.com/api/admin/secrets
```

Update a secret:

```bash
curl -X PUT \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: client-acme" \
  -H "x-functions-key: your-api-key" \
  -d '{
    "secret_value": "sk-new-key-9876543210",
    "description": "Updated API key"
  }' \
  https://your-bifrost-domain.com/api/admin/secrets/api_key
```

Delete a secret:

```bash
curl -X DELETE \
  -H "X-Organization-Id: client-acme" \
  -H "x-functions-key: your-api-key" \
  https://your-bifrost-domain.com/api/admin/secrets/api_key
```

## Using Secrets in Workflows

### Direct Access

Retrieve a secret in your workflow:

```python
from bifrost import workflow, context

@workflow(
    name="fetch_data",
    description="Fetch data using API key"
)
async def fetch_data(ctx: context.WorkflowContext):
    # Get secret from Key Vault
    api_key = await ctx.get_secret("api_key")
    
    # Use in API call
    headers = {"Authorization": f"Bearer {api_key}"}
    response = await ctx.http_get(
        "https://api.example.com/data",
        headers=headers
    )
    
    return response.json()
```

### Configuration with Secret References

Store secret references in configuration:

```python
# In organization config
config = {
    "api_settings": {
        "api_key": {
            "secret_ref": "external_api_key"
        },
        "api_url": "https://api.example.com"
    }
}

# In workflow: automatically resolved from Key Vault
async def workflow(ctx):
    # Secret automatically fetched
    api_key = ctx.get_config("api_settings.api_key")
    api_url = ctx.get_config("api_settings.api_url")
```

### Caching and Performance

Bifrost caches secrets during workflow execution to avoid repeated Key Vault calls:

```python
async def process_batch(ctx):
    # First call: fetches from Key Vault (slow ~100ms)
    api_key_1 = await ctx.get_secret("api_key")
    
    # Subsequent calls in same execution: cached (fast <1ms)
    api_key_2 = await ctx.get_secret("api_key")
    
    # Same value, much faster
    assert api_key_1 == api_key_2
```

## Secret Naming Conventions

Use consistent, descriptive naming:

### Good Names

```
# Specific service and purpose
microsoft_graph_client_secret
halopsa_api_key
database_connection_string
smtp_password
sendgrid_api_key

# Includes environment
production_api_key
staging_api_key
```

### Avoid

```
# Too generic
secret
key
password
token
api_key  # Too vague - which API?

# Too specific (might change)
client_acme_api_key  # Don't include org in name
```

## Rotating Secrets

Secrets should be rotated regularly for security.

### Rotation Process

1. **Create New Secret**
   ```
   Create: new_api_key with new value
   ```

2. **Update Application**
   ```
   Update workflow or config to use new secret
   ```

3. **Test**
   ```
   Verify new secret works
   ```

4. **Delete Old Secret**
   ```
   Delete: old_api_key
   ```

### Automated Rotation

Create a scheduled workflow for rotation:

```python
from bifrost import workflow, context
from datetime import datetime, timedelta

@workflow(
    name="rotate_secrets",
    description="Rotate expired secrets",
    execution_mode="scheduled",
    schedule="0 2 * * 0"  # Weekly on Sunday at 2 AM
)
async def rotate_secrets(ctx: context.WorkflowContext):
    """Automatically rotate old secrets."""
    
    secrets_to_rotate = [
        "api_key",
        "database_password",
        "service_account_key"
    ]
    
    rotated = []
    for secret_name in secrets_to_rotate:
        try:
            # Generate new secret (implementation depends on source)
            new_value = await generate_new_secret(secret_name)
            
            # Store with rotation timestamp
            backup_name = f"{secret_name}_backup_{datetime.now().strftime('%Y%m%d')}"
            old_value = await ctx.get_secret(secret_name)
            await ctx.set_secret(backup_name, old_value)
            
            # Update with new value
            await ctx.set_secret(secret_name, new_value)
            
            rotated.append({
                "secret": secret_name,
                "status": "rotated",
                "backup": backup_name
            })
            
            ctx.log("info", f"Rotated secret: {secret_name}")
            
        except Exception as e:
            ctx.log("error", f"Failed to rotate {secret_name}: {str(e)}")
            rotated.append({
                "secret": secret_name,
                "status": "failed",
                "error": str(e)
            })
    
    return {
        "rotated_count": len([r for r in rotated if r["status"] == "rotated"]),
        "failed_count": len([r for r in rotated if r["status"] == "failed"]),
        "details": rotated
    }

async def generate_new_secret(secret_type: str) -> str:
    """Generate new secret based on type."""
    import secrets
    import string
    
    if "key" in secret_type:
        return f"sk-{secrets.token_hex(32)}"
    elif "password" in secret_type:
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
        return ''.join(secrets.choice(alphabet) for _ in range(32))
    else:
        return secrets.token_hex(16)
```

### Rotation Schedule

**Sensitive Secrets** (high-risk if compromised):
- API keys for payment systems
- Database passwords
- Service account secrets
- **Rotate every 30 days**

**Standard Secrets** (medium-risk):
- Regular API keys
- Internal service credentials
- **Rotate every 90 days**

**Certificates** (managed by provider):
- Let certificates auto-renew
- **Manually rotate every 12 months**

## Security Best Practices

### 1. Principle of Least Privilege

Only grant access to secrets that workflows need:

```python
# Bad: Workflow can access all secrets
workflow_config = {
    "access": "all_secrets"
}

# Good: Workflow only accesses specific secret
workflow_config = {
    "requires_secrets": ["api_key"]
}
```

### 2. Never Log Secrets

Always audit logs to ensure secrets aren't exposed:

```python
# Bad: Logging secret value
ctx.log("info", f"API Key: {api_key}")

# Good: Log only that operation succeeded
ctx.log("info", "API call successful", {
    "endpoint": "/api/users",
    "status_code": 200
})
```

### 3. Use Secret References in Config

Store only references, not actual values:

```python
# Bad: Secret stored in config
config = {
    "api_key": "sk-actual-secret-value"
}

# Good: Reference to secret
config = {
    "api_key": {"secret_ref": "external_api_key"}
}
```

### 4. Audit Secret Access

Monitor who accesses secrets:

```python
# Key Vault logs all access attempts
# Check Azure Portal → Key Vault → Audit Logs
# Review weekly or after sensitive operations
```

### 5. Expire Secrets

Set expiration dates for temporary credentials:

```bash
# When creating secret in UI, set expiration:
# Expires: 90 days from now

# Bifrost will alert when expiration approaches
```

## Troubleshooting Secrets

### "Secret Not Found"

Check:
1. Secret name is correct (case-sensitive)
2. Secret was created in correct organization
3. Workflow has permission to access secret
4. Secret hasn't been deleted

### "Key Vault Access Denied"

Check:
1. Bifrost managed identity has Key Vault permissions
2. Key Vault access policy includes Bifrost
3. Network firewall isn't blocking access

### "Secret Expired"

- Check expiration date
- Rotate to new secret if needed
- Update workflows to use new secret

### "Access Control Denied"

Check:
1. User has org admin role to manage secrets
2. Organization ID is correct in request
3. API key has necessary permissions

## Reference

- [Azure Key Vault Documentation](https://docs.microsoft.com/azure/key-vault/)
- [Key Vault Pricing](https://azure.microsoft.com/pricing/details/key-vault/)
- [Secret Naming Best Practices](https://docs.microsoft.com/azure/key-vault/secrets/about-secrets)
