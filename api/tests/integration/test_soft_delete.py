"""
Integration tests for soft delete (Track D).

Tests the soft delete HTTP endpoints for:
- Custom Asset Types
- Configuration Types
- Configuration Statuses

Each entity has:
- is_active field (default True)
- POST /{id}/deactivate endpoint
- POST /{id}/activate endpoint
- include_inactive query parameter on list endpoints
- Cannot DELETE if related entities exist
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.auth import get_current_active_user
from src.main import app
from src.models.enums import UserRole

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user principal."""
    user = MagicMock()
    user.user_id = uuid4()
    user.email = "admin@test.com"
    user.role = UserRole.ADMINISTRATOR
    user.is_active = True
    user.is_verified = True
    return user


@pytest_asyncio.fixture
async def admin_client(mock_admin_user):
    """Create an async HTTP client with mocked admin authentication."""

    async def override_get_current_active_user():
        return mock_admin_user

    app.dependency_overrides[get_current_active_user] = override_get_current_active_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


def create_mock_custom_asset_type(
    type_id=None,
    name="Test Asset Type",
    is_active=True,
    fields=None,
):
    """Create a mock custom asset type."""
    mock_type = MagicMock()
    mock_type.id = type_id or uuid4()
    mock_type.name = name
    mock_type.is_active = is_active
    mock_type.fields = fields or [{"key": "hostname", "name": "Hostname", "type": "text"}]
    mock_type.icon = None
    mock_type.color = None
    mock_type.created_at = MagicMock()
    mock_type.updated_at = MagicMock()
    return mock_type


def create_mock_configuration_type(
    type_id=None,
    name="Test Config Type",
    is_active=True,
):
    """Create a mock configuration type."""
    mock_type = MagicMock()
    mock_type.id = type_id or uuid4()
    mock_type.name = name
    mock_type.is_active = is_active
    mock_type.icon = None
    mock_type.color = None
    mock_type.created_at = MagicMock()
    mock_type.updated_at = MagicMock()
    return mock_type


def create_mock_configuration_status(
    status_id=None,
    name="Test Status",
    is_active=True,
):
    """Create a mock configuration status."""
    mock_status = MagicMock()
    mock_status.id = status_id or uuid4()
    mock_status.name = name
    mock_status.is_active = is_active
    mock_status.color = None
    mock_status.created_at = MagicMock()
    mock_status.updated_at = MagicMock()
    return mock_status


# =============================================================================
# Custom Asset Type Soft Delete Tests
# =============================================================================


@pytest.mark.integration
class TestCustomAssetTypeSoftDelete:
    """Tests for soft delete of custom asset types."""

    async def test_deactivate_sets_is_active_false(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that POST /deactivate sets is_active to False."""
        type_id = uuid4()
        mock_type = create_mock_custom_asset_type(type_id=type_id, is_active=True)
        deactivated_type = create_mock_custom_asset_type(type_id=type_id, is_active=False)

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_type)
        mock_repo.deactivate = AsyncMock(return_value=deactivated_type)

        with patch(
            "src.routers.custom_asset_types.CustomAssetTypeRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.post(f"/api/custom-asset-types/{type_id}/deactivate")

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        mock_repo.deactivate.assert_called_once_with(type_id)

    async def test_activate_sets_is_active_true(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that POST /activate sets is_active to True."""
        type_id = uuid4()
        mock_type = create_mock_custom_asset_type(type_id=type_id, is_active=False)
        activated_type = create_mock_custom_asset_type(type_id=type_id, is_active=True)

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_type)
        mock_repo.activate = AsyncMock(return_value=activated_type)

        with patch(
            "src.routers.custom_asset_types.CustomAssetTypeRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.post(f"/api/custom-asset-types/{type_id}/activate")

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
        mock_repo.activate.assert_called_once_with(type_id)

    async def test_list_excludes_inactive_by_default(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that GET list excludes inactive types by default."""
        active_type = create_mock_custom_asset_type(name="Active", is_active=True)

        mock_repo = AsyncMock()
        mock_repo.get_all_ordered = AsyncMock(return_value=[active_type])

        with patch(
            "src.routers.custom_asset_types.CustomAssetTypeRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.get("/api/custom-asset-types")

        assert response.status_code == 200
        mock_repo.get_all_ordered.assert_called_once()
        call_kwargs = mock_repo.get_all_ordered.call_args[1]
        assert call_kwargs.get("include_inactive") is False

    async def test_list_includes_inactive_when_requested(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that GET list includes inactive types when requested."""
        active_type = create_mock_custom_asset_type(name="Active", is_active=True)
        inactive_type = create_mock_custom_asset_type(name="Inactive", is_active=False)

        mock_repo = AsyncMock()
        mock_repo.get_all_ordered = AsyncMock(return_value=[active_type, inactive_type])

        with patch(
            "src.routers.custom_asset_types.CustomAssetTypeRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.get(
                "/api/custom-asset-types", params={"include_inactive": "true"}
            )

        assert response.status_code == 200
        mock_repo.get_all_ordered.assert_called_once()
        call_kwargs = mock_repo.get_all_ordered.call_args[1]
        assert call_kwargs.get("include_inactive") is True

    async def test_cannot_delete_with_existing_assets(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that DELETE is prevented when assets exist."""
        type_id = uuid4()
        mock_type = create_mock_custom_asset_type(type_id=type_id)

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_type)
        mock_repo.can_delete = AsyncMock(return_value=False)
        mock_repo.get_asset_count = AsyncMock(return_value=5)

        with patch(
            "src.routers.custom_asset_types.CustomAssetTypeRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.delete(f"/api/custom-asset-types/{type_id}")

        assert response.status_code == 400
        data = response.json()
        assert "cannot" in data["detail"].lower() or "assets" in data["detail"].lower()

    async def test_can_delete_without_assets(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that DELETE works when no assets exist."""
        type_id = uuid4()
        mock_type = create_mock_custom_asset_type(type_id=type_id)

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_type)
        mock_repo.can_delete = AsyncMock(return_value=True)
        mock_repo.delete = AsyncMock(return_value=None)

        with patch(
            "src.routers.custom_asset_types.CustomAssetTypeRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.delete(f"/api/custom-asset-types/{type_id}")

        assert response.status_code == 204
        mock_repo.delete.assert_called_once()

    async def test_deactivate_nonexistent_type_returns_404(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that deactivating a nonexistent type returns 404."""
        type_id = uuid4()

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with patch(
            "src.routers.custom_asset_types.CustomAssetTypeRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.post(f"/api/custom-asset-types/{type_id}/deactivate")

        assert response.status_code == 404

    async def test_activate_nonexistent_type_returns_404(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that activating a nonexistent type returns 404."""
        type_id = uuid4()

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with patch(
            "src.routers.custom_asset_types.CustomAssetTypeRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.post(f"/api/custom-asset-types/{type_id}/activate")

        assert response.status_code == 404


# =============================================================================
# Configuration Type Soft Delete Tests
# =============================================================================


@pytest.mark.integration
class TestConfigurationTypeSoftDelete:
    """Tests for soft delete of configuration types."""

    async def test_deactivate_sets_is_active_false(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that POST /deactivate sets is_active to False."""
        type_id = uuid4()
        mock_type = create_mock_configuration_type(type_id=type_id, is_active=True)
        deactivated_type = create_mock_configuration_type(type_id=type_id, is_active=False)

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_type)
        mock_repo.deactivate = AsyncMock(return_value=deactivated_type)

        with patch(
            "src.routers.configuration_types.ConfigurationTypeRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.post(f"/api/configuration-types/{type_id}/deactivate")

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        mock_repo.deactivate.assert_called_once_with(type_id)

    async def test_activate_sets_is_active_true(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that POST /activate sets is_active to True."""
        type_id = uuid4()
        mock_type = create_mock_configuration_type(type_id=type_id, is_active=False)
        activated_type = create_mock_configuration_type(type_id=type_id, is_active=True)

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_type)
        mock_repo.activate = AsyncMock(return_value=activated_type)

        with patch(
            "src.routers.configuration_types.ConfigurationTypeRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.post(f"/api/configuration-types/{type_id}/activate")

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
        mock_repo.activate.assert_called_once_with(type_id)

    async def test_list_excludes_inactive_by_default(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that GET list excludes inactive types by default."""
        active_type = create_mock_configuration_type(name="Active", is_active=True)

        mock_repo = AsyncMock()
        mock_repo.get_all_ordered = AsyncMock(return_value=[active_type])

        with patch(
            "src.routers.configuration_types.ConfigurationTypeRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.get("/api/configuration-types")

        assert response.status_code == 200
        mock_repo.get_all_ordered.assert_called_once()
        call_kwargs = mock_repo.get_all_ordered.call_args[1]
        assert call_kwargs.get("include_inactive") is False

    async def test_list_includes_inactive_when_requested(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that GET list includes inactive types when requested."""
        active_type = create_mock_configuration_type(name="Active", is_active=True)
        inactive_type = create_mock_configuration_type(name="Inactive", is_active=False)

        mock_repo = AsyncMock()
        mock_repo.get_all_ordered = AsyncMock(return_value=[active_type, inactive_type])

        with patch(
            "src.routers.configuration_types.ConfigurationTypeRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.get(
                "/api/configuration-types", params={"include_inactive": "true"}
            )

        assert response.status_code == 200
        mock_repo.get_all_ordered.assert_called_once()
        call_kwargs = mock_repo.get_all_ordered.call_args[1]
        assert call_kwargs.get("include_inactive") is True

    async def test_cannot_delete_with_existing_configurations(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that DELETE is prevented when configurations exist."""
        type_id = uuid4()
        mock_type = create_mock_configuration_type(type_id=type_id)

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_type)
        mock_repo.can_delete = AsyncMock(return_value=False)
        mock_repo.get_configuration_count = AsyncMock(return_value=3)

        with patch(
            "src.routers.configuration_types.ConfigurationTypeRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.delete(f"/api/configuration-types/{type_id}")

        assert response.status_code == 400
        data = response.json()
        assert "cannot" in data["detail"].lower() or "configuration" in data["detail"].lower()

    async def test_can_delete_without_configurations(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that DELETE works when no configurations exist."""
        type_id = uuid4()
        mock_type = create_mock_configuration_type(type_id=type_id)

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_type)
        mock_repo.can_delete = AsyncMock(return_value=True)
        mock_repo.delete_by_id = AsyncMock(return_value=True)

        with patch(
            "src.routers.configuration_types.ConfigurationTypeRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.delete(f"/api/configuration-types/{type_id}")

        assert response.status_code == 204
        mock_repo.delete_by_id.assert_called_once_with(type_id)

    async def test_deactivate_nonexistent_type_returns_404(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that deactivating a nonexistent type returns 404."""
        type_id = uuid4()

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with patch(
            "src.routers.configuration_types.ConfigurationTypeRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.post(f"/api/configuration-types/{type_id}/deactivate")

        assert response.status_code == 404

    async def test_activate_nonexistent_type_returns_404(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that activating a nonexistent type returns 404."""
        type_id = uuid4()

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with patch(
            "src.routers.configuration_types.ConfigurationTypeRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.post(f"/api/configuration-types/{type_id}/activate")

        assert response.status_code == 404


# =============================================================================
# Configuration Status Soft Delete Tests
# =============================================================================


@pytest.mark.integration
class TestConfigurationStatusSoftDelete:
    """Tests for soft delete of configuration statuses."""

    async def test_deactivate_sets_is_active_false(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that POST /deactivate sets is_active to False."""
        status_id = uuid4()
        mock_status = create_mock_configuration_status(status_id=status_id, is_active=True)
        deactivated_status = create_mock_configuration_status(status_id=status_id, is_active=False)

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_status)
        mock_repo.deactivate = AsyncMock(return_value=deactivated_status)

        with patch(
            "src.routers.configuration_statuses.ConfigurationStatusRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.post(
                f"/api/configuration-statuses/{status_id}/deactivate"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        mock_repo.deactivate.assert_called_once_with(status_id)

    async def test_activate_sets_is_active_true(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that POST /activate sets is_active to True."""
        status_id = uuid4()
        mock_status = create_mock_configuration_status(status_id=status_id, is_active=False)
        activated_status = create_mock_configuration_status(status_id=status_id, is_active=True)

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_status)
        mock_repo.activate = AsyncMock(return_value=activated_status)

        with patch(
            "src.routers.configuration_statuses.ConfigurationStatusRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.post(f"/api/configuration-statuses/{status_id}/activate")

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
        mock_repo.activate.assert_called_once_with(status_id)

    async def test_list_excludes_inactive_by_default(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that GET list excludes inactive statuses by default."""
        active_status = create_mock_configuration_status(name="Active", is_active=True)

        mock_repo = AsyncMock()
        mock_repo.get_all_ordered = AsyncMock(return_value=[active_status])

        with patch(
            "src.routers.configuration_statuses.ConfigurationStatusRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.get("/api/configuration-statuses")

        assert response.status_code == 200
        mock_repo.get_all_ordered.assert_called_once()
        call_kwargs = mock_repo.get_all_ordered.call_args[1]
        assert call_kwargs.get("include_inactive") is False

    async def test_list_includes_inactive_when_requested(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that GET list includes inactive statuses when requested."""
        active_status = create_mock_configuration_status(name="Active", is_active=True)
        inactive_status = create_mock_configuration_status(name="Inactive", is_active=False)

        mock_repo = AsyncMock()
        mock_repo.get_all_ordered = AsyncMock(return_value=[active_status, inactive_status])

        with patch(
            "src.routers.configuration_statuses.ConfigurationStatusRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.get(
                "/api/configuration-statuses", params={"include_inactive": "true"}
            )

        assert response.status_code == 200
        mock_repo.get_all_ordered.assert_called_once()
        call_kwargs = mock_repo.get_all_ordered.call_args[1]
        assert call_kwargs.get("include_inactive") is True

    async def test_cannot_delete_with_existing_configurations(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that DELETE is prevented when configurations exist."""
        status_id = uuid4()
        mock_status = create_mock_configuration_status(status_id=status_id)

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_status)
        mock_repo.can_delete = AsyncMock(return_value=False)
        mock_repo.get_configuration_count = AsyncMock(return_value=3)

        with patch(
            "src.routers.configuration_statuses.ConfigurationStatusRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.delete(f"/api/configuration-statuses/{status_id}")

        assert response.status_code == 400
        data = response.json()
        assert "cannot" in data["detail"].lower() or "configuration" in data["detail"].lower()

    async def test_can_delete_without_configurations(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that DELETE works when no configurations exist."""
        status_id = uuid4()
        mock_status = create_mock_configuration_status(status_id=status_id)

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_status)
        mock_repo.can_delete = AsyncMock(return_value=True)
        mock_repo.delete_by_id = AsyncMock(return_value=True)

        with patch(
            "src.routers.configuration_statuses.ConfigurationStatusRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.delete(f"/api/configuration-statuses/{status_id}")

        assert response.status_code == 204
        mock_repo.delete_by_id.assert_called_once_with(status_id)

    async def test_deactivate_nonexistent_status_returns_404(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that deactivating a nonexistent status returns 404."""
        status_id = uuid4()

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with patch(
            "src.routers.configuration_statuses.ConfigurationStatusRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.post(
                f"/api/configuration-statuses/{status_id}/deactivate"
            )

        assert response.status_code == 404

    async def test_activate_nonexistent_status_returns_404(
        self, admin_client: AsyncClient, mock_admin_user
    ):
        """Test that activating a nonexistent status returns 404."""
        status_id = uuid4()

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with patch(
            "src.routers.configuration_statuses.ConfigurationStatusRepository",
            return_value=mock_repo,
        ):
            response = await admin_client.post(f"/api/configuration-statuses/{status_id}/activate")

        assert response.status_code == 404
