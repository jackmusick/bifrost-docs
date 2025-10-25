---
title: Azure Functions Troubleshooting
description: Diagnose and resolve Azure Functions and infrastructure issues
---

# Azure Functions Troubleshooting

Azure Functions is the runtime that executes Bifrost workflows. This guide helps you diagnose and fix infrastructure-level issues.

## Function App Won't Start

### Check Function App Status

In Azure Portal:

```
1. Navigate to your Function App
2. Click Overview
3. Check Status:
   ✅ "Running" = OK, check logs
   ❌ "Stopped" = Start it (see below)
   ⚠️ "Degraded" = Some resources failing
```

### Start a Stopped Function App

```bash
# Check status
az functionapp show --resource-group <rg> --name <name> \
  --query "state" -o json

# Start it
az functionapp start --resource-group <rg> --name <name>

# Verify it started
az functionapp show --resource-group <rg> --name <name> \
  --query "state" -o json
```

### Check Startup Logs

```bash
# Stream live logs
az functionapp log tail --resource-group <rg> --name <name>

# Or in Azure Portal:
# Function App → Monitoring → Log Stream
```

**Common startup errors:**

```
❌ STORAGE CONNECTION FAILED
   │
   └─ Fix: Check AZURE_STORAGE_ACCOUNT_NAME and connection string
      - Verify storage account still exists
      - Check account is not in "disabled" state
      - Verify function app can access it (managed identity or key)

❌ KEYVAULT ACCESS DENIED
   │
   └─ Fix: Enable managed identity on function app
      - Function App → Identity → System assigned: ON
      - Give identity access to Key Vault (IAM)

❌ PYTHON RUNTIME ERROR
   │
   └─ Fix: Check Python version matches (must be 3.11)
      - Function App → Settings → Configuration
      - Look for runtime stack version

❌ MODULE IMPORT ERROR
   │
   └─ Fix: Reinstall dependencies
      - Check requirements.txt in deployment
      - Verify all packages are compatible with Python 3.11
```

## Connection Issues

### Cannot Connect to Storage Account

**Symptom**: Timeout when trying to read/write table data

#### Solution Step 1: Verify Storage Account Status

```bash
# Check storage account exists
az storage account show --resource-group <rg> --name <name>

# Check if it's accessible
az storage account show --resource-group <rg> --name <name> \
  --query "primaryEndpoints"
```

#### Solution Step 2: Check Connection String

The function app needs one of these:

**Option 1: Managed Identity (Recommended)**

```
✅ Function App has system-assigned identity
✅ Identity has "Storage Blob Data Contributor" on storage account
✅ No connection string needed
```

**Option 2: Connection String in Settings**

```
✅ Storage account connection string in Function App settings
✅ Connection string is current (not rotated key)
✅ Ensure full string, not truncated
```

**Verify in Azure:**

```bash
# Get current connection string
az storage account show-connection-string \
  --resource-group <rg> --name <name>

# Compare with Function App setting
az functionapp config appsettings list --resource-group <rg> \
  --name <name> | grep -i storage
```

#### Solution Step 3: Check Network Access

If function app and storage account are on a VNet:

```bash
# Verify storage account allows Function App to connect
# Storage Account → Networking → Firewalls and virtual networks

✅ Public endpoint enabled with VNet rules
✅ Function App VNet added to firewall rules
✅ Private endpoint configured and authorized

❌ Firewall blocking all public traffic (without VNet rules)
```

### Cannot Connect to Key Vault

**Symptom**: "Access Denied" when reading secrets

#### Solution Step 1: Enable Managed Identity

Function App must have managed identity enabled:

```bash
# Check status
az functionapp identity show --resource-group <rg> --name <name>

# If not enabled, enable it
az functionapp identity assign --resource-group <rg> --name <name>

# Note the principalId (use this in Key Vault permissions)
```

#### Solution Step 2: Grant Key Vault Access

The function app's identity needs access:

```bash
# Get function app principal ID
PRINCIPAL_ID=$(az functionapp identity show \
  --resource-group <rg> --name <name> --query principalId -o tsv)

# Grant access to Key Vault
az keyvault set-policy --name <vault-name> \
  --object-id $PRINCIPAL_ID \
  --secret-permissions get list
```

**Or in Azure Portal:**

```
Key Vault → Access Control (IAM)
  → Add Role Assignment
  → Role: "Key Vault Secrets User"
  → Members: [Select your Function App]
  → Save
```

#### Solution Step 3: Verify Key Vault URL

Function App needs correct Key Vault URL:

```bash
# Get Key Vault URL
az keyvault show --resource-group <rg> --name <vault-name> \
  --query "properties.vaultUri" -o json

# Should be like: https://my-vault.vault.azure.net/

# Add to Function App settings
az functionapp config appsettings set --resource-group <rg> \
  --name <name> --settings KEYVAULT_URL="https://my-vault.vault.azure.net/"
```

### Cannot Connect to Azure Tables

**Symptom**: Errors when storing/retrieving execution records

#### Check 1: Tables Storage Account

```bash
# Verify storage account has Table service enabled
az storage account show --resource-group <rg> --name <name> \
  --query "primaryEndpoints.table"

# Should return something like:
# https://mystg.table.core.windows.net/
```

#### Check 2: Connection String vs Managed Identity

Same as [Storage Account Connection](#solution-step-2-check-connection-string) above.

#### Check 3: Table Exists

```bash
# List tables in storage account
az storage table list --account-name <name>

# Tables should include:
# - organizations
# - users
# - executions
# - etc.

# If missing, table may not have been created yet
# Run initialization script or deploy first time
```

## Performance Issues

### High Response Times

**Symptom**: Workflows run slowly, timeouts occurring

#### Check 1: Azure Function Tier

```bash
# Check current plan
az functionapp show --resource-group <rg> --name <name> \
  --query "appServicePlanId" -o json

# Check if it's:
✅ Flex Consumption (recommended - scales with load)
✅ Premium (fast, guaranteed capacity)
❌ Consumption (slower, cold starts)
❌ App Service (not recommended for functions)
```

#### Check 2: Monitor Duration in Logs

```bash
# Check function execution times
az functionapp log tail --resource-group <rg> --name <name> \
  | grep -i "duration"

# Look for pattern:
✅ Consistently < 5 seconds
❌ Increasing over time (memory leak?)
❌ > 30 seconds regularly (timeout risk)
```

#### Check 3: Memory Consumption

```
Function App → Monitoring → Metrics

Select:
- Memory Percent
- Duration
- Execution Count

Look for:
✅ Memory < 500 MB
✅ Duration consistent
❌ Memory growing over time
❌ Memory > 1 GB (potential leak)
```

#### Solution: Optimize Workflow

```python
# ❌ Bad: Load all data at once
@workflow(name="process_large_file")
async def process_all_at_once(context):
    # Loads 1 million rows into memory
    data = await load_entire_table()
    for row in data:
        process(row)

# ✅ Good: Process in batches
@workflow(name="process_large_file")
async def process_in_batches(context):
    # Processes 100 rows at a time
    async for batch in load_table_in_batches(batch_size=100):
        for row in batch:
            process(row)
```

### Cold Start Issues

**Symptom**: First request after idle period is very slow (> 10 seconds)

#### Understanding Cold Starts

```
First request after idle
  ↓
Azure spins up new container
  ↓
Python runtime starts
  ↓
Bifrost imports and discovers workflows
  ↓
Request executes
```

Cold starts typically take 10-30 seconds on Consumption plan.

#### Solution 1: Use Flex Consumption Plan

```bash
# Flex Consumption has better cold start performance
# Change plan (requires downtime):

az appservice plan create --name <plan-name> \
  --resource-group <rg> --sku FlexConsumption

az functionapp update --resource-group <rg> --name <name> \
  --plan <plan-name>
```

#### Solution 2: Keep Warm (Monitoring Trick)

```python
# Create a scheduled workflow that runs every 5 minutes
@workflow(
    name="keep_alive",
    description="Keep function app warm",
    execution_mode="scheduled",
    schedule="*/5 * * * *",  # Every 5 minutes
    expose_in_forms=False
)
async def keep_alive(context):
    context.log("info", "Keep-alive ping")
    return {"status": "alive"}
```

This keeps the function app from becoming idle.

#### Solution 3: Optimize Startup Code

```python
# ❌ Bad: Expensive imports at module level
import pandas as pd  # Heavy library
from sklearn.ensemble import RandomForestClassifier

# ✅ Good: Lazy import (only when needed)
async def my_workflow(context):
    # Import only when workflow runs
    import pandas as pd
    # Use pandas...
```

## Timeout Issues

**Symptom**: "Function execution timeout" error

### Understanding Timeouts

```
Execution Mode │ Default Timeout │ Max Timeout
─────────────────────────────────────────────
Sync           │ 300 seconds     │ 300 seconds
Async          │ 300 seconds     │ No hard limit
Scheduled      │ 300 seconds     │ No hard limit
```

### Check Workflow Timeout Setting

```python
# Current setting is 300 seconds (5 minutes)
@workflow(
    name="long_workflow",
    timeout_seconds=300  # ← Change this
)
async def long_workflow(context):
    # Workflow has 300 seconds to complete
    pass
```

**Increase timeout for long workflows:**

```python
# For a 30-minute import
@workflow(
    name="import_users",
    timeout_seconds=1800,  # 30 minutes
    execution_mode="async"  # Run in background
)
async def import_users(context):
    # Up to 1800 seconds to complete
    for user in users:
        await create_user(user)
```

**Best practice: Use async mode for long workflows:**

```python
# ✅ Good for long operations
@workflow(
    execution_mode="async",  # Runs in background queue
    timeout_seconds=3600     # 1 hour
)
async def bulk_user_import(context):
    pass

# ❌ Risky for long operations
@workflow(
    execution_mode="sync",   # Blocks user's request
    timeout_seconds=300      # Max 5 minutes
)
async def bulk_user_import(context):
    pass
```

## Memory and Resource Limits

### Check Current Limits

```bash
# Function App configuration
az functionapp show --resource-group <rg> --name <name> \
  --query "siteConfig.functionAppScaleLimit"

# Typical limits:
# Consumption:      1.5 GB RAM per execution
# Premium:          3.5 GB RAM per execution
# Flex Consumption: 2-4 GB RAM per execution
```

### Out of Memory Error

**Symptom**: "Function killed due to memory limit" or process crash

#### Solution 1: Reduce Memory Usage

```python
# ❌ Memory intensive: Load everything into memory
data = await client.get_all_users()  # 1 million users
for user in data:
    process(user)

# ✅ Memory efficient: Stream or paginate
async for page in client.get_users_paginated(page_size=100):
    for user in page:
        process(user)
```

#### Solution 2: Upgrade Plan

```bash
# Switch to a plan with more memory
# Premium or Flex Consumption plans have more RAM

az appservice plan create --name <plan-name> \
  --resource-group <rg> --sku EP1  # Premium

az functionapp update --resource-group <rg> --name <name> \
  --plan <plan-name>
```

## Workflow Discovery Not Working

**Symptom**: Workflows aren't appearing in UI or API

### Check 1: Function App Logs

```bash
# Look for discovery messages during startup
az functionapp log tail --resource-group <rg> --name <name>

# Should see:
✅ "Discovered: workspace.workflows.my_workflow"
❌ "Failed to import: workspace.workflows.broken_file"
```

### Check 2: Verify Workspace Files

```bash
# Files must be in /home or /platform directories
# On Azure, these are mounted from Azure Files share

# Check Azure Files share
az storage file list --share-name workspace --account-name <name>

# Should see:
/home/workflows/
/platform/examples/
```

### Check 3: Check File Permissions

```bash
# Files must be readable by Function App
# Ensure Function App identity has read access to Files share

# Files share should be mounted at startup
# If not mounting:
  - Check Function App settings for file mount config
  - Verify storage account access
```

## Database Schema Issues

**Symptom**: "Table schema mismatch" or missing columns

### Check 1: Verify Tables Exist

```bash
# List tables
az storage table list --account-name <storage-name>

# Should include:
organizations
users
executions
oauth_connections
configuration
```

### Check 2: Check Table Schema

Tables are created automatically on first use. If schema is wrong:

```bash
# Delete and recreate (WARNING: loses data)
az storage table delete --name organizations --account-name <name>

# Restart Function App to recreate with correct schema
az functionapp restart --resource-group <rg> --name <name>
```

## Monitoring and Alerts

### Enable Application Insights

Make sure Application Insights is connected:

```bash
# Check if connected
az functionapp show --resource-group <rg> --name <name> \
  --query "appInsightsKey"

# Should show a key, if not:
az functionapp config appsettings set --resource-group <rg> \
  --name <name> --settings APPINSIGHTS_INSTRUMENTATIONKEY="<key>"
```

### View Performance Metrics

```bash
# In Azure Portal: Function App → Monitoring → Metrics

# Useful metrics to track:
- Function Execution Count
- Function Execution Units
- Average Execution Time
- Errors
- Server Response Time
```

### Set Up Alerts

```bash
# Function App → Monitoring → Alerts → Create alert rule

# Example alerts:
- "Error rate > 5%"
- "Average execution time > 10s"
- "Function App stopped"
```

## Debugging Locally

### Start Local Development Environment

```bash
# In bifrost-api directory
cd /path/to/bifrost-api

# Start Azurite (storage emulator)
azurite --silent &

# Start Function App
func start
```

### Check Local Logs

```bash
# When func start is running:
[timestamp] Worker Process started and Listening on 7071

# Logs appear in console:
[timestamp] Function "discovery" starting
[timestamp] Executed function "discovery" in 123ms
```

### Test Endpoint Locally

```bash
# Test health endpoint
curl http://localhost:7071/api/health

# Should return:
{"status": "healthy"}

# If not responding, check startup logs for errors
```

## Quick Reference

| Symptom | Most Likely Cause | Fix |
|---------|---|---|
| Function app won't start | Storage/Key Vault unreachable | Check connectivity and settings |
| Workflows not discovered | Workspace files not mounted | Check Azure Files share and mount |
| High response times | Cold start or undersized plan | Use Flex Consumption or warm up |
| Timeout errors | Workflow too long | Increase timeout or use async |
| Out of memory | Loading too much data | Stream data instead of loading all |
| Connection refused | Function app stopped | Start it, check Azure Portal |
| 500 errors in logs | Unhandled exception in workflow | Check logs for error details |

## Getting Help

- **Azure Function Logs**: `az functionapp log tail --resource-group <rg> --name <name>`
- **Application Insights**: Function App → Monitoring → Application Insights → Logs
- **Azure Status**: https://status.azure.com/

## Related Topics

- **[Workflow Engine Troubleshooting](/docs/troubleshooting/workflow-engine)** - Workflow execution issues
- **[Local Development](/docs/guides/local-development)** - Setting up locally
- **[Deployment](/docs/guides/deployment)** - Deploying to Azure
