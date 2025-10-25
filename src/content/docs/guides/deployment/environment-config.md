---
title: Configure Environments
description: Guide for configuring Bifrost environment variables, settings, and secrets across development, staging, and production
---

# Configure Environments

This guide covers configuring Bifrost across different environments: local development, staging, and production.

## Table of Contents

- [Environment Variables Overview](#environment-variables-overview)
- [Local Development Configuration](#local-development-configuration)
- [Azure Functions Configuration](#azure-functions-configuration)
- [Key Vault Integration](#key-vault-integration)
- [Environment-Specific Settings](#environment-specific-settings)
- [Configuration Management](#configuration-management)
- [Secrets Management](#secrets-management)
- [Troubleshooting](#troubleshooting)

## Environment Variables Overview

Bifrost uses environment variables to configure behavior across environments. Variables are stored in different locations depending on the environment:

| Environment | Storage Location | Example |
|-------------|------------------|---------|
| **Local** | `local.settings.json` | Development on laptop |
| **Azure Functions** | App Settings (Azure Portal or CLI) | Staging/Production in Azure |
| **Key Vault** | Key Vault Secrets | Sensitive values (passwords, keys) |

### Configuration Priority

When running in Azure Functions:

1. **Key Vault** - Most sensitive values (oauth tokens, API keys)
2. **App Settings** - Environment variables and configuration
3. **Defaults** - Built-in defaults (log level, timeouts)

## Local Development Configuration

### local.settings.json

The `local.settings.json` file configures the local Azure Functions runtime:

```json
{
    "IsEncrypted": false,
    "Values": {
        "AzureWebJobsStorage": "UseDevelopmentStorage=true",
        "FUNCTIONS_WORKER_RUNTIME": "python",
        "AZURE_KEY_VAULT_URL": "https://your-keyvault.vault.azure.net/",
        "AZURE_ENVIRONMENT": "development",
        "LOG_LEVEL": "debug"
    },
    "Host": {
        "CORS": "*",
        "CORSCredentials": false,
        "LocalHttpPort": 7071
    }
}
```

### Configuration File Location

```bash
# The file is in the repository root
ls bifrost-api/local.settings.json

# Example template (committed to git)
ls bifrost-api/local.settings.example.json

# Local file (NOT committed, personal settings)
cat bifrost-api/local.settings.json
```

### Setting Up Local Configuration

```bash
# 1. Clone the repository
git clone https://github.com/jackmusick/bifrost-api.git
cd bifrost-api

# 2. Copy the example file
cp local.settings.example.json local.settings.json

# 3. Edit with your settings
nano local.settings.json

# 4. For local development, defaults are fine
# For Key Vault integration, set AZURE_KEY_VAULT_URL
```

### Local Storage Connection String

```json
{
    "Values": {
        "AzureWebJobsStorage": "UseDevelopmentStorage=true"
    }
}
```

This tells Azure Functions to use Azurite (local storage emulator) running on `localhost:10000-10002`.

### Local Key Vault (Optional)

If you want to test Key Vault integration locally:

```json
{
    "Values": {
        "AZURE_KEY_VAULT_URL": "https://your-keyvault.vault.azure.net/",
        "AZURE_TENANT_ID": "your-tenant-id",
        "AZURE_CLIENT_ID": "your-app-id",
        "AZURE_CLIENT_SECRET": "your-app-secret"
    }
}
```

Then log in with Azure CLI:

```bash
# Azure CLI login (for local development)
az login

# Or use service principal
az login --service-principal \
  -u $AZURE_CLIENT_ID \
  -p $AZURE_CLIENT_SECRET \
  --tenant $AZURE_TENANT_ID
```

## Azure Functions Configuration

### Setting App Settings

App Settings in Azure Functions are environment variables available to your code.

**Using Azure Portal:**

1. Go to Function App resource
2. Click Settings → Configuration
3. Click "New application setting"
4. Enter name and value
5. Click Save

**Using Azure CLI:**

```bash
# Set a single setting
az functionapp config appsettings set \
  --name <function-app-name> \
  --resource-group <resource-group> \
  --settings \
    "AZURE_KEY_VAULT_URL=https://your-kv.vault.azure.net/" \
    "AZURE_ENVIRONMENT=production" \
    "LOG_LEVEL=info"

# View all settings
az functionapp config appsettings list \
  --name <function-app-name> \
  --resource-group <resource-group>

# Delete a setting
az functionapp config appsettings delete \
  --name <function-app-name> \
  --resource-group <resource-group> \
  --setting-names "OLD_SETTING"
```

### Built-in Settings

Azure Functions automatically provides these settings:

| Setting | Value | Purpose |
|---------|-------|---------|
| `AzureWebJobsStorage` | `DefaultEndpoint...` | Storage account connection (set by template) |
| `FUNCTIONS_WORKER_RUNTIME` | `python` | Python runtime (set by template) |
| `WEBSITE_CONTENTAZUREFILECONNECTIONSTRING` | Auto | Content share connection (set by Azure) |
| `WEBSITE_CONTENTSHARE` | Auto | Share name for code (set by Azure) |

### Recommended Settings

Configure these settings for production:

```bash
# Basic configuration
AZURE_KEY_VAULT_URL=https://your-kv.vault.azure.net/
AZURE_ENVIRONMENT=production
LOG_LEVEL=info
WORKFLOW_TIMEOUT_SECONDS=300
MAX_EXECUTION_LOG_LINES=10000

# Organization configuration
DEFAULT_ORGANIZATION_ID=my-org
ALLOWED_ORIGINS=https://your-domain.com

# Feature flags
ENABLE_OAUTH_AUTO_REFRESH=true
ENABLE_EXECUTION_LOGGING=true
```

## Key Vault Integration

Key Vault securely stores sensitive values like API keys and OAuth tokens.

### Accessing Key Vault from Code

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def get_secret(secret_name: str) -> str:
    """Get a secret from Key Vault."""
    kv_url = os.getenv("AZURE_KEY_VAULT_URL")
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=kv_url, credential=credential)

    secret = client.get_secret(secret_name)
    return secret.value
```

### Adding Secrets to Key Vault

```bash
# Using Azure CLI
az keyvault secret set \
  --vault-name <keyvault-name> \
  --name "GraphApiClientSecret" \
  --value "<your-secret-value>"

# View secrets
az keyvault secret list --vault-name <keyvault-name>

# Get a secret value
az keyvault secret show \
  --vault-name <keyvault-name> \
  --name "GraphApiClientSecret" \
  --query value -o tsv
```

### Key Vault Access Policies

The Function App needs permission to read secrets:

```bash
# Get Function App managed identity
FUNCTION_APP_ID=$(az functionapp show \
  --resource-group <resource-group> \
  --name <function-app-name> \
  --query identity.principalId -o tsv)

# Grant access to Key Vault
az keyvault set-policy \
  --name <keyvault-name> \
  --object-id $FUNCTION_APP_ID \
  --secret-permissions get list
```

### Key Vault References in App Settings

You can reference Key Vault secrets from App Settings:

```json
{
  "GRAPH_CLIENT_SECRET": "@Microsoft.KeyVault(SecretUri=https://your-kv.vault.azure.net/secrets/GraphApiClientSecret/)"
}
```

Then access it like a regular setting:

```python
secret = os.getenv("GRAPH_CLIENT_SECRET")
```

## Environment-Specific Settings

Configure different settings for each environment:

### Development Environment

**local.settings.json:**

```json
{
    "Values": {
        "AzureWebJobsStorage": "UseDevelopmentStorage=true",
        "FUNCTIONS_WORKER_RUNTIME": "python",
        "AZURE_ENVIRONMENT": "development",
        "LOG_LEVEL": "debug",
        "ENABLE_SWAGGER": "true"
    }
}
```

**Characteristics:**
- Local storage (Azurite)
- Verbose logging
- Swagger UI enabled
- No Key Vault required (optional)

### Staging Environment

**Configured via Azure Portal or CLI:**

```bash
az functionapp config appsettings set \
  --name bifrost-api-staging \
  --resource-group bifrost-staging-rg \
  --settings \
    "AZURE_ENVIRONMENT=staging" \
    "LOG_LEVEL=info" \
    "AZURE_KEY_VAULT_URL=https://bifrost-kv-staging.vault.azure.net/" \
    "ENABLE_SWAGGER=true"
```

**Characteristics:**
- Real Azure Storage
- Azure Key Vault for secrets
- Standard logging
- Swagger UI enabled (for testing)

### Production Environment

**Configured via Azure Portal or CLI:**

```bash
az functionapp config appsettings set \
  --name bifrost-api-prod \
  --resource-group bifrost-prod-rg \
  --settings \
    "AZURE_ENVIRONMENT=production" \
    "LOG_LEVEL=warn" \
    "AZURE_KEY_VAULT_URL=https://bifrost-kv-prod.vault.azure.net/" \
    "ENABLE_SWAGGER=false" \
    "REQUEST_TIMEOUT_SECONDS=60" \
    "ENABLE_EXECUTION_LOGGING=true"
```

**Characteristics:**
- Real Azure Storage
- Azure Key Vault for secrets
- Minimal logging (errors only)
- Swagger UI disabled
- Stricter timeouts
- Comprehensive audit logging

## Configuration Management

### Creating Multiple Environments

**Option 1: Separate Resource Groups**

```bash
# Create resource groups for each environment
az group create --name bifrost-dev-rg --location eastus
az group create --name bifrost-staging-rg --location eastus
az group create --name bifrost-prod-rg --location eastus

# Deploy to each with different parameters
az deployment group create \
  --resource-group bifrost-prod-rg \
  --template-file azuredeploy.json \
  --parameters baseName=bifrost-prod
```

**Option 2: Same Resource Group, Named Instances**

```bash
# All resources have environment suffix
bifrost-api-staging
bifrost-api-prod

bifrost-kv-staging
bifrost-kv-prod

bifrost-swa-staging
bifrost-swa-prod
```

### Configuration as Code

Store configuration in Git (non-sensitive values):

```bash
# config/development.yaml
azure_environment: development
log_level: debug
enable_swagger: true
request_timeout_seconds: 300

# config/production.yaml
azure_environment: production
log_level: warn
enable_swagger: false
request_timeout_seconds: 60
```

Load configuration from file:

```python
import yaml

def load_config(env: str) -> dict:
    """Load environment-specific configuration."""
    with open(f"config/{env}.yaml") as f:
        return yaml.safe_load(f)

config = load_config(os.getenv("AZURE_ENVIRONMENT", "development"))
LOG_LEVEL = config["log_level"]
```

## Secrets Management

### Best Practices for Secrets

1. **Never commit secrets to Git**

```bash
# Bad: Don't do this
# local.settings.json with real credentials
{
  "GRAPH_CLIENT_SECRET": "actual-secret-value"
}

# Good: Use Key Vault or example file
cp local.settings.example.json local.settings.json
# local.settings.json is in .gitignore
```

2. **Use Key Vault for all secrets**

```python
# Good: Get from Key Vault
secret = get_secret("GraphApiClientSecret")

# Bad: Get from environment variable
# (unless from Key Vault reference)
secret = os.getenv("GRAPH_CLIENT_SECRET")
```

3. **Rotate secrets regularly**

```bash
# Update a secret in Key Vault
az keyvault secret set \
  --vault-name <keyvault-name> \
  --name "GraphApiClientSecret" \
  --value "<new-secret-value>"

# Applications using Key Vault references automatically get new value
# No restart needed
```

4. **Audit secret access**

```bash
# Enable Key Vault logging
az monitor diagnostic-settings create \
  --name keyvault-logging \
  --resource /subscriptions/.../providers/Microsoft.KeyVault/vaults/<kv-name> \
  --logs '[{"category":"AuditEvent","enabled":true}]' \
  --workspace <log-analytics-workspace>
```

### Secret Rotation

Create a timer-triggered function to rotate secrets:

```python
# functions/timer/rotate_secrets.py
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

async def rotate_secrets(mytimer: func.TimerRequest) -> None:
    """Rotate API keys and tokens periodically."""
    kv_client = SecretClient(
        vault_url=os.getenv("AZURE_KEY_VAULT_URL"),
        credential=DefaultAzureCredential()
    )

    # Get current secret version
    current = kv_client.get_secret("ApiKey")

    # Request new key from API provider
    new_key = await request_new_api_key()

    # Store new key with timestamp
    kv_client.set_secret("ApiKey", new_key)
    kv_client.set_secret("ApiKeyRotatedAt", datetime.utcnow().isoformat())
```

## Troubleshooting

### "Key Vault Access Denied"

**Issue:** Function App can't read secrets from Key Vault

**Solution:**
```bash
# 1. Check managed identity is assigned
az functionapp identity show \
  --resource-group <rg> \
  --name <function-app-name>

# 2. Assign managed identity if missing
az functionapp identity assign \
  --resource-group <rg> \
  --name <function-app-name>

# 3. Get the principal ID
PRINCIPAL_ID=$(az functionapp identity show \
  --resource-group <rg> \
  --name <function-app-name> \
  --query principalId -o tsv)

# 4. Grant Key Vault access
az keyvault set-policy \
  --name <keyvault-name> \
  --object-id $PRINCIPAL_ID \
  --secret-permissions get list
```

### "Setting Not Found" Error

**Issue:** Environment variable doesn't exist

**Solution:**
```bash
# 1. Check the setting is configured
az functionapp config appsettings list \
  --name <function-app-name> \
  --resource-group <rg> \
  | grep -i "YOUR_SETTING"

# 2. Set the missing setting
az functionapp config appsettings set \
  --name <function-app-name> \
  --resource-group <rg> \
  --settings "YOUR_SETTING=value"

# 3. Restart the Function App
az functionapp restart \
  --name <function-app-name> \
  --resource-group <rg>
```

### "Invalid Configuration" After Update

**Issue:** Changes to settings don't take effect

**Solution:**
```bash
# 1. Verify settings were saved
az functionapp config appsettings list \
  --name <function-app-name> \
  --resource-group <rg>

# 2. Restart to apply changes
az functionapp restart \
  --name <function-app-name> \
  --resource-group <rg>

# 3. Check logs for errors
az functionapp log tail \
  --name <function-app-name> \
  --resource-group <rg>
```

### "Storage Connection Failed"

**Issue:** Can't connect to storage account

**Solution:**
```bash
# 1. Verify connection string
az functionapp config appsettings list \
  --name <function-app-name> \
  --resource-group <rg> \
  | grep -i storage

# 2. Get correct connection string
az storage account show-connection-string \
  --name <storage-account-name> \
  --resource-group <rg>

# 3. Update the setting
az functionapp config appsettings set \
  --name <function-app-name> \
  --resource-group <rg> \
  --settings "AzureWebJobsStorage=$(az storage account show-connection-string...)"
```

## Related Documentation

- [Deploy to Azure](/guides/deployment/azure-setup/) - Infrastructure setup
- [GitHub Actions CI/CD](/guides/deployment/github-actions/) - Automated deployment
- [Secrets Management](/guides/integrations/secrets-management/) - OAuth and API key management
- [Azure Functions Configuration](https://learn.microsoft.com/en-us/azure/azure-functions/functions-app-settings) - Microsoft docs

---

**Pro tip:** Use `az functionapp config appsettings list` to review all settings, and `az functionapp config appsettings delete --setting-names OLD_VAR` to clean up obsolete variables.
