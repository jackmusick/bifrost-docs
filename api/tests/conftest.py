"""
Pytest fixtures for Bifrost Docs API testing infrastructure.

This module provides:
1. Database fixtures (PostgreSQL with SQLAlchemy async)
2. Authentication fixtures
3. Common test data fixtures
"""

import os
import sys
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set environment variables BEFORE any imports that might load settings
# This must happen at module level, not in fixtures, to run before test collection
os.environ.setdefault("BIFROST_DOCS_ENVIRONMENT", "testing")
os.environ.setdefault("BIFROST_DOCS_SECRET_KEY",
                      "test-secret-key-for-testing-must-be-32-chars")
os.environ.setdefault("BIFROST_DOCS_DATABASE_URL",
                      "postgresql+asyncpg://bifrost_docs:bifrost_docstest@localhost:5433/bifrost_docs_test")
os.environ.setdefault("BIFROST_DOCS_DATABASE_URL_SYNC",
                      "postgresql://bifrost_docs:bifrost_docstest@localhost:5433/bifrost_docs_test")
os.environ.setdefault("BIFROST_DOCS_REDIS_URL", "redis://localhost:6380/0")


# ==================== CONFIGURATION ====================

# Test database URL (prefer env provided by docker-compose; fall back to local defaults)
TEST_DATABASE_URL = os.getenv(
    "BIFROST_DOCS_DATABASE_URL",
    "postgresql+asyncpg://bifrost_docs:bifrost_docstest@localhost:5433/bifrost_docs_test",
)

TEST_DATABASE_URL_SYNC = os.getenv(
    "BIFROST_DOCS_DATABASE_URL_SYNC",
    "postgresql://bifrost_docs:bifrost_docstest@localhost:5433/bifrost_docs_test",
)

TEST_REDIS_URL = os.getenv(
    "BIFROST_DOCS_REDIS_URL",
    "redis://localhost:6380/0",
)

TEST_API_URL = os.getenv("TEST_API_URL", "http://localhost:8001")


# ==================== SESSION FIXTURES ====================


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(tmp_path_factory):
    """Set up test environment variables once per session."""
    # Set environment variables for testing
    os.environ["BIFROST_DOCS_ENVIRONMENT"] = "testing"
    os.environ["BIFROST_DOCS_DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["BIFROST_DOCS_DATABASE_URL_SYNC"] = TEST_DATABASE_URL_SYNC
    os.environ["BIFROST_DOCS_REDIS_URL"] = TEST_REDIS_URL
    os.environ["BIFROST_DOCS_SECRET_KEY"] = "test-secret-key-for-testing-must-be-32-chars"

    # Set up temp locations for tests
    test_temp = Path("/tmp/bifrost_docs/temp")
    test_temp.mkdir(parents=True, exist_ok=True)
    os.environ["BIFROST_DOCS_TEMP_LOCATION"] = str(test_temp)

    # Reset global database state to ensure it uses test settings
    from src.core.database import reset_db_state

    reset_db_state()

    yield

    # Clean up global database state after tests
    reset_db_state()


# ==================== DATABASE FIXTURES ====================


@pytest.fixture(scope="session")
def async_engine():
    """Create async SQLAlchemy engine for test session.

    Uses NullPool to avoid connection pooling issues with pytest-asyncio's
    function-scoped event loops.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    yield engine


@pytest.fixture(scope="session")
def async_session_factory(async_engine):
    """Create async session factory."""
    return async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def db_session(async_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a database session for each test.

    Each test gets its own session that is rolled back after the test,
    ensuring test isolation.
    """
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def clean_db(db_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a clean database for tests that need it.

    Truncates all tables before the test runs.
    Use sparingly as this is slower than transaction rollback.
    """
    # Get all table names
    result = await db_session.execute(
        text("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename != 'alembic_version'
        """)
    )
    tables = [row[0] for row in result.fetchall()]

    if tables:
        # Disable foreign key checks, truncate, re-enable
        await db_session.execute(text("SET session_replication_role = 'replica'"))
        for table in tables:
            await db_session.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
        await db_session.execute(text("SET session_replication_role = 'origin'"))
        await db_session.commit()

    yield db_session


# ==================== MOCK FIXTURES ====================


@pytest.fixture
def mock_redis():
    """Mock Redis connection for unit tests."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.expire = AsyncMock(return_value=True)
    return mock


# ==================== TEST DATA FIXTURES ====================


@pytest.fixture
def sample_user_data() -> dict[str, Any]:
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "SecurePassword123!",
        "name": "Test User",
    }


@pytest.fixture
def sample_org_data() -> dict[str, Any]:
    """Sample organization data for testing."""
    return {
        "name": "Test Organization",
    }


# ==================== MARKERS ====================


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, mocked dependencies)")
    config.addinivalue_line(
        "markers", "integration: Integration tests (real database)"
    )
    config.addinivalue_line("markers", "slow: Tests that take >1 second")
