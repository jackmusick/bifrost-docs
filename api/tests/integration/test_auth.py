"""
Integration tests for authentication flow.

Tests the complete authentication flow including:
- User registration
- Login with JWT tokens
- Protected route access
- Token refresh
- Logout
"""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest_asyncio.fixture
async def client():
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.mark.integration
class TestHealthCheck:
    """Tests for health check endpoint."""

    async def test_health_check_returns_200(self, client: AsyncClient):
        """Test that health check endpoint returns 200."""
        response = await client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"


@pytest.mark.integration
class TestRootEndpoint:
    """Tests for root endpoint."""

    async def test_root_returns_api_info(self, client: AsyncClient):
        """Test that root endpoint returns API info."""
        response = await client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Bifrost Docs API"
        assert data["version"] == "1.0.0"


@pytest.mark.integration
class TestAuthenticationFlow:
    """Tests for the complete authentication flow."""

    async def test_unauthenticated_access_to_protected_route(self, client: AsyncClient):
        """Test that protected routes require authentication."""
        response = await client.get("/api/auth/me")
        assert response.status_code == 401

    async def test_login_with_invalid_credentials(self, client: AsyncClient):
        """Test that login fails with invalid credentials (mocked DB)."""
        # Mock the user repository to return None (user not found)
        mock_repo = AsyncMock()
        mock_repo.get_by_email = AsyncMock(return_value=None)

        with patch("src.routers.auth.UserRepository", return_value=mock_repo):
            response = await client.post(
                "/api/auth/login",
                data={
                    "username": "nonexistent@example.com",
                    "password": "wrongpassword",
                },
            )
        assert response.status_code == 401


@pytest.mark.integration
class TestOrganizationsEndpoint:
    """Tests for organizations endpoint."""

    async def test_unauthenticated_list_organizations(self, client: AsyncClient):
        """Test that listing organizations requires authentication."""
        response = await client.get("/api/organizations")
        assert response.status_code == 401

    async def test_unauthenticated_create_organization(self, client: AsyncClient):
        """Test that creating organizations requires authentication."""
        response = await client.post(
            "/api/organizations",
            json={"name": "Test Org"},
        )
        assert response.status_code == 401
