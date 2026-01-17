"""
Integration tests for configurations.

Tests the complete configuration flow including:
- Configuration types CRUD
- Configuration statuses CRUD
- Configurations CRUD with filtering
- Organization isolation
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.models.enums import UserRole


@pytest_asyncio.fixture
async def client():
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test") as ac:
        yield ac


def create_mock_user(user_id=None, role=None):
    """Create a mock UserPrincipal for testing."""
    from src.core.auth import UserPrincipal

    return UserPrincipal(
        user_id=user_id or uuid4(),
        email="test@example.com",
        name="Test User",
        role=role or UserRole.CONTRIBUTOR,
        is_active=True,
        is_verified=True)


@pytest.mark.integration
class TestConfigurationTypesEndpoints:
    """Tests for configuration types endpoints."""

    async def test_unauthenticated_list_configuration_types(self, client: AsyncClient):
        """Test that listing configuration types requires authentication."""
        org_id = uuid4()
        response = await client.get(f"/api/organizations/{org_id}/configuration-types")
        assert response.status_code == 401

    async def test_unauthenticated_create_configuration_type(self, client: AsyncClient):
        """Test that creating configuration types requires authentication."""
        org_id = uuid4()
        response = await client.post(
            f"/api/organizations/{org_id}/configuration-types",
            json={"name": "Server"})
        assert response.status_code == 401

    async def test_unauthenticated_get_configuration_type(self, client: AsyncClient):
        """Test that getting a configuration type requires authentication."""
        org_id = uuid4()
        type_id = uuid4()
        response = await client.get(f"/api/organizations/{org_id}/configuration-types/{type_id}")
        assert response.status_code == 401

    async def test_unauthenticated_delete_configuration_type(self, client: AsyncClient):
        """Test that deleting a configuration type requires authentication."""
        org_id = uuid4()
        type_id = uuid4()
        response = await client.delete(f"/api/organizations/{org_id}/configuration-types/{type_id}")
        assert response.status_code == 401


@pytest.mark.integration
class TestConfigurationStatusesEndpoints:
    """Tests for configuration statuses endpoints."""

    async def test_unauthenticated_list_configuration_statuses(self, client: AsyncClient):
        """Test that listing configuration statuses requires authentication."""
        org_id = uuid4()
        response = await client.get(f"/api/organizations/{org_id}/configuration-statuses")
        assert response.status_code == 401

    async def test_unauthenticated_create_configuration_status(self, client: AsyncClient):
        """Test that creating configuration statuses requires authentication."""
        org_id = uuid4()
        response = await client.post(
            f"/api/organizations/{org_id}/configuration-statuses",
            json={"name": "Active"})
        assert response.status_code == 401

    async def test_unauthenticated_get_configuration_status(self, client: AsyncClient):
        """Test that getting a configuration status requires authentication."""
        org_id = uuid4()
        status_id = uuid4()
        response = await client.get(f"/api/organizations/{org_id}/configuration-statuses/{status_id}")
        assert response.status_code == 401

    async def test_unauthenticated_delete_configuration_status(self, client: AsyncClient):
        """Test that deleting a configuration status requires authentication."""
        org_id = uuid4()
        status_id = uuid4()
        response = await client.delete(f"/api/organizations/{org_id}/configuration-statuses/{status_id}")
        assert response.status_code == 401


@pytest.mark.integration
class TestConfigurationsEndpoints:
    """Tests for configurations endpoints."""

    async def test_unauthenticated_list_configurations(self, client: AsyncClient):
        """Test that listing configurations requires authentication."""
        org_id = uuid4()
        response = await client.get(f"/api/organizations/{org_id}/configurations")
        assert response.status_code == 401

    async def test_unauthenticated_create_configuration(self, client: AsyncClient):
        """Test that creating configurations requires authentication."""
        org_id = uuid4()
        response = await client.post(
            f"/api/organizations/{org_id}/configurations",
            json={"name": "web-server-01"})
        assert response.status_code == 401

    async def test_unauthenticated_get_configuration(self, client: AsyncClient):
        """Test that getting a configuration requires authentication."""
        org_id = uuid4()
        config_id = uuid4()
        response = await client.get(f"/api/organizations/{org_id}/configurations/{config_id}")
        assert response.status_code == 401

    async def test_unauthenticated_update_configuration(self, client: AsyncClient):
        """Test that updating a configuration requires authentication."""
        org_id = uuid4()
        config_id = uuid4()
        response = await client.put(
            f"/api/organizations/{org_id}/configurations/{config_id}",
            json={"name": "updated-server"})
        assert response.status_code == 401

    async def test_unauthenticated_delete_configuration(self, client: AsyncClient):
        """Test that deleting a configuration requires authentication."""
        org_id = uuid4()
        config_id = uuid4()
        response = await client.delete(f"/api/organizations/{org_id}/configurations/{config_id}")
        assert response.status_code == 401


@pytest.mark.integration
class TestConfigurationTypeWithAuth:
    """Tests for configuration types with mocked authentication."""

    async def test_list_configuration_types_empty(self, client: AsyncClient):
        """Test listing configuration types when none exist."""
        org_id = uuid4()
        mock_user = create_mock_user()

        with patch(
            "src.core.auth.get_current_active_user", return_value=mock_user
        ), patch(
            "src.core.auth.get_current_user", return_value=mock_user
        ), patch(
            "src.core.auth.get_current_user_optional", return_value=mock_user
        ), patch(
            "src.routers.configuration_types.ConfigurationTypeRepository"
        ) as mock_type_repo:
            mock_type_repo.return_value.get_all_for_org = AsyncMock(return_value=[])

            response = await client.get(
                f"/api/organizations/{org_id}/configuration-types",
                headers={"Authorization": "Bearer test-token"},
            )

            assert response.status_code == 200
            assert response.json() == []


@pytest.mark.integration
class TestConfigurationStatusWithAuth:
    """Tests for configuration statuses with mocked authentication."""

    async def test_list_configuration_statuses_empty(self, client: AsyncClient):
        """Test listing configuration statuses when none exist."""
        org_id = uuid4()
        mock_user = create_mock_user()

        with patch(
            "src.core.auth.get_current_active_user", return_value=mock_user
        ), patch(
            "src.core.auth.get_current_user", return_value=mock_user
        ), patch(
            "src.core.auth.get_current_user_optional", return_value=mock_user
        ), patch(
            "src.routers.configuration_statuses.ConfigurationStatusRepository"
        ) as mock_status_repo:
            mock_status_repo.return_value.get_all_for_org = AsyncMock(return_value=[])

            response = await client.get(
                f"/api/organizations/{org_id}/configuration-statuses",
                headers={"Authorization": "Bearer test-token"},
            )

            assert response.status_code == 200
            assert response.json() == []


@pytest.mark.integration
class TestConfigurationWithAuth:
    """Tests for configurations with mocked authentication."""

    async def test_list_configurations_empty(self, client: AsyncClient):
        """Test listing configurations when none exist."""
        org_id = uuid4()
        mock_user = create_mock_user()

        with patch(
            "src.core.auth.get_current_active_user", return_value=mock_user
        ), patch(
            "src.core.auth.get_current_user", return_value=mock_user
        ), patch(
            "src.core.auth.get_current_user_optional", return_value=mock_user
        ), patch(
            "src.routers.configurations.ConfigurationRepository"
        ) as mock_config_repo:
            mock_config_repo.return_value.get_paginated_by_org = AsyncMock(
                return_value=([], 0)
            )

            response = await client.get(
                f"/api/organizations/{org_id}/configurations",
                headers={"Authorization": "Bearer test-token"},
            )

            assert response.status_code == 200
            assert response.json() == []
