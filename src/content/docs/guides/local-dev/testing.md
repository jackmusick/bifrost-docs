---
title: Test Workflows Locally
description: Guide for running tests, understanding test structure, and debugging tests
---

# Test Workflows Locally

This guide covers running tests, understanding the test structure, and best practices for testing Bifrost workflows.

## Table of Contents

- [Quick Start](#quick-start)
- [Test Environment](#test-environment)
- [Running Tests](#running-tests)
- [Test Structure](#test-structure)
- [Writing Tests](#writing-tests)
- [Understanding Coverage](#understanding-coverage)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

## Quick Start

Running tests is simple with the `test.sh` script:

```bash
# Run all tests
./test.sh

# Run tests with coverage report
./test.sh --coverage

# Run specific test file
./test.sh tests/unit/test_models.py

# Run specific test
./test.sh tests/unit/test_models.py::test_organization_model -v

# Run only integration tests
./test.sh tests/integration/
```

**Important:** Always use `./test.sh` instead of `pytest` directly. The script sets up the test environment (Azurite, Functions runtime) automatically.

## Test Environment

The `test.sh` script automatically sets up the complete test environment:

### What test.sh Does

1. **Starts Azurite** - Azure Storage emulator on test ports (10100-10102)
2. **Starts Azure Functions runtime** - On port 7777 with test configuration
3. **Configures storage connection** - Points to in-memory Azurite
4. **Runs pytest** - With coverage if requested
5. **Cleans up** - Stops services on completion (or interruption)

### Test Configuration

```bash
# Connection string used for tests
AzureWebJobsStorage="DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;..."

# Functions runtime on port 7777 (not 7071)
FUNCTIONS_WORKER_RUNTIME=python

# In-memory storage (no persistence between runs)
azurite --inMemoryPersistence
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests (simplest approach)
./test.sh

# This will:
# 1. Start Azurite
# 2. Start Functions runtime on :7777
# 3. Wait for Services to be ready
# 4. Run pytest tests/
# 5. Clean up on exit
```

### Common Test Commands

```bash
# Run all tests with detailed output
./test.sh -v

# Run tests matching a pattern
./test.sh -k "test_workflow" -v

# Run single test file
./test.sh tests/unit/test_models.py

# Run single test
./test.sh tests/integration/platform/test_sdk_from_workflow.py::TestSDKFileOperations::test_file_path_sandboxing

# Run tests in a directory
./test.sh tests/unit/

# Run with coverage
./test.sh --coverage

# Run with coverage and verbose output
./test.sh --coverage -v

# Stop on first failure
./test.sh -x

# Run only failed tests from last run
./test.sh --lf

# Run failed tests and new tests
./test.sh --ff
```

### Test Execution Flow

When you run `./test.sh`, here's what happens:

```
1. Cleanup any existing test processes
2. Start Azurite on ports 10100-10102 (in-memory)
   └─ Wait 15 seconds for Azurite to be ready
3. Start Azure Functions runtime on port 7777
   └─ Wait up to 60 seconds for /api/openapi/v3.json to be available
4. Wait additional 10 seconds for queue to stabilize
5. Run pytest with the arguments you provided
6. On exit (success or failure): Kill Azurite and Functions processes
```

## Test Structure

Understanding the test directory structure helps you organize new tests:

```
tests/
├── conftest.py                    # Pytest configuration & shared fixtures
├── unit/                          # Unit tests (fast, isolated)
│   ├── test_models.py            # Pydantic model validation tests
│   ├── test_handlers.py          # Business logic tests (mocked services)
│   └── ...
├── integration/                   # Integration tests (slower, real services)
│   ├── conftest.py               # Integration test fixtures
│   ├── platform/
│   │   ├── test_sdk_from_workflow.py  # SDK from within workflow context
│   │   └── ...
│   ├── functions/
│   │   ├── test_discovery.py     # Discovery API tests
│   │   ├── test_endpoints.py     # Workflow execution tests
│   │   └── ...
│   └── ...
└── contract/                      # Contract tests (SDK API guarantees)
    └── test_sdk_contracts.py     # SDK public API tests
```

### Test Categories

**Unit Tests** (`tests/unit/`)
- Test individual functions and classes
- Mock external services (storage, key vault)
- Fast execution (< 1 second per test)
- Located in `tests/unit/test_*.py`

**Integration Tests** (`tests/integration/`)
- Test full workflows with Azure Functions context
- Use real Azurite storage
- Slower execution (1-10 seconds per test)
- Test against actual HTTP functions
- Located in `tests/integration/**/test_*.py`

**Contract Tests** (`tests/contract/`)
- Verify SDK public API contracts
- Ensure backward compatibility
- Test SDK behavior guarantees
- Located in `tests/contract/test_*.py`

## Writing Tests

### Test File Template

Create tests in the appropriate directory:

```python
# tests/unit/test_my_feature.py
import pytest
from shared.models import MyModel

class TestMyModel:
    """Test suite for MyModel."""

    def test_valid_model_creation(self):
        """Test creating a valid model instance."""
        model = MyModel(name="test", value=123)
        assert model.name == "test"
        assert model.value == 123

    def test_invalid_model_raises_error(self):
        """Test that invalid data raises validation error."""
        with pytest.raises(ValueError):
            MyModel(name="test", value="invalid")
```

### Using Fixtures

Fixtures provide common test setup. Define them in `conftest.py`:

```python
# tests/conftest.py
import pytest

@pytest.fixture
def sample_organization():
    """Fixture: Create a test organization."""
    from shared.models import Organization
    return Organization(
        id="test-org",
        name="Test Org",
        created_by="test-user"
    )

@pytest.fixture
def test_client(sample_organization):
    """Fixture: HTTP client with test headers."""
    # Implementation here
    pass

# Usage in tests:
def test_something(sample_organization):
    assert sample_organization.id == "test-org"
```

### Integration Test Pattern

```python
# tests/integration/functions/test_discovery.py
import pytest
import httpx

class TestDiscoveryAPI:
    """Integration tests for discovery endpoint."""

    @pytest.mark.asyncio
    async def test_list_workflows(self):
        """Test listing available workflows."""
        async with httpx.AsyncClient(base_url="http://localhost:7777") as client:
            response = await client.get(
                "/api/registry/metadata",
                headers={
                    "x-functions-key": "test",
                    "X-Organization-Id": "test-org-active"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "workflows" in data
```

### Mocking Services

For unit tests, mock external services:

```python
# tests/unit/test_handlers.py
from unittest.mock import AsyncMock, patch
from shared.handlers.executions_handlers import ExecutionHandler

@pytest.mark.asyncio
async def test_execution_handler_calls_storage():
    """Test that handler calls storage service."""
    mock_storage = AsyncMock()
    mock_storage.get_execution.return_value = {"id": "123"}

    handler = ExecutionHandler(storage=mock_storage)
    result = await handler.get_execution("test-org", "123")

    assert result["id"] == "123"
    mock_storage.get_execution.assert_called_once()
```

## Understanding Coverage

Coverage reports show which code paths are tested:

### Running Coverage

```bash
# Run tests and generate coverage report
./test.sh --coverage

# Output shows:
# Name                    Stmts   Miss  Cover
# shared/models.py           120    10    92%
# shared/handlers/...        250    15    94%
# ...
# TOTAL                     1500    45    97%
```

### Coverage Reports

The script generates multiple reports:

```bash
# Terminal output (last test run)
./test.sh --coverage

# XML report (for CI/CD)
coverage.xml

# HTML report (open in browser)
htmlcov/index.html
```

### Coverage Thresholds

New code should maintain high coverage:

- **Unit tests:** Aim for 90%+ coverage
- **Integration tests:** Focus on critical paths
- **Overall target:** 85%+ total coverage

### Improving Coverage

```bash
# See which lines are not covered
pytest --cov=shared --cov-report=term-missing

# Focus on specific module
pytest --cov=shared/handlers --cov-report=term-missing tests/unit/
```

## Common Patterns

### Testing Async Functions

```python
import pytest

class TestAsyncWorkflow:
    """Test async workflow functions."""

    @pytest.mark.asyncio
    async def test_workflow_execution(self):
        """Test async workflow."""
        result = await my_async_function()
        assert result == expected_value
```

### Testing With Database

```python
@pytest.fixture
def organization_table():
    """Fixture: Create test table with sample data."""
    # Create temporary table
    # Insert test data
    # Clean up after test
    pass

def test_with_database(organization_table):
    """Test using database fixture."""
    # Test code using organization_table
    pass
```

### Parameterized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("alice", "ALICE"),
    ("bob", "BOB"),
    ("charlie", "CHARLIE"),
])
def test_uppercase_conversion(input, expected):
    """Test uppercase conversion with multiple inputs."""
    assert input.upper() == expected
```

### Testing Error Cases

```python
def test_invalid_input_raises_error():
    """Test that invalid input raises appropriate error."""
    with pytest.raises(ValueError, match="Invalid value"):
        my_function("invalid")
```

## Troubleshooting

### Tests Fail With "Connection Refused"

**Issue:** Azurite or Functions runtime not running

**Solution:**
```bash
# Make sure you're using test.sh
./test.sh

# If it still fails, check what's using the ports
lsof -i :7777,10100,10101,10102

# Kill stray processes
pkill -f "azurite"
pkill -f "func start"

# Try again
./test.sh
```

### "Module not found" in Tests

**Issue:** Dependencies not installed or Python path incorrect

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Verify conftest.py is in tests/ directory
ls tests/conftest.py

# Run pytest from root directory
./test.sh
```

### "Timeout waiting for function app"

**Issue:** Functions runtime taking too long to start

**Solution:**
```bash
# Check if something is hogging resources
top  # Or Activity Monitor on macOS

# Look at the startup log
tail -f /tmp/func-test.log

# The test.sh script waits up to 60 seconds
# If this consistently fails, your system might be too slow
# Try running with fewer tests to verify basic functionality
./test.sh tests/unit/ -v
```

### "Port already in use"

**Issue:** A previous test run didn't clean up

**Solution:**
```bash
# Kill processes on test ports
lsof -ti:7777 | xargs kill -9 || true
pkill -9 -f "azurite" || true

# Try again
./test.sh
```

### Coverage Report Shows Low Coverage

**Issue:** New code not tested

**Solution:**
```bash
# See which lines are not covered
./test.sh --coverage

# Review the coverage.xml or htmlcov/index.html
# Add tests for uncovered lines

# Run with verbose output to see which tests ran
./test.sh -v --coverage
```

## Best Practices

1. **Always use `./test.sh`** - Never run `pytest` directly
2. **Write tests before code** - Test-driven development helps catch bugs early
3. **Keep tests fast** - Unit tests should be < 1 second
4. **Mock external services** - Don't call real APIs in tests
5. **Use descriptive names** - `test_workflow_execution_with_invalid_input()` is better than `test_1()`
6. **Test edge cases** - Empty inputs, null values, errors
7. **Maintain coverage** - Don't let coverage decrease
8. **Run before committing** - Always run `./test.sh` before pushing code

## Next Steps

- **Debug failing tests:** See [Debug Workflows](./debugging.md)
- **Write custom workflows:** See [First Workflow](/tutorials/first-workflow/)
- **Explore test examples:** Look at `tests/integration/` for real examples

---

**Tips:** Run `./test.sh -h` for pytest help, or `./test.sh -v --cov` for detailed output.
