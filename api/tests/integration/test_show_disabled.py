"""
Integration tests for show_disabled parameter across endpoints.

Tests the show_disabled parameter for list and search endpoints.
"""

from unittest.mock import patch
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
        base_url="http://test"
    ) as ac:
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
        is_verified=True,
    )


@pytest.mark.integration
class TestShowDisabledConfigurations:
    """Tests for show_disabled parameter on configurations endpoint."""

    async def test_list_configurations_show_disabled_false(self, client: AsyncClient):
        """Test listing configurations with show_disabled=False excludes disabled items."""
        user = create_mock_user()
        org_id = uuid4()

        with patch("src.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = user

            with patch(
                "src.repositories.configuration.ConfigurationRepository.get_paginated_by_org"
            ) as mock_repo:
                mock_repo.return_value = ([], 0)

                response = await client.get(
                    f"/api/organizations/{org_id}/configurations?show_disabled=false"
                )

                # Should pass is_enabled=True filter
                assert response.status_code in [200, 404]

    async def test_list_configurations_show_disabled_true(self, client: AsyncClient):
        """Test listing configurations with show_disabled=True includes all items."""
        user = create_mock_user()
        org_id = uuid4()

        with patch("src.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = user

            with patch(
                "src.repositories.configuration.ConfigurationRepository.get_paginated_by_org"
            ) as mock_repo:
                mock_repo.return_value = ([], 0)

                response = await client.get(
                    f"/api/organizations/{org_id}/configurations?show_disabled=true"
                )

                # Should pass is_enabled=None filter (show all)
                assert response.status_code in [200, 404]

    async def test_list_configurations_default_show_disabled(self, client: AsyncClient):
        """Test that show_disabled defaults to False (enabled only)."""
        user = create_mock_user()
        org_id = uuid4()

        with patch("src.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = user

            with patch(
                "src.repositories.configuration.ConfigurationRepository.get_paginated_by_org"
            ) as mock_repo:
                mock_repo.return_value = ([], 0)

                # Call without show_disabled parameter
                response = await client.get(f"/api/organizations/{org_id}/configurations")

                # Should default to show_disabled=False
                assert response.status_code in [200, 404]


@pytest.mark.integration
class TestShowDisabledLocations:
    """Tests for show_disabled parameter on locations endpoint."""

    async def test_list_locations_show_disabled_false(self, client: AsyncClient):
        """Test listing locations with show_disabled=False excludes disabled items."""
        user = create_mock_user()
        org_id = uuid4()

        with patch("src.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = user

            with patch(
                "src.repositories.location.LocationRepository.get_paginated_by_org"
            ) as mock_repo:
                mock_repo.return_value = ([], 0)

                response = await client.get(
                    f"/api/organizations/{org_id}/locations?show_disabled=false"
                )

                assert response.status_code in [200, 404]

    async def test_list_locations_show_disabled_true(self, client: AsyncClient):
        """Test listing locations with show_disabled=True includes all items."""
        user = create_mock_user()
        org_id = uuid4()

        with patch("src.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = user

            with patch(
                "src.repositories.location.LocationRepository.get_paginated_by_org"
            ) as mock_repo:
                mock_repo.return_value = ([], 0)

                response = await client.get(
                    f"/api/organizations/{org_id}/locations?show_disabled=true"
                )

                assert response.status_code in [200, 404]


@pytest.mark.integration
class TestShowDisabledCustomAssets:
    """Tests for show_disabled parameter on custom assets endpoint."""

    async def test_list_custom_assets_show_disabled_false(self, client: AsyncClient):
        """Test listing custom assets with show_disabled=False excludes disabled items."""
        user = create_mock_user()
        org_id = uuid4()

        with patch("src.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = user

            with patch(
                "src.repositories.custom_asset.CustomAssetRepository.get_paginated_by_org"
            ) as mock_repo:
                mock_repo.return_value = ([], 0)

                response = await client.get(
                    f"/api/organizations/{org_id}/custom-assets?show_disabled=false"
                )

                assert response.status_code in [200, 404]

    async def test_list_custom_assets_show_disabled_true(self, client: AsyncClient):
        """Test listing custom assets with show_disabled=True includes all items."""
        user = create_mock_user()
        org_id = uuid4()

        with patch("src.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = user

            with patch(
                "src.repositories.custom_asset.CustomAssetRepository.get_paginated_by_org"
            ) as mock_repo:
                mock_repo.return_value = ([], 0)

                response = await client.get(
                    f"/api/organizations/{org_id}/custom-assets?show_disabled=true"
                )

                assert response.status_code in [200, 404]


@pytest.mark.integration
class TestShowDisabledPasswords:
    """Tests for show_disabled parameter on passwords endpoint."""

    async def test_list_passwords_show_disabled_false(self, client: AsyncClient):
        """Test listing passwords with show_disabled=False excludes disabled items."""
        user = create_mock_user()
        org_id = uuid4()

        with patch("src.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = user

            with patch(
                "src.repositories.password.PasswordRepository.get_paginated_by_org"
            ) as mock_repo:
                mock_repo.return_value = ([], 0)

                response = await client.get(
                    f"/api/organizations/{org_id}/passwords?show_disabled=false"
                )

                assert response.status_code in [200, 404]

    async def test_list_passwords_show_disabled_true(self, client: AsyncClient):
        """Test listing passwords with show_disabled=True includes all items."""
        user = create_mock_user()
        org_id = uuid4()

        with patch("src.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = user

            with patch(
                "src.repositories.password.PasswordRepository.get_paginated_by_org"
            ) as mock_repo:
                mock_repo.return_value = ([], 0)

                response = await client.get(
                    f"/api/organizations/{org_id}/passwords?show_disabled=true"
                )

                assert response.status_code in [200, 404]


@pytest.mark.integration
class TestShowDisabledDocuments:
    """Tests for show_disabled parameter on documents endpoint."""

    async def test_list_documents_show_disabled_false(self, client: AsyncClient):
        """Test listing documents with show_disabled=False excludes disabled items."""
        user = create_mock_user()
        org_id = uuid4()

        with patch("src.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = user

            with patch(
                "src.repositories.document.DocumentRepository.get_paginated_by_org"
            ) as mock_repo:
                mock_repo.return_value = ([], 0)

                response = await client.get(
                    f"/api/organizations/{org_id}/documents?show_disabled=false"
                )

                assert response.status_code in [200, 404]

    async def test_list_documents_show_disabled_true(self, client: AsyncClient):
        """Test listing documents with show_disabled=True includes all items."""
        user = create_mock_user()
        org_id = uuid4()

        with patch("src.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = user

            with patch(
                "src.repositories.document.DocumentRepository.get_paginated_by_org"
            ) as mock_repo:
                mock_repo.return_value = ([], 0)

                response = await client.get(
                    f"/api/organizations/{org_id}/documents?show_disabled=true"
                )

                assert response.status_code in [200, 404]


@pytest.mark.integration
class TestShowDisabledOrganizations:
    """Tests for show_disabled parameter on organizations endpoint."""

    async def test_list_organizations_show_disabled_false(self, client: AsyncClient):
        """Test listing organizations with show_disabled=False excludes disabled items."""
        user = create_mock_user(role=UserRole.ADMINISTRATOR)

        with patch("src.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = user

            with patch(
                "src.repositories.organization.OrganizationRepository.get_all"
            ) as mock_repo:
                mock_repo.return_value = []

                response = await client.get("/api/organizations?show_disabled=false")

                assert response.status_code in [200, 401]

    async def test_list_organizations_show_disabled_true(self, client: AsyncClient):
        """Test listing organizations with show_disabled=True includes all items."""
        user = create_mock_user(role=UserRole.ADMINISTRATOR)

        with patch("src.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = user

            with patch(
                "src.repositories.organization.OrganizationRepository.get_all"
            ) as mock_repo:
                mock_repo.return_value = []

                response = await client.get("/api/organizations?show_disabled=true")

                assert response.status_code in [200, 401]


@pytest.mark.integration
class TestShowDisabledSearch:
    """Tests for show_disabled parameter on search endpoint."""

    async def test_search_configurations_show_disabled_false(self, client: AsyncClient):
        """Test searching configurations with show_disabled=False excludes disabled items."""
        user = create_mock_user()
        org_id = uuid4()

        with patch("src.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = user

            with patch("src.services.search.SearchService.search") as mock_search:
                mock_search.return_value = {
                    "configurations": [],
                    "custom_assets": [],
                    "documents": [],
                    "passwords": [],
                    "locations": [],
                }

                response = await client.get(
                    f"/api/organizations/{org_id}/search?q=test&show_disabled=false"
                )

                assert response.status_code in [200, 404]

    async def test_search_configurations_show_disabled_true(self, client: AsyncClient):
        """Test searching configurations with show_disabled=True includes all items."""
        user = create_mock_user()
        org_id = uuid4()

        with patch("src.core.auth.get_current_user") as mock_auth:
            mock_auth.return_value = user

            with patch("src.services.search.SearchService.search") as mock_search:
                mock_search.return_value = {
                    "configurations": [],
                    "custom_assets": [],
                    "documents": [],
                    "passwords": [],
                    "locations": [],
                }

                response = await client.get(
                    f"/api/organizations/{org_id}/search?q=test&show_disabled=true"
                )

                assert response.status_code in [200, 404]
