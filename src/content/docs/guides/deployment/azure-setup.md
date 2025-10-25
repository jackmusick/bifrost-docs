---
title: Deploy to Azure
description: Complete guide for deploying Bifrost to Azure infrastructure using ARM templates and Azure CLI
---

# Deploy to Azure

This guide walks you through deploying Bifrost to Azure using an ARM template that provisions all required infrastructure automatically.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Infrastructure Overview](#infrastructure-overview)
- [Deployment Steps](#deployment-steps)
- [Post-Deployment Configuration](#post-deployment-configuration)
- [Verifying the Deployment](#verifying-the-deployment)
- [Cost Estimation](#cost-estimation)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before deploying to Azure, you need:

### Required Tools

- **Azure CLI** - Command-line interface for Azure
  ```bash
  # Install from https://learn.microsoft.com/en-us/cli/azure/install-azure-cli
  az --version  # Verify installation
  ```

- **Azure Subscription** - Active Azure account with appropriate permissions
  ```bash
  az login
  az account list
  az account set --subscription <subscription-id>
  ```

### Required Permissions

Your Azure account needs these permissions:
- Create resource groups
- Create storage accounts
- Create function apps
- Create key vaults
- Create application insights
- Create static web apps
- Assign IAM roles

If you don't have these permissions, contact your Azure subscription administrator.

### Resource Quotas

Verify you have sufficient quotas:
```bash
# Check Function App quota
az provider show --namespace Microsoft.Web

# Check Storage account quota
az provider show --namespace Microsoft.Storage
```

## Infrastructure Overview

The ARM template creates the following Azure resources:

### Compute
- **Azure Functions (Flex Consumption Plan)** - Serverless backend runtime
  - Python 3.11 runtime
  - Flexible scaling with configurable memory (512 MB)
  - Maximum 100 instances
  - Pay-per-execution pricing

### Storage
- **Storage Account (Standard_LRS)** - Data and file storage
  - **Tables** - Organization data, users, configurations, executions
  - **Blobs** - Deployment packages, archived data
  - **Files** - Workflow workspace mounts (`/home`, `/tmp`)

### Secrets & Configuration
- **Azure Key Vault** - Secure secrets management
  - OAuth tokens
  - API keys
  - Database connection strings
  - Custom configuration values

### Monitoring
- **Application Insights** - Performance monitoring and diagnostics
  - Request tracking
  - Performance metrics
  - Error monitoring
  - Custom events

### Frontend
- **Static Web App** - React frontend hosting
  - Automatic CDN distribution
  - SSL/TLS certificate management
  - OAuth authentication

## Deployment Steps

### Step 1: Prepare for Deployment

Clone the Bifrost API repository to access the ARM template:

```bash
# Clone the repository
git clone https://github.com/jackmusick/bifrost-api.git
cd bifrost-api

# Verify the ARM template exists
ls deployment/azuredeploy.json
```

### Step 2: Create a Resource Group

Create a resource group to organize all resources:

```bash
# Set variables for consistency
RESOURCE_GROUP="bifrost-prod-rg"
LOCATION="eastus"  # Choose appropriate region
SUBSCRIPTION="your-subscription-id"

# Create resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION \
  --subscription $SUBSCRIPTION
```

### Step 3: Deploy Infrastructure

Deploy the ARM template with your desired configuration:

```bash
# Basic deployment (uses all defaults)
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file deployment/azuredeploy.json

# Or with custom parameters
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file deployment/azuredeploy.json \
  --parameters \
    baseName=mycompany \
    workspacesQuotaGB=200 \
    tmpQuotaGB=100 \
    functionsStorageAccountType=Standard_GRS \
    staticWebAppLocation=eastus2
```

**Important Parameters:**

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `baseName` | bifrost | string | Name prefix for all resources |
| `workspacesQuotaGB` | 100 | 1-1024 | Workflow workspace storage quota |
| `tmpQuotaGB` | 50 | 1-1024 | Temporary file storage quota |
| `functionsStorageAccountType` | Standard_LRS | Standard_LRS, Standard_GRS | Storage redundancy (LRS = local, GRS = geo-replicated) |
| `staticWebAppLocation` | eastus2 | See list | SWA deployment region (limited availability) |

**Static Web App Locations:**
- eastus2
- westus2
- centralus
- westeurope
- eastasia

### Step 4: Monitor Deployment

The deployment typically takes 5-10 minutes. Monitor progress:

```bash
# Watch deployment progress (real-time)
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file deployment/azuredeploy.json \
  --parameters baseName=mycompany

# Check deployment status
az deployment group list --resource-group $RESOURCE_GROUP

# View specific deployment details
az deployment group show \
  --resource-group $RESOURCE_GROUP \
  --name azuredeploy
```

### Step 5: Retrieve Deployment Outputs

After successful deployment, get the resource URLs and names:

```bash
# Get deployment outputs
az deployment group show \
  --resource-group $RESOURCE_GROUP \
  --name azuredeploy \
  --query properties.outputs
```

Output includes:
- **apiFunctionAppUrl** - Your Bifrost API endpoint
- **apiFunctionAppName** - Function App resource name
- **staticWebAppUrl** - Frontend URL
- **staticWebAppName** - SWA resource name
- **storageAccountName** - Storage account name
- **keyVaultName** - Key Vault name
- **keyVaultUrl** - Key Vault endpoint

Save these values for later configuration.

## Post-Deployment Configuration

### 1. Configure Azure Key Vault

Set up Key Vault with necessary secrets:

```bash
# Variables
KEY_VAULT="<keyVaultName-from-outputs>"
RESOURCE_GROUP="bifrost-prod-rg"

# Grant yourself Key Vault access
az keyvault set-policy \
  --name $KEY_VAULT \
  --resource-group $RESOURCE_GROUP \
  --upn $(az account show --query user.name -o tsv) \
  --secret-permissions get list set delete purge

# Add secrets (examples)
az keyvault secret set \
  --vault-name $KEY_VAULT \
  --name "GraphApiClientId" \
  --value "<your-azure-ad-app-id>"

az keyvault secret set \
  --vault-name $KEY_VAULT \
  --name "GraphApiClientSecret" \
  --value "<your-azure-ad-app-secret>"

az keyvault secret set \
  --vault-name $KEY_VAULT \
  --name "HaloApiKey" \
  --value "<your-halopsa-api-key>"
```

### 2. Deploy the API Code

Deploy the Bifrost API code to Azure Functions:

#### Option A: Zip Deploy (Quick)

```bash
# Get api.zip from GitHub releases
# https://github.com/jackmusick/bifrost-api/releases

FUNCTION_APP="<apiFunctionAppName-from-outputs>"
RESOURCE_GROUP="bifrost-prod-rg"

# Deploy the zip package
az functionapp deployment source config-zip \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP \
  --src api.zip
```

#### Option B: GitHub Actions (Recommended)

See [GitHub Actions CI/CD](./github-actions.md) for automated deployment setup.

### 3. Configure Function App Settings

Add required environment variables:

```bash
FUNCTION_APP="<apiFunctionAppName-from-outputs>"
RESOURCE_GROUP="bifrost-prod-rg"
KEY_VAULT_URL="<keyVaultUrl-from-outputs>"

# Configure app settings
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
    AZURE_KEY_VAULT_URL=$KEY_VAULT_URL \
    AZURE_ENVIRONMENT=prod \
    LOG_LEVEL=info
```

### 4. Deploy the Frontend

Deploy the React frontend to Static Web App:

```bash
# Build the frontend
cd bifrost-client
npm install
npm run build

# Deploy using Azure Static Web Apps CLI
# (Typically done through GitHub Actions, see github-actions.md)
```

### 5. Configure Static Web App Authentication

Link the Function App backend to Static Web App:

```bash
SWA_NAME="<staticWebAppName-from-outputs>"
FUNCTION_APP="<apiFunctionAppName-from-outputs>"
RESOURCE_GROUP="bifrost-prod-rg"

# Get Function App resource ID
FUNCTION_APP_ID=$(az functionapp show \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP \
  --query id -o tsv)

# Link backend (if not done by template)
az rest --method post \
  --uri "/subscriptions/{subscription-id}/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/staticSites/$SWA_NAME/linkedBackends?api-version=2024-04-01" \
  --body "{\"properties\": {\"backendResourceId\": \"$FUNCTION_APP_ID\", \"region\": \"eastus\"}}"
```

## Verifying the Deployment

### Check API Connectivity

```bash
# Get API URL
API_URL=$(az deployment group show \
  --resource-group $RESOURCE_GROUP \
  --name azuredeploy \
  --query 'properties.outputs.apiFunctionAppUrl.value' -o tsv)

# Test health endpoint
curl $API_URL/api/health

# Expected response
# {"status": "healthy", "version": "..."}
```

### Check Function App Logs

```bash
FUNCTION_APP="<apiFunctionAppName-from-outputs>"
RESOURCE_GROUP="bifrost-prod-rg"

# Stream logs
az functionapp log tail \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --provider Microsoft.Web/sites/config/logs
```

### Check Application Insights

View performance metrics and errors:

```bash
# List Application Insights resources
az monitor app-insights component show \
  --app <appInsightsName> \
  --resource-group $RESOURCE_GROUP
```

In Azure Portal:
1. Go to Application Insights resource
2. Click "Performance" to see response times
3. Click "Failures" to see errors
4. Click "Metrics" for custom metrics

### Verify Storage Access

```bash
# Check storage account connectivity
az storage account show \
  --name <storageAccountName> \
  --resource-group $RESOURCE_GROUP

# List blob containers
az storage container list \
  --account-name <storageAccountName> \
  --account-key <account-key>

# List file shares
az storage share list \
  --account-name <storageAccountName> \
  --account-key <account-key>
```

## Cost Estimation

### Typical Monthly Costs

**Small Deployment (100-1000 executions/month):**
- Azure Functions: $5-10
- Storage Account: $2-3
- Key Vault: $0.50
- Application Insights: $2-3
- Static Web App: $10-15
- **Total: $20-30/month**

**Medium Deployment (5000-10000 executions/month):**
- Azure Functions: $15-25
- Storage Account: $3-5
- Key Vault: $0.50
- Application Insights: $3-5
- Static Web App: $10-15
- **Total: $30-50/month**

**Large Deployment (50000+ executions/month):**
- Azure Functions: $50-100
- Storage Account: $5-10
- Key Vault: $0.50
- Application Insights: $5-10
- Static Web App: $10-15
- **Total: $70-135/month**

### Cost Optimization

1. **Use Standard_LRS for storage** - Reduces costs vs. Standard_GRS
2. **Set appropriate storage quotas** - Only allocate what you need
3. **Monitor with Azure Cost Management:**
   ```bash
   # View costs in Azure CLI
   az costmanagement query --api-version 2021-10-01 \
     --scope "/subscriptions/{subscription-id}"
   ```
4. **Enable alerts** for cost anomalies in Azure Portal
5. **Archive old execution logs** to reduce storage costs

## Troubleshooting

### Deployment Fails

**Error: "Insufficient quota"**
```bash
# Increase quota in Azure Portal or contact support
# Go to Subscriptions → Usage + quotas
```

**Error: "Location not available"**
```bash
# Static Web App has limited region availability
# Change staticWebAppLocation parameter to supported region
```

### Function App Not Starting

**Check logs:**
```bash
FUNCTION_APP="<apiFunctionAppName>"
RESOURCE_GROUP="bifrost-prod-rg"

az functionapp log tail \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP

# Also check in Azure Portal:
# Function App → Monitor → Logs
```

**Common issues:**
- Missing environment variables (AZURE_KEY_VAULT_URL)
- Storage connection string misconfiguration
- Python version mismatch (ensure 3.11)

### Key Vault Access Denied

**Issue:** Function App can't read secrets from Key Vault

**Solution:**
```bash
# Check IAM role assignment
az role assignment list \
  --resource-group $RESOURCE_GROUP \
  --query "[?principalName=='<function-app-name>']"

# Grant Key Vault Secrets User role
az keyvault set-policy \
  --name <keyVaultName> \
  --object-id <function-app-principal-id> \
  --secret-permissions get list
```

### Storage Connection Issues

**Issue:** Function App can't access storage

```bash
# Verify storage account is accessible
az storage account show-connection-string \
  --name <storageAccountName> \
  --resource-group $RESOURCE_GROUP

# Test connectivity
curl -H "Authorization: Bearer $(az account get-access-token --query accessToken -o tsv)" \
  https://<storageAccountName>.table.core.windows.net/
```

### Static Web App Not Showing

**Issue:** Frontend shows error or blank page

```bash
# Check SWA deployment status
az staticwebapp show \
  --name <staticWebAppName> \
  --resource-group $RESOURCE_GROUP

# View deployment history
az staticwebapp deployment list \
  --name <staticWebAppName> \
  --resource-group $RESOURCE_GROUP
```

## Next Steps

1. **Configure OAuth Connections** - Set up Microsoft Graph or HaloPSA integrations
2. **Deploy Workflows** - Upload your custom workflows
3. **Configure Users** - Add users and set up access control
4. **Monitor Performance** - Set up alerts in Application Insights
5. **Configure Backups** - Enable storage account backups

## Related Documentation

- [GitHub Actions CI/CD](./github-actions.md) - Automated deployment
- [Environment Configuration](./environment-config.md) - Configure app settings
- [Azure CLI Reference](https://learn.microsoft.com/en-us/cli/azure/reference-index)
- [Azure Functions Documentation](https://learn.microsoft.com/en-us/azure/azure-functions/)
- [Azure Storage Documentation](https://learn.microsoft.com/en-us/azure/storage/)
