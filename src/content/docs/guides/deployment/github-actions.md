---
title: Set Up GitHub Actions CI/CD
description: Automate testing, building, and deployment of Bifrost using GitHub Actions workflows
---

# Set Up GitHub Actions CI/CD

This guide covers setting up automated CI/CD pipelines using GitHub Actions to test, build, and deploy Bifrost to Azure.

## Table of Contents

- [Overview](#overview)
- [Available Workflows](#available-workflows)
- [Setup Requirements](#setup-requirements)
- [Configuring Secrets](#configuring-secrets)
- [Deployment Workflow](#deployment-workflow)
- [Release & Deployment](#release--deployment)
- [Monitoring Deployments](#monitoring-deployments)
- [Troubleshooting](#troubleshooting)

## Overview

Bifrost API uses GitHub Actions to automate:

1. **Testing** - Run test suite on every push and PR
2. **Coverage** - Track test coverage with Codecov
3. **Building** - Create release packages on version tags
4. **Deployment** - Automatically deploy to Azure Functions

The workflows are defined in `.github/workflows/`:

```
.github/workflows/
├── test-and-coverage.yml    # Run tests on push/PR
└── build-release.yml        # Create releases on tags
```

## Available Workflows

### 1. Test and Coverage Workflow

**File:** `.github/workflows/test-and-coverage.yml`

**Triggers:**
- Push to `main` branch with Python changes
- Pull requests to `main` branch with Python changes
- Manual trigger via "Run workflow" button

**What it does:**
1. Sets up Python 3.11 environment
2. Installs dependencies
3. Installs Azure Functions Core Tools
4. Runs full test suite with `./test.sh --coverage`
5. Uploads coverage to Codecov

**Example output:**
```
✓ Set up Python 3.11
✓ Set up Node.js 20
✓ Install dependencies
✓ Install Azure Functions Core Tools
✓ Run tests with coverage
  • 247 tests passed
  • Coverage: 94%
✓ Upload coverage to Codecov
```

### 2. Build and Release Workflow

**File:** `.github/workflows/build-release.yml`

**Triggers:**
- Push with git tags matching `v*` (e.g., `v1.0.0`)
- Manual trigger via "Run workflow" button

**What it does:**
1. Sets up Python 3.11 environment
2. Installs dependencies with `--target` flag
3. Creates `api.zip` package excluding tests and dev files
4. Creates GitHub Release with `api.zip` artifact
5. Auto-generates release notes

**Example output:**
```
✓ Set up Python 3.11
✓ Build API package
  • Installed dependencies to .python_packages/
  • Created api.zip (45 MB)
✓ Upload artifact
✓ Create Release
  • Released v1.0.0
  • Asset: api.zip (45 MB)
```

## Setup Requirements

Before using GitHub Actions, ensure you have:

### 1. GitHub Repository Access

```bash
# Verify you can push to the repository
git remote -v

# Should show:
# origin  https://github.com/jackmusick/bifrost-api.git (fetch)
# origin  https://github.com/jackmusick/bifrost-api.git (push)
```

### 2. Branch Protection (Optional but Recommended)

Set up branch protection to require tests pass before merging:

1. Go to repository Settings → Branches
2. Click "Add rule" for `main` branch
3. Enable:
   - "Require status checks to pass before merging"
   - "Require branches to be up to date before merging"
4. Select "Tests and Coverage" as required check

### 3. Codecov Integration (Optional)

For coverage reports in pull requests:

1. Go to [codecov.io](https://codecov.io)
2. Click "Set up new repository"
3. Authorize GitHub
4. Select your repository
5. Copy the token (if needed)

## Configuring Secrets

GitHub Actions needs secrets to deploy to Azure. Configure them:

### Step 1: Create Azure Credentials

Create a publish profile for your Function App:

```bash
# Get your Function App publish profile
az functionapp deployment list-publishing-profiles \
  --resource-group <resource-group> \
  --name <function-app-name> \
  --xml

# Copy the entire XML output (starts with <?xml and ends with </publishData>)
```

### Step 2: Add Repository Secrets

1. Go to repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add these secrets:

| Name | Value | Description |
|------|-------|-------------|
| `AZURE_FUNCTIONAPP_NAME` | `bifrost-api-xxxxx` | Your Function App name |
| `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` | XML from step 1 | Publish profile for authentication |
| `CODECOV_TOKEN` | From codecov.io | Optional: Codecov token |

**Example:**

```bash
# Using GitHub CLI to add secrets
gh secret set AZURE_FUNCTIONAPP_NAME --body "bifrost-api-abc123"
gh secret set AZURE_FUNCTIONAPP_PUBLISH_PROFILE --body "$(cat publish-profile.xml)"
```

### Step 3: Verify Secrets

```bash
# List configured secrets (values are hidden)
gh secret list

# Output:
# AZURE_FUNCTIONAPP_NAME         Updated ...
# AZURE_FUNCTIONAPP_PUBLISH_PROFILE Updated ...
# CODECOV_TOKEN                  Updated ...
```

## Deployment Workflow

### Manual Workflow for Custom Deployment

Create a custom deployment workflow if needed. Example workflow:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Azure

on:
  workflow_dispatch:  # Manual trigger only
    inputs:
      environment:
        description: 'Environment to deploy to'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Build deployment package
        run: |
          pip install -r requirements.txt --target=".python_packages/lib/site-packages"
          zip -r api.zip . -x "tests/*" ".git/*"

      - name: Deploy to Azure Functions
        uses: azure/webapps-deploy@v2
        with:
          app-name: ${{ secrets.AZURE_FUNCTIONAPP_NAME }}
          publish-profile: ${{ secrets.AZURE_FUNCTIONAPP_PUBLISH_PROFILE }}
          package: api.zip

      - name: Verify deployment
        run: |
          curl -s https://${{ secrets.AZURE_FUNCTIONAPP_NAME }}.azurewebsites.net/api/health
```

To use this workflow:

1. Create the file `.github/workflows/deploy.yml`
2. Go to Actions → Deploy to Azure
3. Click "Run workflow"
4. Choose the environment
5. Click "Run workflow"

## Release & Deployment

### Creating a Release (Step-by-Step)

**Step 1: Prepare Release**

```bash
# Make sure you're on main branch and up to date
git checkout main
git pull origin main

# Verify tests pass locally
./test.sh
```

**Step 2: Create Version Tag**

```bash
# Create a version tag (semantic versioning)
git tag v1.0.0

# Push the tag to GitHub
git push origin v1.0.0

# Or using GitHub CLI
gh release create v1.0.0 --auto-generate-notes
```

**Step 3: GitHub Actions Builds Release**

1. Go to Actions → Build and Release
2. Watch the workflow run
3. Once complete, go to Releases
4. You'll see a new release with `api.zip` attached

**Step 4: Download Package**

```bash
# Via GitHub CLI
gh release download v1.0.0 --pattern "api.zip"

# Or manually: Go to Releases page and download api.zip
```

### Deploying from a Release

Once you have a release package, deploy with:

```bash
# Get the api.zip from release
gh release download v1.0.0 --pattern "api.zip"

# Deploy to Azure
az functionapp deployment source config-zip \
  --resource-group <resource-group> \
  --name <function-app-name> \
  --src api.zip

# Verify
curl https://<function-app-name>.azurewebsites.net/api/health
```

### Semantic Versioning

Follow semantic versioning for releases:

```
v<MAJOR>.<MINOR>.<PATCH>

v1.0.0       # Initial release
v1.1.0       # New features added
v1.1.1       # Bug fix
v2.0.0       # Breaking changes
```

**Rules:**
- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

**Examples:**
- `v1.2.3` - Current production version
- `v1.2.4` - Patch release (bug fix)
- `v1.3.0` - Minor release (new features)
- `v2.0.0` - Major release (breaking changes)

## Monitoring Deployments

### Viewing Workflow Runs

```bash
# List recent workflow runs
gh run list

# Output:
# STATUS    CONCLUSION  WORKFLOW             BRANCH  EVENT
# ✓         success     test-and-coverage    main    push
# ✓         success     build-release        main    create

# View specific run details
gh run view <run-id> --log
```

### Checking Test Results

1. Go to Actions tab in GitHub
2. Click on the workflow run
3. Click on "API Tests" job
4. Scroll down to see test results

### Viewing Coverage Reports

If Codecov is configured:

1. Go to Codecov.io
2. Select your repository
3. See coverage trends over time
4. Coverage reports appear in PR comments

### Checking Deployment Status

```bash
# Using Azure CLI
az functionapp deployment list \
  --resource-group <resource-group> \
  --name <function-app-name>

# Using portal
# Go to Function App → Deployment center → Deployment logs
```

## Troubleshooting

### Tests Fail in GitHub Actions But Pass Locally

**Issue:** Tests pass locally but fail in GitHub Actions

**Solutions:**
```bash
# 1. Check Python version matches
python --version  # Should be 3.11

# 2. Reinstall dependencies
pip install -r requirements.txt

# 3. Run tests the same way CI does
./test.sh --coverage

# 4. Check for hardcoded paths or environment-specific code
grep -r "/Users/yourname" .  # Remove local paths
```

### Deployment Fails With "Publish Profile Invalid"

**Issue:** `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` secret is missing or invalid

**Solution:**
```bash
# 1. Verify secret is configured
gh secret list | grep AZURE_FUNCTIONAPP_PUBLISH_PROFILE

# 2. Get new publish profile
az functionapp deployment list-publishing-profiles \
  --resource-group <rg> \
  --name <function-app-name> \
  --xml > profile.xml

# 3. Update the secret
gh secret set AZURE_FUNCTIONAPP_PUBLISH_PROFILE < profile.xml

# 4. Re-run the workflow
gh workflow run deploy.yml
```

### Workflow Not Triggering

**Issue:** Workflow doesn't run on push or PR

**Solutions:**
```bash
# 1. Check workflow is enabled
# Go to Actions → Select workflow → "Enable workflow"

# 2. Verify trigger conditions
# Look at "on:" section in .github/workflows/*.yml
grep -A 5 "^on:" .github/workflows/test-and-coverage.yml

# 3. For tag-based workflows, tag correctly
git tag v1.0.0  # Matches "v*" pattern
git push origin v1.0.0

# 4. Check branch name
# Workflow only runs on "main" branch (not "master")
```

### Secrets Not Available in Workflow

**Issue:** Workflow can't access secrets

**Solutions:**
```bash
# 1. Verify secrets are configured
gh secret list

# 2. Check secret names match exactly (case-sensitive)
# AZURE_FUNCTIONAPP_NAME (not azure_functionapp_name)

# 3. Test workflow has access
# Add step to print if secret exists:
- name: Check secrets
  run: |
    if [ -z "${{ secrets.AZURE_FUNCTIONAPP_NAME }}" ]; then
      echo "Secret not configured!"
      exit 1
    fi
```

### "Coverage token is not valid"

**Issue:** Codecov upload fails with invalid token

**Solution:**
```bash
# 1. Get new token from codecov.io
# Go to codecov.io → Settings → Tokens

# 2. Update the secret
gh secret set CODECOV_TOKEN --body "your-new-token"

# 3. Run the workflow again
```

### Workflow Takes Too Long

**Issue:** Tests take > 5 minutes to run

**Solutions:**
```bash
# 1. Run tests locally to see what's slow
./test.sh --coverage -v

# 2. Check for external API calls
grep -r "http" tests/  # Should mostly be localhost

# 3. Consider running subset of tests in parallel
# (Requires pytest configuration changes)

# 4. Increase timeout in workflow (if needed)
# In .github/workflows/*.yml, add:
# timeout-minutes: 10
```

## Best Practices

1. **Always run tests locally before pushing**
   ```bash
   ./test.sh
   ```

2. **Use meaningful commit messages**
   ```bash
   git commit -m "Fix: Correct workflow discovery query"
   ```

3. **Keep releases meaningful**
   ```bash
   # Good release notes
   v1.2.0: Add OAuth2 token refresh and improve error messages

   # Bad release notes
   v1.2.0: Updates
   ```

4. **Test the release locally first**
   ```bash
   # Download the built package
   gh release download v1.0.0 --pattern "api.zip"

   # Deploy to staging/dev first
   az functionapp deployment source config-zip \
     --resource-group staging \
     --name staging-api \
     --src api.zip

   # Verify it works
   curl https://staging-api.azurewebsites.net/api/health

   # Then deploy to production
   ```

5. **Keep secrets secure**
   - Never commit secrets to git
   - Rotate secrets regularly
   - Use least privilege principle
   - Don't share secrets in chat/email

## Next Steps

- **Deploy to Azure:** [Deploy to Azure](/guides/deployment/azure-setup/)
- **Environment Configuration:** [Configure Environments](/guides/deployment/environment-config/)
- **GitHub CLI Reference:** [GitHub CLI Docs](https://cli.github.com/manual/)
- **GitHub Actions Reference:** [Actions Documentation](https://docs.github.com/en/actions)

---

**Pro tip:** Use `gh workflow run test-and-coverage.yml` to manually trigger a workflow without pushing code.
