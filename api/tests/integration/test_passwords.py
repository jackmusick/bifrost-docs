"""
Integration tests for passwords endpoints.

Tests the complete password management flow including:
- Creating passwords
- Listing passwords
- Retrieving passwords (with and without revealing password value)
- Updating passwords
- Deleting passwords
- Organization isolation
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.auth import UserPrincipal, get_current_active_user
from src.main import app
from src.models.enums import UserRole
from src.models.orm.password import Password


@pytest.fixture
def test_org_id():
    """Generate a test organization ID."""
    return uuid4()


@pytest.fixture
def other_org_id():
    """Generate another organization ID for isolation tests."""
    return uuid4()


@pytest.fixture
def test_user(test_org_id):
    """Create a test user principal."""
    return UserPrincipal(
        user_id=uuid4(),
        email="test@example.com",
        name="Test User",
        role=UserRole.CONTRIBUTOR,
        is_active=True,
        is_verified=True)


@pytest_asyncio.fixture
async def client():
    """Create an async HTTP client for testing (unauthenticated)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test") as ac:
        yield ac


@pytest.mark.integration
class TestPasswordsEndpointsUnauthenticated:
    """Tests for passwords endpoints without authentication."""

    async def test_list_passwords_unauthenticated(self, client: AsyncClient, test_org_id):
        """Test that listing passwords requires authentication."""
        response = await client.get(f"/api/organizations/{test_org_id}/passwords")
        assert response.status_code == 401

    async def test_create_password_unauthenticated(self, client: AsyncClient, test_org_id):
        """Test that creating passwords requires authentication."""
        response = await client.post(
            f"/api/organizations/{test_org_id}/passwords",
            json={"name": "Test Password", "password": "secret123"})
        assert response.status_code == 401

    async def test_get_password_unauthenticated(self, client: AsyncClient, test_org_id):
        """Test that getting a password requires authentication."""
        password_id = uuid4()
        response = await client.get(f"/api/organizations/{test_org_id}/passwords/{password_id}")
        assert response.status_code == 401

    async def test_reveal_password_unauthenticated(self, client: AsyncClient, test_org_id):
        """Test that revealing a password requires authentication."""
        password_id = uuid4()
        response = await client.get(
            f"/api/organizations/{test_org_id}/passwords/{password_id}/reveal"
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestPasswordsCreate:
    """Tests for password creation."""

    async def test_create_password_success(self, test_user, test_org_id):
        """Test successful password creation."""
        # Set up dependency override for authentication
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        mock_password_repo = AsyncMock()
        created_password = MagicMock(spec=Password)
        created_password.id = uuid4()
        created_password.organization_id = test_org_id
        created_password.name = "Admin Account"
        created_password.username = "admin"
        created_password.url = "https://example.com"
        created_password.notes = "Main admin account"
        created_password.created_at = MagicMock()
        created_password.updated_at = MagicMock()
        mock_password_repo.create = AsyncMock(return_value=created_password)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch("src.routers.passwords.PasswordRepository", return_value=mock_password_repo):
                    response = await client.post(
                        f"/api/organizations/{test_org_id}/passwords",
                        json={
                            "name": "Admin Account",
                            "username": "admin",
                            "password": "secret123",
                            "url": "https://example.com",
                            "notes": "Main admin account",
                        })

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "Admin Account"
            assert data["username"] == "admin"
            assert "password" not in data  # Password should not be in response
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_create_password_non_member_org(self, test_user, other_org_id):
        """Test that users cannot create passwords in orgs they don't belong to."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                response = await client.post(
                    f"/api/organizations/{other_org_id}/passwords",
                    json={
                        "name": "Test Password",
                        "password": "secret123",
                    })

            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.integration
class TestPasswordsRetrieve:
    """Tests for password retrieval."""

    async def test_get_password_without_reveal(self, test_user, test_org_id):
        """Test getting a password without revealing the password value."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user
        password_id = uuid4()

        mock_password = MagicMock(spec=Password)
        mock_password.id = password_id
        mock_password.organization_id = test_org_id
        mock_password.name = "Test Password"
        mock_password.username = "testuser"
        mock_password.url = "https://test.com"
        mock_password.notes = "Test notes"
        mock_password.created_at = MagicMock()
        mock_password.updated_at = MagicMock()

        mock_password_repo = AsyncMock()
        mock_password_repo.get_by_id_and_org = AsyncMock(return_value=mock_password)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch("src.routers.passwords.PasswordRepository", return_value=mock_password_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/passwords/{password_id}"
                    )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Test Password"
            assert data["username"] == "testuser"
            assert "password" not in data
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_get_password_with_reveal(self, test_user, test_org_id):
        """Test getting a password with the password value revealed."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user
        password_id = uuid4()
        plaintext_password = "supersecret123"

        # Encrypt the password to simulate stored value
        from src.core.security import encrypt_secret

        encrypted_password = encrypt_secret(plaintext_password)

        mock_password = MagicMock(spec=Password)
        mock_password.id = password_id
        mock_password.organization_id = test_org_id
        mock_password.name = "Test Password"
        mock_password.username = "testuser"
        mock_password.password_encrypted = encrypted_password
        mock_password.url = "https://test.com"
        mock_password.notes = "Test notes"
        mock_password.created_at = MagicMock()
        mock_password.updated_at = MagicMock()

        mock_password_repo = AsyncMock()
        mock_password_repo.get_by_id_and_org = AsyncMock(return_value=mock_password)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch("src.routers.passwords.PasswordRepository", return_value=mock_password_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/passwords/{password_id}/reveal"
                    )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Test Password"
            assert data["password"] == plaintext_password
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_get_password_not_found(self, test_user, test_org_id):
        """Test getting a non-existent password returns 404."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user
        password_id = uuid4()

        mock_password_repo = AsyncMock()
        mock_password_repo.get_by_id_and_org = AsyncMock(return_value=None)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch("src.routers.passwords.PasswordRepository", return_value=mock_password_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/passwords/{password_id}"
                    )

            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.integration
class TestPasswordsOrganizationIsolation:
    """Tests for organization-level password isolation."""

    async def test_cannot_access_other_org_passwords(self, test_user, other_org_id):
        """Test that users cannot access passwords from other organizations."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user
        password_id = uuid4()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                response = await client.get(
                    f"/api/organizations/{other_org_id}/passwords/{password_id}"
                )

            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_cannot_list_other_org_passwords(self, test_user, other_org_id):
        """Test that users cannot list passwords from other organizations."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                response = await client.get(f"/api/organizations/{other_org_id}/passwords")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.integration
class TestPasswordsUpdate:
    """Tests for password updates."""

    async def test_update_password_success(self, test_user, test_org_id):
        """Test successful password update."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user
        password_id = uuid4()

        mock_password = MagicMock(spec=Password)
        mock_password.id = password_id
        mock_password.organization_id = test_org_id
        mock_password.name = "Old Name"
        mock_password.username = "olduser"
        mock_password.url = "https://old.com"
        mock_password.notes = "Old notes"
        mock_password.created_at = MagicMock()
        mock_password.updated_at = MagicMock()

        mock_password_repo = AsyncMock()
        mock_password_repo.get_by_id_and_org = AsyncMock(return_value=mock_password)
        mock_password_repo.update = AsyncMock(return_value=mock_password)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch("src.routers.passwords.PasswordRepository", return_value=mock_password_repo):
                    response = await client.put(
                        f"/api/organizations/{test_org_id}/passwords/{password_id}",
                        json={"name": "New Name", "username": "newuser"})

            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_update_password_not_found(self, test_user, test_org_id):
        """Test updating a non-existent password returns 404."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user
        password_id = uuid4()

        mock_password_repo = AsyncMock()
        mock_password_repo.get_by_id_and_org = AsyncMock(return_value=None)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch("src.routers.passwords.PasswordRepository", return_value=mock_password_repo):
                    response = await client.put(
                        f"/api/organizations/{test_org_id}/passwords/{password_id}",
                        json={"name": "New Name"})

            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.integration
class TestPasswordsDelete:
    """Tests for password deletion."""

    async def test_delete_password_success(self, test_user, test_org_id):
        """Test successful password deletion."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user
        password_id = uuid4()

        mock_password = MagicMock(spec=Password)
        mock_password.id = password_id
        mock_password.name = "Test Password"

        mock_password_repo = AsyncMock()
        mock_password_repo.get_by_id_and_org = AsyncMock(return_value=mock_password)
        mock_password_repo.delete = AsyncMock()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch("src.routers.passwords.PasswordRepository", return_value=mock_password_repo):
                    response = await client.delete(
                        f"/api/organizations/{test_org_id}/passwords/{password_id}"
                    )

            assert response.status_code == 204
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_delete_password_not_found(self, test_user, test_org_id):
        """Test deleting a non-existent password returns 404."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user
        password_id = uuid4()

        mock_password_repo = AsyncMock()
        mock_password_repo.get_by_id_and_org = AsyncMock(return_value=None)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch("src.routers.passwords.PasswordRepository", return_value=mock_password_repo):
                    response = await client.delete(
                        f"/api/organizations/{test_org_id}/passwords/{password_id}"
                    )

            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
