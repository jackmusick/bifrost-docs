#!/bin/bash
# Bifrost Docs API - Test Runner
#
# This script runs tests in an isolated Docker environment using docker-compose.test.yml.
# All dependencies (PostgreSQL, Redis) are ephemeral and cleaned up after tests.
#
# Usage:
#   ./test.sh                          # Run ALL backend tests (unit, integration)
#   ./test.sh --coverage               # Run all tests with coverage report
#   ./test.sh --wait                   # Wait before cleanup (for debugging)
#   ./test.sh tests/unit/ -v           # Run only unit tests
#   ./test.sh tests/integration/ -v    # Run only integration tests
#   ./test.sh tests/unit/test_foo.py::test_bar -v  # Run single test

set -e

# Get script directory (repo root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# =============================================================================
# Configuration
# =============================================================================
COMPOSE_FILE="docker-compose.test.yml"
COVERAGE=false
WAIT_MODE=false
PYTEST_ARGS=()

# Load .env.test if it exists (for test secrets)
if [ -f ".env.test" ]; then
    echo "Loading test configuration from .env.test..."
    set -a  # automatically export all variables
    source .env.test
    set +a
fi

# Parse command line arguments
for arg in "$@"; do
    if [ "$arg" = "--coverage" ]; then
        COVERAGE=true
    elif [ "$arg" = "--wait" ]; then
        WAIT_MODE=true
    else
        PYTEST_ARGS+=("$arg")
    fi
done

# =============================================================================
# Docker log export directory
# =============================================================================
LOG_DIR="/tmp/bifrost-docs"
mkdir -p "$LOG_DIR"

# =============================================================================
# Function to export docker logs
# =============================================================================
export_docker_logs() {
    echo "Exporting docker logs to $LOG_DIR/..."

    # Clean up old log files from previous runs
    rm -f "$LOG_DIR"/*.log "$LOG_DIR"/docker-logs.txt 2>/dev/null

    # Export combined logs with timestamps
    {
        echo "============================================================"
        echo "Docker Compose Logs - $(date)"
        echo "============================================================"
        docker compose -f "$COMPOSE_FILE" logs --no-color --timestamps 2>&1
    } > "$LOG_DIR/docker-logs.txt" 2>&1

    # Dynamically get all service names
    local services
    services=$(docker compose -f "$COMPOSE_FILE" --profile test config --services 2>/dev/null)

    for service in $services; do
        local log_file="$LOG_DIR/$service.log"
        if docker compose -f "$COMPOSE_FILE" logs --no-color --timestamps "$service" > "$log_file" 2>&1; then
            if [ -s "$log_file" ]; then
                echo "  Exported: $service.log ($(wc -l < "$log_file") lines)"
            else
                rm -f "$log_file"  # Remove empty log files
            fi
        fi
    done

    echo ""
    echo "Logs exported to $LOG_DIR/"
    ls -la "$LOG_DIR"/*.log 2>/dev/null || echo "  No individual logs captured"
}

# =============================================================================
# Cleanup function
# =============================================================================
cleanup() {
    echo ""
    # Export logs before cleanup
    export_docker_logs
    echo "Cleaning up test environment..."
    docker compose -f "$COMPOSE_FILE" --profile test down -v 2>/dev/null || true
    echo "Cleanup complete"
}

# =============================================================================
# Error handler - prompts before cleanup on any failure
# =============================================================================
error_handler() {
    local exit_code=$?
    local line_number=$1

    echo ""
    echo "============================================================"
    echo "ERROR: Script failed at line $line_number (exit code: $exit_code)"
    echo "============================================================"

    # Show recent container logs for debugging
    echo ""
    echo "Recent container logs:"
    echo "------------------------------------------------------------"
    docker compose -f "$COMPOSE_FILE" logs --tail=50 2>/dev/null || true
    echo "------------------------------------------------------------"

    # In wait mode, wait for user before cleanup
    if [ "$WAIT_MODE" = true ]; then
        echo ""
        echo "Press Enter to cleanup and exit (or Ctrl+C to keep containers running for debugging)..."
        read -r
    fi
}

# Trap errors to show logs and wait before cleanup
trap 'error_handler $LINENO' ERR
# Trap to ensure cleanup on exit or Ctrl+C
trap cleanup EXIT

# =============================================================================
# Start services
# =============================================================================
echo "============================================================"
echo "Bifrost Docs API - Test Runner (Containerized)"
echo "============================================================"
echo ""

# Stop any existing test containers
echo "Stopping any existing test containers..."
docker compose -f "$COMPOSE_FILE" --profile test down -v 2>/dev/null || true

# Build the test runner image
echo "Building test runner image..."
docker compose -f "$COMPOSE_FILE" build test-runner

# Start infrastructure services
echo "Starting PostgreSQL, PgBouncer, and Redis..."
docker compose -f "$COMPOSE_FILE" up -d postgres redis

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U bifrost_docs -d bifrost_docs_test > /dev/null 2>&1; then
        echo "PostgreSQL is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "ERROR: PostgreSQL failed to start within 30 seconds"
        exit 1
    fi
    echo "  Waiting for PostgreSQL... (attempt $i/30)"
    sleep 1
done

# Wait for Redis to be ready
echo "Waiting for Redis to be ready..."
for i in {1..15}; do
    if docker compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo "Redis is ready!"
        break
    fi
    if [ $i -eq 15 ]; then
        echo "ERROR: Redis failed to start within 15 seconds"
        exit 1
    fi
    echo "  Waiting for Redis... (attempt $i/15)"
    sleep 1
done

# Start PgBouncer (depends on PostgreSQL being healthy)
echo "Starting PgBouncer..."
docker compose -f "$COMPOSE_FILE" up -d pgbouncer

# Wait for PgBouncer to be ready
echo "Waiting for PgBouncer to be ready..."
for i in {1..15}; do
    if docker compose -f "$COMPOSE_FILE" exec -T pgbouncer pg_isready -h localhost -p 5432 -U bifrost_docs > /dev/null 2>&1; then
        echo "PgBouncer is ready!"
        break
    fi
    if [ $i -eq 15 ]; then
        echo "ERROR: PgBouncer failed to start within 15 seconds"
        exit 1
    fi
    echo "  Waiting for PgBouncer... (attempt $i/15)"
    sleep 1
done

# Run init container (migrations)
echo ""
echo "Running database migrations..."
docker compose -f "$COMPOSE_FILE" up init
INIT_EXIT_CODE=$(docker inspect bifrost-docs-test-init --format='{{.State.ExitCode}}' 2>/dev/null || echo "1")
if [ "$INIT_EXIT_CODE" != "0" ]; then
    echo "ERROR: Init container failed (migrations)"
    exit 1
fi
echo "Migrations complete!"

# =============================================================================
# Run backend tests
# =============================================================================
TEST_EXIT_CODE=0

echo ""
echo "============================================================"
echo "Running backend tests..."
echo "============================================================"
echo ""

# Build pytest command
PYTEST_CMD=("pytest")

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD+=("--cov=src" "--cov-report=term-missing" "--cov-report=xml:/app/coverage.xml")
fi

if [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
    # Default: run ALL tests
    PYTEST_CMD+=("tests/" "-v")
else
    # Custom test paths provided
    PYTEST_CMD+=("${PYTEST_ARGS[@]}")
fi

# Run tests in container (disable ERR trap for tests - we handle exit code manually)
trap - ERR
set +e
docker compose -f "$COMPOSE_FILE" --profile test run --rm test-runner "${PYTEST_CMD[@]}"
TEST_EXIT_CODE=$?
set -e

# Copy coverage report if generated
if [ "$COVERAGE" = true ]; then
    echo ""
    echo "Copying coverage report..."
    docker compose -f "$COMPOSE_FILE" --profile test run --rm test-runner cat /app/coverage.xml > coverage.xml 2>/dev/null || true
fi

echo ""
echo "============================================================"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "Backend tests completed successfully!"
else
    echo "Backend tests failed with exit code $TEST_EXIT_CODE"
fi
echo "============================================================"

# =============================================================================
# Final summary
# =============================================================================
echo ""
echo "============================================================"
echo "Test Summary"
echo "============================================================"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "  Backend tests: PASSED"
else
    echo "  Backend tests: FAILED (exit code $TEST_EXIT_CODE)"
fi
echo "============================================================"

# In wait mode, wait for user before cleanup
if [ "$WAIT_MODE" = true ]; then
    echo ""
    echo "Press Enter to cleanup and exit (or Ctrl+C to keep containers running)..."
    read -r
fi

# Exit with failure if tests failed
if [ $TEST_EXIT_CODE -ne 0 ]; then
    exit $TEST_EXIT_CODE
fi
exit 0
