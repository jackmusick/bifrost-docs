---
title: Set Up Local Development
description: Complete guide for setting up Bifrost development environment with dev containers or manual setup
---

# Set Up Local Development

This guide walks you through setting up Bifrost for local development. Choose either the **Dev Container** approach (recommended) or **Manual Setup**.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Option 1: Dev Container Setup (Recommended)](#option-1-dev-container-setup-recommended)
- [Option 2: Manual Setup](#option-2-manual-setup)
- [Verifying Your Setup](#verifying-your-setup)
- [Project Structure](#project-structure)
- [Next Steps](#next-steps)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before you start, ensure you have:

### Required Software

- **Git** - Version control
  ```bash
  git --version  # Should be 2.30+
  ```

- **Either Dev Container OR Manual Setup tools:**
  - **Dev Container approach:** Docker Desktop 24+ and VS Code with Dev Containers extension
  - **Manual approach:** Python 3.11+, Node.js 20+, and Azure Functions Core Tools

### Required Access

- Clone access to [bifrost-api](https://github.com/jackmusick/bifrost-api) and [bifrost-client](https://github.com/jackmusick/bifrost-client) repositories
- GitHub account (for pulling dependencies)

### Hardware Requirements

- **Disk Space:** At least 5 GB (2 GB for containers, 3 GB for dependencies)
- **RAM:** Minimum 4 GB (8 GB recommended for smooth experience)
- **CPU:** 2+ cores recommended

## Option 1: Dev Container Setup (Recommended)

The dev container provides a complete, pre-configured development environment with all dependencies.

### Step 1: Open Repository in VS Code

```bash
# Clone the API repository
git clone https://github.com/jackmusick/bifrost-api.git
cd bifrost-api

# Open in VS Code
code .
```

### Step 2: Install Dev Container Extension

1. Open VS Code
2. Go to Extensions (Cmd/Ctrl + Shift + X)
3. Search for "Dev Containers" by Microsoft
4. Click Install

### Step 3: Reopen in Container

1. Open the Command Palette (Cmd/Ctrl + Shift + P)
2. Type "Dev Containers: Reopen in Container"
3. Select the option and wait for the container to build (2-3 minutes on first run)

The dev container automatically:
- Installs Python 3.11
- Installs Azure Functions Core Tools v4
- Installs Node.js 20
- Installs all Python dependencies from `requirements.txt`
- Installs Azurite (Azure Storage emulator)
- Configures VS Code with Python extensions

### Step 4: Start the Functions Runtime

Inside the dev container terminal:

```bash
# Start Azure Functions runtime
func start

# Expected output:
# Azure Functions Core Tools (4.0.x)
# Host lock lease acquired by instance ID 'xxx'.
# Workers initialized in 2456 ms.
# Http Functions:
#   health: [GET,POST] http://localhost:7071/api/health
#   ...
```

The API is now running at:
- **API Base:** http://localhost:7071
- **Health Check:** http://localhost:7071/api/health
- **OpenAPI Spec:** http://localhost:7071/api/openapi.json

### Step 5: Verify the Setup

In a new terminal:

```bash
# Test the health endpoint
curl http://localhost:7071/api/health

# Expected response:
# {"status": "healthy", "version": "..."}
```

## Option 2: Manual Setup

If you prefer not to use dev containers, set up the environment manually.

### Step 1: Clone Repository

```bash
git clone https://github.com/jackmusick/bifrost-api.git
cd bifrost-api
```

### Step 2: Install Python Dependencies

```bash
# Create virtual environment (recommended)
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Install Azure Functions Core Tools

```bash
# Using npm (recommended)
npm install -g azure-functions-core-tools@4 --unsafe-perm true

# Verify installation
func --version  # Should show 4.x.x

# Alternative: Using Homebrew (macOS)
brew tap azure/azurite && brew install azure-functions-core-tools@4
```

### Step 4: Set Up Local Storage Emulator

You can use either Azurite or Azure Storage Emulator:

#### Option A: Azurite (Recommended)

```bash
# Install globally
npm install -g azurite

# Start in a separate terminal (with persistent storage)
azurite --blobPort 10000 --queuePort 10001 --tablePort 10002

# Or use in-memory for testing
azurite --blobPort 10000 --queuePort 10001 --tablePort 10002 --inMemoryPersistence
```

#### Option B: Azure Storage Emulator

```bash
# Install from: https://go.microsoft.com/fwlink/?linkid=717179
# Then start it:
AzureStorageEmulator.exe start
```

### Step 5: Configure Local Settings

```bash
# Copy the example settings
cp local.settings.example.json local.settings.json

# Edit local.settings.json if needed
cat local.settings.json
```

The default `local.settings.json`:

```json
{
    "IsEncrypted": false,
    "Values": {
        "AzureWebJobsStorage": "UseDevelopmentStorage=true",
        "FUNCTIONS_WORKER_RUNTIME": "python",
        "AZURE_KEY_VAULT_URL": "https://your-keyvault.vault.azure.net/"
    },
    "Host": {
        "CORS": "*",
        "CORSCredentials": false,
        "LocalHttpPort": 7071
    }
}
```

### Step 6: Start the Functions Runtime

```bash
# In the bifrost-api directory (with venv activated)
func start

# Expected output:
# Azure Functions Core Tools (4.0.x)
# Host lock lease acquired by instance ID 'xxx'.
# Http Functions:
#   health: [GET,POST] http://localhost:7071/api/health
#   ...
```

### Step 7: Verify the Setup

```bash
# In a new terminal
curl http://localhost:7071/api/health

# Expected response:
# {"status": "healthy", "version": "..."}
```

## Verifying Your Setup

### Test API Endpoints

```bash
# Health check (no auth required)
curl http://localhost:7071/api/health

# List workflows (requires function key and org ID)
curl -H "x-functions-key: test" \
     -H "X-Organization-Id: test-org-active" \
     http://localhost:7071/api/registry/metadata

# Execute a workflow
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-functions-key: test" \
  -H "X-Organization-Id: test-org-active" \
  -d '{"name": "World"}' \
  http://localhost:7071/api/workflows/hello_world | jq
```

### Check OpenAPI Documentation

```bash
# Get the OpenAPI specification
curl http://localhost:7071/api/openapi.json | jq
```

### Run Tests

```bash
# Using the test.sh script (always use this, not pytest directly)
./test.sh

# Run specific test file
./test.sh tests/unit/test_example.py

# Run with coverage
./test.sh --coverage
```

## Project Structure

Understanding the project structure helps with navigation:

```
bifrost-api/
├── functions/                     # Azure Functions (HTTP/Timer/Queue triggers)
│   ├── http/                      # HTTP-triggered endpoints
│   │   ├── discovery.py
│   │   ├── endpoints.py
│   │   ├── executions.py
│   │   └── openapi.py
│   ├── timer/                     # Timer-triggered functions
│   └── queue/                     # Queue-triggered functions
├── shared/                        # Business logic (NOT in functions/)
│   ├── models.py                  # Pydantic models (source of truth)
│   ├── handlers/                  # Business logic handlers
│   ├── repositories/              # Data access layer
│   └── services/                  # External service integrations
├── sdk/                           # Bifrost SDK (available in workflows)
│   ├── workflows.py
│   ├── executions.py
│   ├── secrets.py
│   └── oauth.py
├── workspace/                     # User workflows (mounted from Azure Files)
│   └── examples/                  # Example workflows
├── tests/                         # Test suite
│   ├── unit/                      # Unit tests
│   ├── integration/               # Integration tests
│   └── contract/                  # Contract tests
├── .devcontainer/                 # Dev container configuration
├── requirements.txt               # Python dependencies
├── host.json                      # Functions host configuration
├── local.settings.json            # Local development settings
└── test.sh                        # Test runner script
```

## Key Files & Their Purpose

### Development Configuration

- **`local.settings.json`** - Local Azure Functions settings (storage connection, key vault URL, etc.)
- **`.devcontainer/devcontainer.json`** - VS Code dev container configuration
- **`requirements.txt`** - Python dependencies
- **`host.json`** - Azure Functions host configuration

### Running Code

- **`bifrost.py`** - Azure Functions app entry point
- **`test.sh`** - Test runner script (always use this, not pytest directly)

### Business Logic

- **`shared/models.py`** - Pydantic models (source of truth for data)
- **`shared/handlers/`** - Business logic handlers (separate from HTTP functions)
- **`shared/repositories/`** - Data access layer

## Common Development Tasks

### Running the API

```bash
# Dev container:
func start

# Manual setup (with venv activated):
func start

# Stop with Ctrl+C
```

### Running Tests

```bash
# All tests
./test.sh

# Specific test file
./test.sh tests/unit/test_models.py

# Specific test
./test.sh tests/unit/test_models.py::test_organization_model

# With coverage report
./test.sh --coverage

# Only integration tests
./test.sh tests/integration/
```

### Code Formatting & Linting

```bash
# Format code with Ruff
ruff format .

# Check code style
ruff check .

# Type checking
npx pyright
```

### Installing New Dependencies

```bash
# Add to requirements.txt, then:
pip install -r requirements.txt

# In dev container, the container will automatically rebuild
```

## Next Steps

After setting up your development environment:

1. **Run Tests** - Ensure everything is working
   ```bash
   ./test.sh
   ```

2. **Test Local API** - Try the health endpoint and example workflows

3. **Read the Next Guides:**
   - [Test Workflows Locally](./testing.md) - Learn how to run and debug tests
   - [Debug Workflows](./debugging.md) - Set up local debugging
   - [Write Your First Workflow](/tutorials/first-workflow/) - Create a workflow

4. **Explore the Code** - Read through the existing workflows and handlers

## Troubleshooting

### "func: command not found"

**Issue:** Azure Functions Core Tools not installed or not in PATH

**Solution:**
```bash
# Install globally
npm install -g azure-functions-core-tools@4

# Verify
func --version
```

### "Python 3.11 not found"

**Issue:** Python 3.11 is not installed or not in PATH

**Solution:**
```bash
# Check installed Python versions
python3 --version

# Install Python 3.11 from python.org or use your package manager
# macOS:
brew install python@3.11

# Then create virtual environment with explicit version
python3.11 -m venv venv
```

### "Storage connection failed"

**Issue:** Azurite or storage emulator not running

**Solution:**
```bash
# Check if Azurite is running
curl http://localhost:10000/devstoreaccount1 || echo "Not running"

# Start Azurite in a separate terminal
azurite --blobPort 10000 --queuePort 10001 --tablePort 10002

# If ports are in use, kill the processes
lsof -ti:10000,10001,10002 | xargs kill -9
```

### "Port 7071 already in use"

**Issue:** Another service is using port 7071

**Solution:**
```bash
# Find what's using port 7071
lsof -i :7071

# Kill the process
kill -9 <PID>

# Or use a different port
func start --port 7777
```

### "Dev container won't start"

**Issue:** Docker or dev container issues

**Solution:**
```bash
# Rebuild the dev container from scratch
# In VS Code: Command Palette → "Dev Containers: Rebuild Container"

# Or from command line:
docker system prune -a
```

### "Module not found" errors

**Issue:** Dependencies not installed

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or in dev container, rebuild:
# Command Palette → "Dev Containers: Rebuild Container"
```

## Getting Help

- **Issues:** [GitHub Issues](https://github.com/jackmusick/bifrost-api/issues)
- **Discussions:** [GitHub Discussions](https://github.com/jackmusick/bifrost-api/discussions)
- **Documentation:** [Bifrost Docs](/guides/local-dev/)

---

**Ready to dive deeper?** Check out [Test Workflows Locally](./testing.md) or [Debug Workflows](./debugging.md).
