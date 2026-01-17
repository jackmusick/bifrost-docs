"""
Integration tests for role-based access control (RBAC).

Tests the role hierarchy and access restrictions:
- OWNER > ADMINISTRATOR > CONTRIBUTOR > READER

Test Scenarios:
1. Admin-only endpoints - Non-admins (CONTRIBUTOR, READER) get 403
2. Owner-only endpoints - Non-owners get 403
3. Reader restrictions - READER cannot create/update/delete resources
4. Contributor access - Can perform CRUD on their organization's resources
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.auth import UserPrincipal, get_current_active_user
from src.main import app
from src.models.enums import UserRole
from src.models.orm.user import User


def create_mock_user(
    user_id=None,
    role=UserRole.CONTRIBUTOR,
    email="test@example.com",
    name="Test User") -> UserPrincipal:
    """Create a mock UserPrincipal for testing."""
    return UserPrincipal(
        user_id=user_id or uuid4(),
        email=email,
        name=name,
        role=role,
        is_active=True,
        is_verified=True)


@pytest_asyncio.fixture
async def client():
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_org_id():
    """Generate a test organization ID."""
    return uuid4()


@pytest.fixture
def owner_user(test_org_id):
    """Create an OWNER user."""
    return create_mock_user(role=UserRole.OWNER, email="owner@example.com")


@pytest.fixture
def admin_user(test_org_id):
    """Create an ADMINISTRATOR user."""
    return create_mock_user(
        role=UserRole.ADMINISTRATOR, email="admin@example.com"
    )


@pytest.fixture
def contributor_user(test_org_id):
    """Create a CONTRIBUTOR user."""
    return create_mock_user(
        role=UserRole.CONTRIBUTOR, email="contributor@example.com"
    )


@pytest.fixture
def reader_user(test_org_id):
    """Create a READER user."""
    return create_mock_user(role=UserRole.READER, email="reader@example.com")


# =============================================================================
# Admin-only Endpoint Tests
# =============================================================================


@pytest.mark.integration
class TestAdminEndpointsAccessControl:
    """
    Tests that admin-only endpoints require ADMINISTRATOR or OWNER role.

    These endpoints are in the /api/admin/* namespace and use RequireAdmin dependency.
    """

    async def test_get_users_as_owner(self, client: AsyncClient, owner_user):
        """Test that OWNER can access GET /api/admin/users."""
        app.dependency_overrides[get_current_active_user] = lambda: owner_user

        mock_user_repo = AsyncMock()
        mock_user_repo.get_all = AsyncMock(return_value=[])

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                with patch("src.routers.admin.UserRepository", return_value=mock_user_repo):
                    response = await test_client.get("/api/admin/users")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_get_users_as_admin(self, client: AsyncClient, admin_user):
        """Test that ADMINISTRATOR can access GET /api/admin/users."""
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        mock_user_repo = AsyncMock()
        mock_user_repo.get_all = AsyncMock(return_value=[])

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                with patch("src.routers.admin.UserRepository", return_value=mock_user_repo):
                    response = await test_client.get("/api/admin/users")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_get_users_as_contributor_forbidden(self, client: AsyncClient, contributor_user):
        """Test that CONTRIBUTOR cannot access GET /api/admin/users (403)."""
        app.dependency_overrides[get_current_active_user] = lambda: contributor_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.get("/api/admin/users")

            assert response.status_code == 403
            assert "administrator" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_get_users_as_reader_forbidden(self, client: AsyncClient, reader_user):
        """Test that READER cannot access GET /api/admin/users (403)."""
        app.dependency_overrides[get_current_active_user] = lambda: reader_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.get("/api/admin/users")

            assert response.status_code == 403
            assert "administrator" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_invite_user_as_admin(self, client: AsyncClient, admin_user):
        """Test that ADMINISTRATOR can access POST /api/admin/users/invite."""
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.post(
                    "/api/admin/users/invite",
                    json={"email": "newuser@example.com", "role": "contributor"})

            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_invite_user_as_contributor_forbidden(
        self, client: AsyncClient, contributor_user
    ):
        """Test that CONTRIBUTOR cannot access POST /api/admin/users/invite (403)."""
        app.dependency_overrides[get_current_active_user] = lambda: contributor_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.post(
                    "/api/admin/users/invite",
                    json={"email": "newuser@example.com", "role": "contributor"})

            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_invite_user_as_reader_forbidden(self, client: AsyncClient, reader_user):
        """Test that READER cannot access POST /api/admin/users/invite (403)."""
        app.dependency_overrides[get_current_active_user] = lambda: reader_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.post(
                    "/api/admin/users/invite",
                    json={"email": "newuser@example.com", "role": "contributor"})

            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_delete_user_as_admin(self, client: AsyncClient, admin_user):
        """Test that ADMINISTRATOR can access DELETE /api/admin/users/{id}."""
        app.dependency_overrides[get_current_active_user] = lambda: admin_user
        target_user_id = uuid4()

        mock_user = MagicMock(spec=User)
        mock_user.id = target_user_id
        mock_user.email = "target@example.com"
        mock_user.role = UserRole.CONTRIBUTOR  # Not an owner

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)
        mock_user_repo.delete = AsyncMock()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                with patch("src.routers.admin.UserRepository", return_value=mock_user_repo):
                    response = await test_client.delete(f"/api/admin/users/{target_user_id}")

            assert response.status_code == 204
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_delete_user_as_contributor_forbidden(
        self, client: AsyncClient, contributor_user
    ):
        """Test that CONTRIBUTOR cannot access DELETE /api/admin/users/{id} (403)."""
        app.dependency_overrides[get_current_active_user] = lambda: contributor_user
        target_user_id = uuid4()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.delete(f"/api/admin/users/{target_user_id}")

            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_delete_user_as_reader_forbidden(self, client: AsyncClient, reader_user):
        """Test that READER cannot access DELETE /api/admin/users/{id} (403)."""
        app.dependency_overrides[get_current_active_user] = lambda: reader_user
        target_user_id = uuid4()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.delete(f"/api/admin/users/{target_user_id}")

            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


# =============================================================================
# Owner-only Endpoint Tests
# =============================================================================


@pytest.mark.integration
class TestOwnerEndpointsAccessControl:
    """
    Tests that owner-only endpoints require OWNER role.

    These endpoints use RequireOwner dependency.
    """

    async def test_transfer_ownership_as_owner(self, client: AsyncClient, owner_user):
        """Test that OWNER can access POST /api/admin/transfer-ownership."""
        app.dependency_overrides[get_current_active_user] = lambda: owner_user
        new_owner_id = uuid4()

        mock_new_owner = MagicMock(spec=User)
        mock_new_owner.id = new_owner_id
        mock_new_owner.email = "newowner@example.com"
        mock_new_owner.role = UserRole.ADMINISTRATOR

        mock_current_owner = MagicMock(spec=User)
        mock_current_owner.id = owner_user.user_id
        mock_current_owner.email = owner_user.email
        mock_current_owner.role = UserRole.OWNER

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = AsyncMock(
            side_effect=lambda uid: mock_new_owner if uid == new_owner_id else mock_current_owner
        )
        mock_user_repo.update = AsyncMock()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                with patch("src.routers.admin.UserRepository", return_value=mock_user_repo):
                    response = await test_client.post(
                        "/api/admin/transfer-ownership",
                        json={"user_id": str(new_owner_id)})

            assert response.status_code == 200
            assert "transferred" in response.json()["message"].lower()
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_transfer_ownership_as_admin_forbidden(self, client: AsyncClient, admin_user):
        """Test that ADMINISTRATOR cannot access POST /api/admin/transfer-ownership (403)."""
        app.dependency_overrides[get_current_active_user] = lambda: admin_user
        new_owner_id = uuid4()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.post(
                    "/api/admin/transfer-ownership",
                    json={"user_id": str(new_owner_id)})

            assert response.status_code == 403
            assert "owner" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_transfer_ownership_as_contributor_forbidden(
        self, client: AsyncClient, contributor_user
    ):
        """Test that CONTRIBUTOR cannot access POST /api/admin/transfer-ownership (403)."""
        app.dependency_overrides[get_current_active_user] = lambda: contributor_user
        new_owner_id = uuid4()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.post(
                    "/api/admin/transfer-ownership",
                    json={"user_id": str(new_owner_id)})

            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_transfer_ownership_as_reader_forbidden(self, client: AsyncClient, reader_user):
        """Test that READER cannot access POST /api/admin/transfer-ownership (403)."""
        app.dependency_overrides[get_current_active_user] = lambda: reader_user
        new_owner_id = uuid4()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.post(
                    "/api/admin/transfer-ownership",
                    json={"user_id": str(new_owner_id)})

            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_update_role_to_owner_as_admin_forbidden(self, client: AsyncClient, admin_user):
        """Test that ADMINISTRATOR cannot grant OWNER role (403)."""
        app.dependency_overrides[get_current_active_user] = lambda: admin_user
        target_user_id = uuid4()

        mock_target_user = MagicMock(spec=User)
        mock_target_user.id = target_user_id
        mock_target_user.email = "target@example.com"
        mock_target_user.role = UserRole.CONTRIBUTOR

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=mock_target_user)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                with patch("src.routers.admin.UserRepository", return_value=mock_user_repo):
                    response = await test_client.patch(
                        f"/api/admin/users/{target_user_id}",
                        json={"role": "owner"})

            assert response.status_code == 403
            assert "owner" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_update_role_to_owner_as_owner_success(self, client: AsyncClient, owner_user):
        """Test that OWNER can grant OWNER role."""
        app.dependency_overrides[get_current_active_user] = lambda: owner_user
        target_user_id = uuid4()

        mock_target_user = MagicMock(spec=User)
        mock_target_user.id = target_user_id
        mock_target_user.email = "target@example.com"
        mock_target_user.name = "Target User"
        mock_target_user.role = UserRole.CONTRIBUTOR
        mock_target_user.is_active = True
        mock_target_user.created_at = MagicMock()
        mock_target_user.created_at.isoformat = MagicMock(return_value="2024-01-01T00:00:00")

        mock_updated_user = MagicMock(spec=User)
        mock_updated_user.id = target_user_id
        mock_updated_user.email = "target@example.com"
        mock_updated_user.name = "Target User"
        mock_updated_user.role = UserRole.OWNER
        mock_updated_user.is_active = True
        mock_updated_user.created_at = MagicMock()
        mock_updated_user.created_at.isoformat = MagicMock(return_value="2024-01-01T00:00:00")

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=mock_target_user)
        mock_user_repo.update_role = AsyncMock(return_value=mock_updated_user)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                with patch("src.routers.admin.UserRepository", return_value=mock_user_repo):
                    response = await test_client.patch(
                        f"/api/admin/users/{target_user_id}",
                        json={"role": "owner"})

            assert response.status_code == 200
            assert response.json()["role"] == "owner"
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


# =============================================================================
# Reader Restrictions Tests
# =============================================================================


@pytest.mark.integration
class TestReaderRestrictions:
    """
    Tests that READER role has read-only access.

    Readers can read resources but cannot create, update, or delete them.
    Write operations require CONTRIBUTOR role or higher.
    """

    async def test_reader_cannot_create_password(
        self, client: AsyncClient, reader_user, test_org_id
    ):
        """Test that READER cannot create passwords (403 Forbidden)."""
        app.dependency_overrides[get_current_active_user] = lambda: reader_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.post(
                    f"/api/organizations/{test_org_id}/passwords",
                    json={
                        "name": "Test Password",
                        "username": "testuser",
                        "password": "secret123",
                    })

            assert response.status_code == 403
            assert "contributor" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_reader_cannot_update_password(
        self, client: AsyncClient, reader_user, test_org_id
    ):
        """Test that READER cannot update passwords (403 Forbidden)."""
        app.dependency_overrides[get_current_active_user] = lambda: reader_user
        password_id = uuid4()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.put(
                    f"/api/organizations/{test_org_id}/passwords/{password_id}",
                    json={"name": "Updated Password"})

            assert response.status_code == 403
            assert "contributor" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_reader_cannot_delete_password(
        self, client: AsyncClient, reader_user, test_org_id
    ):
        """Test that READER cannot delete passwords (403 Forbidden)."""
        app.dependency_overrides[get_current_active_user] = lambda: reader_user
        password_id = uuid4()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.delete(
                    f"/api/organizations/{test_org_id}/passwords/{password_id}"
                )

            assert response.status_code == 403
            assert "contributor" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_reader_cannot_create_document(
        self, client: AsyncClient, reader_user, test_org_id
    ):
        """Test that READER cannot create documents (403 Forbidden)."""
        app.dependency_overrides[get_current_active_user] = lambda: reader_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.post(
                    f"/api/organizations/{test_org_id}/documents",
                    json={
                        "path": "/Test",
                        "name": "Test Document",
                        "content": "Test content",
                    })

            assert response.status_code == 403
            assert "contributor" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_reader_cannot_update_document(
        self, client: AsyncClient, reader_user, test_org_id
    ):
        """Test that READER cannot update documents (403 Forbidden)."""
        app.dependency_overrides[get_current_active_user] = lambda: reader_user
        doc_id = uuid4()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.put(
                    f"/api/organizations/{test_org_id}/documents/{doc_id}",
                    json={"name": "Updated Document"})

            assert response.status_code == 403
            assert "contributor" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_reader_cannot_delete_document(
        self, client: AsyncClient, reader_user, test_org_id
    ):
        """Test that READER cannot delete documents (403 Forbidden)."""
        app.dependency_overrides[get_current_active_user] = lambda: reader_user
        doc_id = uuid4()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.delete(
                    f"/api/organizations/{test_org_id}/documents/{doc_id}"
                )

            assert response.status_code == 403
            assert "contributor" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_reader_cannot_create_configuration(
        self, client: AsyncClient, reader_user, test_org_id
    ):
        """Test that READER cannot create configurations (403 Forbidden)."""
        app.dependency_overrides[get_current_active_user] = lambda: reader_user
        config_type_id = uuid4()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.post(
                    f"/api/organizations/{test_org_id}/configurations",
                    json={
                        "name": "Test Configuration",
                        "configuration_type_id": str(config_type_id),
                    })

            assert response.status_code == 403
            assert "contributor" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_reader_cannot_delete_configuration(
        self, client: AsyncClient, reader_user, test_org_id
    ):
        """Test that READER cannot delete configurations (403 Forbidden)."""
        app.dependency_overrides[get_current_active_user] = lambda: reader_user
        config_id = uuid4()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.delete(
                    f"/api/organizations/{test_org_id}/configurations/{config_id}"
                )

            assert response.status_code == 403
            assert "contributor" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_reader_can_list_passwords(self, client: AsyncClient, reader_user, test_org_id):
        """Test that READER can list passwords (read access)."""
        app.dependency_overrides[get_current_active_user] = lambda: reader_user

        mock_password_repo = AsyncMock()
        mock_password_repo.get_paginated_by_org = AsyncMock(return_value=([], 0))

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo):
                    response = await test_client.get(
                        f"/api/organizations/{test_org_id}/passwords"
                    )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_reader_can_list_documents(self, client: AsyncClient, reader_user, test_org_id):
        """Test that READER can list documents (read access)."""
        app.dependency_overrides[get_current_active_user] = lambda: reader_user

        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_paginated_by_org = AsyncMock(return_value=([], 0))

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                with patch(
                    "src.routers.documents.DocumentRepository", return_value=mock_doc_repo
                ):
                    response = await test_client.get(
                        f"/api/organizations/{test_org_id}/documents"
                    )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_reader_can_list_configurations(
        self, client: AsyncClient, reader_user, test_org_id
    ):
        """Test that READER can list configurations (read access)."""
        app.dependency_overrides[get_current_active_user] = lambda: reader_user

        mock_config_repo = AsyncMock()
        mock_config_repo.get_paginated_by_org = AsyncMock(return_value=([], 0))

        try:
            with patch(
                "src.routers.configurations.ConfigurationRepository",
                return_value=mock_config_repo,
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as test_client:
                    response = await test_client.get(
                        f"/api/organizations/{test_org_id}/configurations"
                    )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


# =============================================================================
# Contributor Access Tests
# =============================================================================


@pytest.mark.integration
class TestContributorAccess:
    """
    Tests that CONTRIBUTOR role can create, update, and delete resources
    within their own organization.
    """

    async def test_contributor_can_create_password(
        self, client: AsyncClient, contributor_user, test_org_id
    ):
        """Test that CONTRIBUTOR can create passwords in their org."""
        app.dependency_overrides[get_current_active_user] = lambda: contributor_user

        mock_password = MagicMock()
        mock_password.id = uuid4()
        mock_password.organization_id = test_org_id
        mock_password.name = "Test Password"
        mock_password.username = "testuser"
        mock_password.url = "https://example.com"
        mock_password.notes = "Test notes"
        mock_password.created_at = MagicMock()
        mock_password.updated_at = MagicMock()

        mock_password_repo = AsyncMock()
        mock_password_repo.create = AsyncMock(return_value=mock_password)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo
                ), patch("src.routers.passwords.index_entity_for_search", new_callable=AsyncMock):
                    response = await test_client.post(
                        f"/api/organizations/{test_org_id}/passwords",
                        json={
                            "name": "Test Password",
                            "username": "testuser",
                            "password": "secret123",
                            "url": "https://example.com",
                            "notes": "Test notes",
                        })

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "Test Password"
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_contributor_can_update_password(
        self, client: AsyncClient, contributor_user, test_org_id
    ):
        """Test that CONTRIBUTOR can update passwords in their org."""
        app.dependency_overrides[get_current_active_user] = lambda: contributor_user
        password_id = uuid4()

        mock_password = MagicMock()
        mock_password.id = password_id
        mock_password.organization_id = test_org_id
        mock_password.name = "Updated Password"
        mock_password.username = "updateduser"
        mock_password.url = "https://updated.com"
        mock_password.notes = "Updated notes"
        mock_password.created_at = MagicMock()
        mock_password.updated_at = MagicMock()

        mock_password_repo = AsyncMock()
        mock_password_repo.get_by_id_and_org = AsyncMock(return_value=mock_password)
        mock_password_repo.update = AsyncMock(return_value=mock_password)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo
                ), patch("src.routers.passwords.index_entity_for_search", new_callable=AsyncMock):
                    response = await test_client.put(
                        f"/api/organizations/{test_org_id}/passwords/{password_id}",
                        json={"name": "Updated Password"})

            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_contributor_can_delete_password(
        self, client: AsyncClient, contributor_user, test_org_id
    ):
        """Test that CONTRIBUTOR can delete passwords in their org."""
        app.dependency_overrides[get_current_active_user] = lambda: contributor_user
        password_id = uuid4()

        mock_password = MagicMock()
        mock_password.id = password_id
        mock_password.name = "Test Password"

        mock_password_repo = AsyncMock()
        mock_password_repo.get_by_id_and_org = AsyncMock(return_value=mock_password)
        mock_password_repo.delete = AsyncMock()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo
                ), patch(
                    "src.routers.passwords.remove_entity_from_search", new_callable=AsyncMock
                ):
                    response = await test_client.delete(
                        f"/api/organizations/{test_org_id}/passwords/{password_id}"
                    )

            assert response.status_code == 204
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_contributor_can_create_document(
        self, client: AsyncClient, contributor_user, test_org_id
    ):
        """Test that CONTRIBUTOR can create documents in their org."""
        app.dependency_overrides[get_current_active_user] = lambda: contributor_user

        mock_document = MagicMock()
        mock_document.id = uuid4()
        mock_document.organization_id = test_org_id
        mock_document.path = "/Infrastructure"
        mock_document.name = "Network Docs"
        mock_document.content = "# Network Documentation"
        mock_document.created_at = "2024-01-01T00:00:00Z"
        mock_document.updated_at = "2024-01-01T00:00:00Z"

        mock_doc_repo = AsyncMock()
        mock_doc_repo.create = AsyncMock(return_value=mock_document)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                with patch(
                    "src.routers.documents.DocumentRepository", return_value=mock_doc_repo
                ), patch("src.routers.documents.index_entity_for_search", new_callable=AsyncMock):
                    response = await test_client.post(
                        f"/api/organizations/{test_org_id}/documents",
                        json={
                            "path": "/Infrastructure",
                            "name": "Network Docs",
                            "content": "# Network Documentation",
                        })

            assert response.status_code == 201
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_contributor_can_update_document(
        self, client: AsyncClient, contributor_user, test_org_id
    ):
        """Test that CONTRIBUTOR can update documents in their org."""
        app.dependency_overrides[get_current_active_user] = lambda: contributor_user
        doc_id = uuid4()

        mock_document = MagicMock()
        mock_document.id = doc_id
        mock_document.organization_id = test_org_id
        mock_document.path = "/Infrastructure"
        mock_document.name = "Updated Docs"
        mock_document.content = "# Updated Content"
        mock_document.created_at = "2024-01-01T00:00:00Z"
        mock_document.updated_at = "2024-01-01T00:00:00Z"

        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id_and_org = AsyncMock(return_value=mock_document)
        mock_doc_repo.update = AsyncMock(return_value=mock_document)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                with patch(
                    "src.routers.documents.DocumentRepository", return_value=mock_doc_repo
                ), patch("src.routers.documents.index_entity_for_search", new_callable=AsyncMock):
                    response = await test_client.put(
                        f"/api/organizations/{test_org_id}/documents/{doc_id}",
                        json={"name": "Updated Docs", "content": "# Updated Content"})

            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_contributor_can_delete_configuration(
        self, client: AsyncClient, contributor_user, test_org_id
    ):
        """Test that CONTRIBUTOR can delete configurations in their org."""
        app.dependency_overrides[get_current_active_user] = lambda: contributor_user
        config_id = uuid4()

        mock_config_repo = AsyncMock()
        mock_config_repo.delete_for_org = AsyncMock(return_value=True)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                with patch(
                    "src.routers.configurations.ConfigurationRepository",
                    return_value=mock_config_repo
                ), patch(
                    "src.routers.configurations.remove_entity_from_search",
                    new_callable=AsyncMock
                ):
                    response = await test_client.delete(
                        f"/api/organizations/{test_org_id}/configurations/{config_id}"
                    )

            assert response.status_code == 204
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


# =============================================================================
# Role Hierarchy Tests
# =============================================================================


@pytest.mark.integration
class TestRoleHierarchy:
    """
    Tests the role hierarchy: OWNER > ADMINISTRATOR > CONTRIBUTOR > READER.

    Higher roles should have all permissions of lower roles.
    """

    async def test_owner_has_admin_access(self, client: AsyncClient, owner_user):
        """Test that OWNER has admin endpoint access (role hierarchy)."""
        app.dependency_overrides[get_current_active_user] = lambda: owner_user

        mock_user_repo = AsyncMock()
        mock_user_repo.get_all = AsyncMock(return_value=[])

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                with patch("src.routers.admin.UserRepository", return_value=mock_user_repo):
                    response = await test_client.get("/api/admin/users")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_admin_has_contributor_access(
        self, client: AsyncClient, admin_user, test_org_id
    ):
        """Test that ADMINISTRATOR has contributor-level access (can create resources)."""
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        mock_password = MagicMock()
        mock_password.id = uuid4()
        mock_password.organization_id = test_org_id
        mock_password.name = "Admin Created Password"
        mock_password.username = "admin"
        mock_password.url = None
        mock_password.notes = None
        mock_password.created_at = MagicMock()
        mock_password.updated_at = MagicMock()

        mock_password_repo = AsyncMock()
        mock_password_repo.create = AsyncMock(return_value=mock_password)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo
                ), patch("src.routers.passwords.index_entity_for_search", new_callable=AsyncMock):
                    response = await test_client.post(
                        f"/api/organizations/{test_org_id}/passwords",
                        json={
                            "name": "Admin Created Password",
                            "username": "admin",
                            "password": "secret123",
                        })

            assert response.status_code == 201
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_admin_has_reader_access(self, client: AsyncClient, admin_user, test_org_id):
        """Test that ADMINISTRATOR has reader-level access (can read resources)."""
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        mock_password_repo = AsyncMock()
        mock_password_repo.get_paginated_by_org = AsyncMock(return_value=([], 0))

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo):
                    response = await test_client.get(
                        f"/api/organizations/{test_org_id}/passwords"
                    )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_contributor_has_reader_access(
        self, client: AsyncClient, contributor_user, test_org_id
    ):
        """Test that CONTRIBUTOR has reader-level access (can read resources)."""
        app.dependency_overrides[get_current_active_user] = lambda: contributor_user

        mock_password_repo = AsyncMock()
        mock_password_repo.get_paginated_by_org = AsyncMock(return_value=([], 0))

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                with patch(
                    "src.routers.passwords.PasswordRepository",
                    return_value=mock_password_repo):
                    response = await test_client.get(
                        f"/api/organizations/{test_org_id}/passwords"
                    )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


# =============================================================================
# Admin Config Endpoint Tests
# =============================================================================


@pytest.mark.integration
class TestAdminConfigEndpoints:
    """Tests for admin configuration endpoints that require admin role."""

    async def test_get_config_as_admin(self, client: AsyncClient, admin_user):
        """Test that ADMINISTRATOR can access GET /api/admin/config."""
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.get("/api/admin/config")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_get_config_as_contributor_forbidden(
        self, client: AsyncClient, contributor_user
    ):
        """Test that CONTRIBUTOR cannot access GET /api/admin/config (403)."""
        app.dependency_overrides[get_current_active_user] = lambda: contributor_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.get("/api/admin/config")

            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_get_config_as_reader_forbidden(self, client: AsyncClient, reader_user):
        """Test that READER cannot access GET /api/admin/config (403)."""
        app.dependency_overrides[get_current_active_user] = lambda: reader_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.get("/api/admin/config")

            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_update_config_as_admin(self, client: AsyncClient, admin_user):
        """Test that ADMINISTRATOR can access PATCH /api/admin/config."""
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.patch(
                    "/api/admin/config",
                    json={"embedding_model": "text-embedding-3-large"})

            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_update_config_as_contributor_forbidden(
        self, client: AsyncClient, contributor_user
    ):
        """Test that CONTRIBUTOR cannot access PATCH /api/admin/config (403)."""
        app.dependency_overrides[get_current_active_user] = lambda: contributor_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.patch(
                    "/api/admin/config",
                    json={"embedding_model": "text-embedding-3-large"})

            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


# =============================================================================
# Reindex Endpoint Tests
# =============================================================================


@pytest.mark.integration
class TestReindexEndpoints:
    """Tests for reindex endpoints that require admin role."""

    async def test_get_reindex_status_as_admin(self, client: AsyncClient, admin_user):
        """Test that ADMINISTRATOR can access GET /api/admin/reindex/status."""
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.get("/api/admin/reindex/status")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_get_reindex_status_as_contributor_forbidden(
        self, client: AsyncClient, contributor_user
    ):
        """Test that CONTRIBUTOR cannot access GET /api/admin/reindex/status (403)."""
        app.dependency_overrides[get_current_active_user] = lambda: contributor_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.get("/api/admin/reindex/status")

            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_get_reindex_status_as_reader_forbidden(self, client: AsyncClient, reader_user):
        """Test that READER cannot access GET /api/admin/reindex/status (403)."""
        app.dependency_overrides[get_current_active_user] = lambda: reader_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as test_client:
                response = await test_client.get("/api/admin/reindex/status")

            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
