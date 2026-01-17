"""
Integration tests for user preferences API endpoints.

Tests the complete preferences workflow including:
- Getting preferences (returns defaults if not found)
- Creating/updating preferences (upsert)
- Deleting preferences
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.auth import UserPrincipal, get_current_active_user
from src.main import app
from src.models.enums import UserRole


@pytest_asyncio.fixture
async def client():
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    return UserPrincipal(
        user_id=uuid4(),
        email="test@example.com",
        name="Test User",
        role=UserRole.CONTRIBUTOR,
        is_active=True,
        is_verified=True,
    )


@pytest.mark.integration
class TestPreferencesEndpointAuthentication:
    """Tests for preferences endpoint authentication requirements."""

    async def test_get_preferences_requires_authentication(self, client: AsyncClient):
        """Test that getting preferences requires authentication."""
        response = await client.get("/api/preferences/passwords")
        assert response.status_code == 401

    async def test_put_preferences_requires_authentication(self, client: AsyncClient):
        """Test that updating preferences requires authentication."""
        response = await client.put(
            "/api/preferences/passwords",
            json={"preferences": {"columns": {"visible": [], "order": [], "widths": {}}}},
        )
        assert response.status_code == 401

    async def test_delete_preferences_requires_authentication(self, client: AsyncClient):
        """Test that deleting preferences requires authentication."""
        response = await client.delete("/api/preferences/passwords")
        assert response.status_code == 401


@pytest.mark.integration
class TestGetPreferences:
    """Tests for GET /api/preferences/{entity_type} endpoint."""

    async def test_get_preferences_returns_defaults_when_not_found(
        self, client: AsyncClient, mock_user: UserPrincipal
    ):
        """Test that getting non-existent preferences returns empty defaults."""
        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        try:
            with patch("src.routers.preferences.UserPreferencesRepository") as MockRepo:
                mock_repo = AsyncMock()
                mock_repo.get_by_user_and_entity.return_value = None
                MockRepo.return_value = mock_repo

                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as test_client:
                    response = await test_client.get("/api/preferences/passwords")

            assert response.status_code == 200
            data = response.json()
            assert data["entity_type"] == "passwords"
            assert data["preferences"]["columns"]["visible"] == []
            assert data["preferences"]["columns"]["order"] == []
            assert data["preferences"]["columns"]["widths"] == {}
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_get_preferences_returns_stored_preferences(
        self, client: AsyncClient, mock_user: UserPrincipal
    ):
        """Test that getting existing preferences returns stored data."""
        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        stored_prefs = MagicMock()
        stored_prefs.preferences = {
            "columns": {
                "visible": ["name", "username"],
                "order": ["name", "username", "url"],
                "widths": {"name": 200},
            }
        }

        try:
            with patch("src.routers.preferences.UserPreferencesRepository") as MockRepo:
                mock_repo = AsyncMock()
                mock_repo.get_by_user_and_entity.return_value = stored_prefs
                MockRepo.return_value = mock_repo

                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as test_client:
                    response = await test_client.get("/api/preferences/passwords")

            assert response.status_code == 200
            data = response.json()
            assert data["entity_type"] == "passwords"
            assert data["preferences"]["columns"]["visible"] == ["name", "username"]
            assert data["preferences"]["columns"]["widths"]["name"] == 200
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_get_preferences_rejects_too_long_entity_type(
        self, client: AsyncClient, mock_user: UserPrincipal
    ):
        """Test that entity_type longer than 100 chars is rejected."""
        app.dependency_overrides[get_current_active_user] = lambda: mock_user
        long_entity_type = "a" * 101

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as test_client:
                response = await test_client.get(f"/api/preferences/{long_entity_type}")

            assert response.status_code == 400
            assert "100 characters" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.integration
class TestUpsertPreferences:
    """Tests for PUT /api/preferences/{entity_type} endpoint."""

    async def test_upsert_preferences_creates_new_record(
        self, client: AsyncClient, mock_user: UserPrincipal
    ):
        """Test that upsert creates new preferences when they don't exist."""
        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        mock_prefs = MagicMock()
        mock_prefs.preferences = {
            "columns": {
                "visible": ["name"],
                "order": ["name", "url"],
                "widths": {},
            }
        }

        try:
            with patch("src.routers.preferences.UserPreferencesRepository") as MockRepo:
                mock_repo = AsyncMock()
                mock_repo.upsert.return_value = mock_prefs
                MockRepo.return_value = mock_repo

                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as test_client:
                    response = await test_client.put(
                        "/api/preferences/passwords",
                        json={
                            "preferences": {
                                "columns": {
                                    "visible": ["name"],
                                    "order": ["name", "url"],
                                    "widths": {},
                                }
                            }
                        },
                    )

            assert response.status_code == 200
            data = response.json()
            assert data["entity_type"] == "passwords"
            assert data["preferences"]["columns"]["visible"] == ["name"]
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_upsert_preferences_with_custom_asset_type(
        self, client: AsyncClient, mock_user: UserPrincipal
    ):
        """Test that upsert works with custom asset type entity identifiers."""
        app.dependency_overrides[get_current_active_user] = lambda: mock_user
        custom_type_id = str(uuid4())
        entity_type = f"custom_asset_{custom_type_id}"

        mock_prefs = MagicMock()
        mock_prefs.preferences = {
            "columns": {"visible": ["name"], "order": ["name"], "widths": {}}
        }

        try:
            with patch("src.routers.preferences.UserPreferencesRepository") as MockRepo:
                mock_repo = AsyncMock()
                mock_repo.upsert.return_value = mock_prefs
                MockRepo.return_value = mock_repo

                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as test_client:
                    response = await test_client.put(
                        f"/api/preferences/{entity_type}",
                        json={
                            "preferences": {
                                "columns": {"visible": ["name"], "order": ["name"], "widths": {}}
                            }
                        },
                    )

            assert response.status_code == 200
            data = response.json()
            assert data["entity_type"] == entity_type
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.integration
class TestDeletePreferences:
    """Tests for DELETE /api/preferences/{entity_type} endpoint."""

    async def test_delete_preferences_returns_204(
        self, client: AsyncClient, mock_user: UserPrincipal
    ):
        """Test that deleting preferences returns 204 No Content."""
        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        try:
            with patch("src.routers.preferences.UserPreferencesRepository") as MockRepo:
                mock_repo = AsyncMock()
                mock_repo.delete_by_user_and_entity.return_value = True
                MockRepo.return_value = mock_repo

                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as test_client:
                    response = await test_client.delete("/api/preferences/passwords")

            assert response.status_code == 204
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_delete_nonexistent_preferences_returns_204(
        self, client: AsyncClient, mock_user: UserPrincipal
    ):
        """Test that deleting non-existent preferences still returns 204."""
        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        try:
            with patch("src.routers.preferences.UserPreferencesRepository") as MockRepo:
                mock_repo = AsyncMock()
                mock_repo.delete_by_user_and_entity.return_value = False
                MockRepo.return_value = mock_repo

                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as test_client:
                    response = await test_client.delete("/api/preferences/configurations")

            # Idempotent delete - returns 204 even if nothing was deleted
            assert response.status_code == 204
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
