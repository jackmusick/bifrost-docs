"""
Integration tests for exports endpoints.

Tests the complete export flow including:
- Creating exports (admin only)
- Listing user's exports
- Getting single export
- Downloading export (presigned URL)
- Revoking export
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.auth import UserPrincipal, get_current_active_user
from src.core.database import get_db
from src.main import app
from src.models.enums import UserRole
from src.models.orm.export import Export, ExportStatus


@pytest_asyncio.fixture
async def client():
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def mock_admin_principal():
    """Create a mock admin principal for authentication."""
    return UserPrincipal(
        user_id=uuid4(),
        email="admin@example.com",
        name="Admin User",
        role=UserRole.ADMINISTRATOR,
        is_active=True,
        is_verified=True,
    )


@pytest.fixture
def mock_contributor_principal():
    """Create a mock contributor principal for authentication."""
    return UserPrincipal(
        user_id=uuid4(),
        email="contributor@example.com",
        name="Contributor User",
        role=UserRole.CONTRIBUTOR,
        is_active=True,
        is_verified=True,
    )


@pytest.fixture
def mock_other_user_principal():
    """Create a mock principal for a different user."""
    return UserPrincipal(
        user_id=uuid4(),
        email="other@example.com",
        name="Other User",
        role=UserRole.ADMINISTRATOR,
        is_active=True,
        is_verified=True,
    )


def create_mock_db_session():
    """Create a mock database session for testing."""
    mock_db = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.rollback = AsyncMock()
    return mock_db


@pytest_asyncio.fixture
async def admin_client(mock_admin_principal):
    """Create an async HTTP client with mocked admin authentication."""

    async def override_get_current_active_user():
        return mock_admin_principal

    app.dependency_overrides[get_current_active_user] = override_get_current_active_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    # Clean up
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def contributor_client(mock_contributor_principal):
    """Create an async HTTP client with mocked contributor authentication."""

    async def override_get_current_active_user():
        return mock_contributor_principal

    app.dependency_overrides[get_current_active_user] = override_get_current_active_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    # Clean up
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def other_user_client(mock_other_user_principal):
    """Create an async HTTP client with mocked other user authentication."""

    async def override_get_current_active_user():
        return mock_other_user_principal

    app.dependency_overrides[get_current_active_user] = override_get_current_active_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    # Clean up
    app.dependency_overrides.clear()


def create_mock_export(
    user_id=None,
    status=ExportStatus.PENDING,
    s3_key=None,
    file_size_bytes=None,
    revoked_at=None,
    expires_at=None,
    error_message=None,
    organization_ids=None,
):
    """Helper to create a mock export object that mimics the Export ORM model."""
    export_id = uuid4()
    now = datetime.now(UTC)

    # Create an Export-like object with proper attributes
    mock_export = MagicMock(spec=Export)
    mock_export.id = export_id
    mock_export.user_id = user_id or uuid4()
    mock_export.organization_ids = organization_ids
    mock_export.status = status
    mock_export.s3_key = s3_key
    mock_export.file_size_bytes = file_size_bytes
    mock_export.expires_at = expires_at or (now + timedelta(days=7))
    mock_export.revoked_at = revoked_at
    mock_export.error_message = error_message
    mock_export.created_at = now
    mock_export.updated_at = now
    return mock_export


@pytest.mark.integration
class TestExportsEndpointAuth:
    """Tests for export endpoint authentication."""

    async def test_unauthenticated_list_exports(self, client: AsyncClient):
        """Test that listing exports requires authentication."""
        response = await client.get("/api/exports")
        assert response.status_code == 401

    async def test_unauthenticated_create_export(self, client: AsyncClient):
        """Test that creating exports requires authentication."""
        response = await client.post(
            "/api/exports",
            json={"expires_in_days": 7},
        )
        assert response.status_code == 401

    async def test_unauthenticated_get_export(self, client: AsyncClient):
        """Test that getting an export requires authentication."""
        export_id = uuid4()
        response = await client.get(f"/api/exports/{export_id}")
        assert response.status_code == 401

    async def test_unauthenticated_download_export(self, client: AsyncClient):
        """Test that downloading an export requires authentication."""
        export_id = uuid4()
        response = await client.get(f"/api/exports/{export_id}/download")
        assert response.status_code == 401

    async def test_unauthenticated_revoke_export(self, client: AsyncClient):
        """Test that revoking an export requires authentication."""
        export_id = uuid4()
        response = await client.delete(f"/api/exports/{export_id}")
        assert response.status_code == 401


@pytest.mark.integration
class TestCreateExport:
    """Tests for export creation."""

    async def test_admin_can_create_export(self, mock_admin_principal):
        """Test that admin can create export."""
        mock_export = create_mock_export(user_id=mock_admin_principal.user_id)

        mock_repo = AsyncMock()
        mock_repo.create = AsyncMock(return_value=mock_export)

        mock_db = create_mock_db_session()

        async def override_get_current_active_user():
            return mock_admin_principal

        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_current_active_user] = override_get_current_active_user
        app.dependency_overrides[get_db] = override_get_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as ac:
                with (
                    patch("src.routers.exports.ExportRepository", return_value=mock_repo),
                    patch("src.services.export_service.process_export", new_callable=AsyncMock),
                ):
                    response = await ac.post(
                        "/api/exports",
                        json={"expires_in_days": 7},
                    )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert "id" in data

    async def test_export_starts_with_pending_status(self, mock_admin_principal):
        """Test that newly created export has pending status."""
        mock_export = create_mock_export(
            user_id=mock_admin_principal.user_id,
            status=ExportStatus.PENDING,
        )

        mock_repo = AsyncMock()
        mock_repo.create = AsyncMock(return_value=mock_export)

        mock_db = create_mock_db_session()

        async def override_get_current_active_user():
            return mock_admin_principal

        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_current_active_user] = override_get_current_active_user
        app.dependency_overrides[get_db] = override_get_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as ac:
                with (
                    patch("src.routers.exports.ExportRepository", return_value=mock_repo),
                    patch("src.services.export_service.process_export", new_callable=AsyncMock),
                ):
                    response = await ac.post(
                        "/api/exports",
                        json={},
                    )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"

    async def test_non_admin_cannot_create_export(
        self, contributor_client: AsyncClient
    ):
        """Test that non-admin users get 403 when creating export."""
        response = await contributor_client.post(
            "/api/exports",
            json={"expires_in_days": 7},
        )

        assert response.status_code == 403
        data = response.json()
        assert "administrator" in data["detail"].lower() or "role" in data["detail"].lower()

    async def test_create_export_with_organization_ids(self, mock_admin_principal):
        """Test creating export with specific organization IDs."""
        org_id_1 = uuid4()
        org_id_2 = uuid4()
        mock_export = create_mock_export(
            user_id=mock_admin_principal.user_id,
            organization_ids=[str(org_id_1), str(org_id_2)],
        )

        mock_repo = AsyncMock()
        mock_repo.create = AsyncMock(return_value=mock_export)

        mock_db = create_mock_db_session()

        async def override_get_current_active_user():
            return mock_admin_principal

        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_current_active_user] = override_get_current_active_user
        app.dependency_overrides[get_db] = override_get_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as ac:
                with (
                    patch("src.routers.exports.ExportRepository", return_value=mock_repo),
                    patch("src.services.export_service.process_export", new_callable=AsyncMock),
                ):
                    response = await ac.post(
                        "/api/exports",
                        json={
                            "organization_ids": [str(org_id_1), str(org_id_2)],
                            "expires_in_days": 14,
                        },
                    )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert data["organization_ids"] == [str(org_id_1), str(org_id_2)]


@pytest.mark.integration
class TestListExports:
    """Tests for listing exports."""

    async def test_list_user_exports(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test listing exports returns only user's exports."""
        mock_export_1 = create_mock_export(user_id=mock_admin_principal.user_id)
        mock_export_2 = create_mock_export(
            user_id=mock_admin_principal.user_id,
            status=ExportStatus.COMPLETED,
            s3_key="exports/test.zip",
            file_size_bytes=1024,
        )

        mock_repo = AsyncMock()
        mock_repo.get_by_user = AsyncMock(return_value=[mock_export_1, mock_export_2])

        with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
            response = await admin_client.get("/api/exports")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    async def test_list_exports_pagination(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test listing exports with pagination parameters."""
        mock_export = create_mock_export(user_id=mock_admin_principal.user_id)

        mock_repo = AsyncMock()
        mock_repo.get_by_user = AsyncMock(return_value=[mock_export])

        with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
            response = await admin_client.get(
                "/api/exports",
                params={"limit": 10, "offset": 5},
            )

        assert response.status_code == 200
        # Verify pagination params were passed to repository
        mock_repo.get_by_user.assert_called_once()
        call_kwargs = mock_repo.get_by_user.call_args[1]
        assert call_kwargs["limit"] == 10
        assert call_kwargs["offset"] == 5

    async def test_list_exports_empty(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test listing exports when user has no exports."""
        mock_repo = AsyncMock()
        mock_repo.get_by_user = AsyncMock(return_value=[])

        with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
            response = await admin_client.get("/api/exports")

        assert response.status_code == 200
        data = response.json()
        assert data == []


@pytest.mark.integration
class TestGetSingleExport:
    """Tests for getting a single export."""

    async def test_get_own_export(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test getting user's own export."""
        export_id = uuid4()
        mock_export = create_mock_export(user_id=mock_admin_principal.user_id)
        mock_export.id = export_id

        mock_repo = AsyncMock()
        mock_repo.get_by_id_and_user = AsyncMock(return_value=mock_export)

        with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
            response = await admin_client.get(f"/api/exports/{export_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(export_id)

    async def test_get_other_users_export_returns_404(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test that getting another user's export returns 404."""
        export_id = uuid4()

        mock_repo = AsyncMock()
        # Repository returns None because export doesn't belong to user
        mock_repo.get_by_id_and_user = AsyncMock(return_value=None)

        with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
            response = await admin_client.get(f"/api/exports/{export_id}")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    async def test_get_nonexistent_export_returns_404(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test getting a non-existent export returns 404."""
        export_id = uuid4()

        mock_repo = AsyncMock()
        mock_repo.get_by_id_and_user = AsyncMock(return_value=None)

        with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
            response = await admin_client.get(f"/api/exports/{export_id}")

        assert response.status_code == 404


@pytest.mark.integration
class TestRevokeExport:
    """Tests for revoking exports."""

    async def test_revoke_own_export(self, mock_admin_principal):
        """Test revoking user's own export."""
        export_id = uuid4()
        mock_export = create_mock_export(user_id=mock_admin_principal.user_id)
        mock_export.id = export_id

        revoked_export = create_mock_export(
            user_id=mock_admin_principal.user_id,
            revoked_at=datetime.now(UTC),
        )
        revoked_export.id = export_id

        mock_repo = AsyncMock()
        mock_repo.get_by_id_and_user = AsyncMock(return_value=mock_export)
        mock_repo.revoke = AsyncMock(return_value=revoked_export)

        mock_db = create_mock_db_session()

        async def override_get_current_active_user():
            return mock_admin_principal

        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_current_active_user] = override_get_current_active_user
        app.dependency_overrides[get_db] = override_get_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as ac:
                with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
                    response = await ac.delete(f"/api/exports/{export_id}")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["revoked"] is True
        assert "revoked_at" in data

    async def test_revoked_export_has_revoked_at_set(self, mock_admin_principal):
        """Test that revoked export has revoked_at timestamp."""
        export_id = uuid4()
        mock_export = create_mock_export(user_id=mock_admin_principal.user_id)
        mock_export.id = export_id

        revoke_time = datetime.now(UTC)
        revoked_export = create_mock_export(
            user_id=mock_admin_principal.user_id,
            revoked_at=revoke_time,
        )
        revoked_export.id = export_id

        mock_repo = AsyncMock()
        mock_repo.get_by_id_and_user = AsyncMock(return_value=mock_export)
        mock_repo.revoke = AsyncMock(return_value=revoked_export)

        mock_db = create_mock_db_session()

        async def override_get_current_active_user():
            return mock_admin_principal

        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_current_active_user] = override_get_current_active_user
        app.dependency_overrides[get_db] = override_get_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as ac:
                with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
                    response = await ac.delete(f"/api/exports/{export_id}")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["revoked_at"] is not None

    async def test_revoke_already_revoked_export(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test revoking an already revoked export returns error."""
        export_id = uuid4()
        mock_export = create_mock_export(
            user_id=mock_admin_principal.user_id,
            revoked_at=datetime.now(UTC),  # Already revoked
        )
        mock_export.id = export_id

        mock_repo = AsyncMock()
        mock_repo.get_by_id_and_user = AsyncMock(return_value=mock_export)

        with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
            response = await admin_client.delete(f"/api/exports/{export_id}")

        assert response.status_code == 400
        data = response.json()
        assert "already" in data["detail"].lower() or "revoked" in data["detail"].lower()

    async def test_revoke_nonexistent_export_returns_404(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test revoking a non-existent export returns 404."""
        export_id = uuid4()

        mock_repo = AsyncMock()
        mock_repo.get_by_id_and_user = AsyncMock(return_value=None)

        with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
            response = await admin_client.delete(f"/api/exports/{export_id}")

        assert response.status_code == 404


@pytest.mark.integration
class TestDownloadExport:
    """Tests for downloading exports (presigned URL)."""

    async def test_download_completed_export(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test downloading a completed export returns presigned URL."""
        export_id = uuid4()
        mock_export = create_mock_export(
            user_id=mock_admin_principal.user_id,
            status=ExportStatus.COMPLETED,
            s3_key="exports/test-export.zip",
            file_size_bytes=10240,
        )
        mock_export.id = export_id

        mock_repo = AsyncMock()
        mock_repo.get_by_id_and_user = AsyncMock(return_value=mock_export)

        mock_file_storage = AsyncMock()
        mock_file_storage.generate_download_url = AsyncMock(
            return_value="https://s3.example.com/presigned-url?token=abc123"
        )

        with (
            patch("src.routers.exports.ExportRepository", return_value=mock_repo),
            patch(
                "src.routers.exports.get_file_storage_service",
                return_value=mock_file_storage,
            ),
        ):
            response = await admin_client.get(f"/api/exports/{export_id}/download")

        assert response.status_code == 200
        data = response.json()
        assert "download_url" in data
        assert data["download_url"].startswith("https://")
        assert "expires_in_seconds" in data

    async def test_download_pending_export_fails(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test downloading a pending export returns error."""
        export_id = uuid4()
        mock_export = create_mock_export(
            user_id=mock_admin_principal.user_id,
            status=ExportStatus.PENDING,
        )
        mock_export.id = export_id

        mock_repo = AsyncMock()
        mock_repo.get_by_id_and_user = AsyncMock(return_value=mock_export)

        with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
            response = await admin_client.get(f"/api/exports/{export_id}/download")

        assert response.status_code == 400
        data = response.json()
        assert "not ready" in data["detail"].lower() or "pending" in data["detail"].lower()

    async def test_download_processing_export_fails(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test downloading a processing export returns error."""
        export_id = uuid4()
        mock_export = create_mock_export(
            user_id=mock_admin_principal.user_id,
            status=ExportStatus.PROCESSING,
        )
        mock_export.id = export_id

        mock_repo = AsyncMock()
        mock_repo.get_by_id_and_user = AsyncMock(return_value=mock_export)

        with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
            response = await admin_client.get(f"/api/exports/{export_id}/download")

        assert response.status_code == 400
        data = response.json()
        assert "not ready" in data["detail"].lower() or "processing" in data["detail"].lower()

    async def test_download_failed_export_fails(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test downloading a failed export returns error."""
        export_id = uuid4()
        mock_export = create_mock_export(
            user_id=mock_admin_principal.user_id,
            status=ExportStatus.FAILED,
            error_message="Export failed due to timeout",
        )
        mock_export.id = export_id

        mock_repo = AsyncMock()
        mock_repo.get_by_id_and_user = AsyncMock(return_value=mock_export)

        with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
            response = await admin_client.get(f"/api/exports/{export_id}/download")

        assert response.status_code == 400
        data = response.json()
        assert "not ready" in data["detail"].lower() or "failed" in data["detail"].lower()

    async def test_download_revoked_export_fails(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test downloading a revoked export returns error."""
        export_id = uuid4()
        mock_export = create_mock_export(
            user_id=mock_admin_principal.user_id,
            status=ExportStatus.COMPLETED,
            s3_key="exports/test-export.zip",
            file_size_bytes=10240,
            revoked_at=datetime.now(UTC),  # Revoked
        )
        mock_export.id = export_id

        mock_repo = AsyncMock()
        mock_repo.get_by_id_and_user = AsyncMock(return_value=mock_export)

        with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
            response = await admin_client.get(f"/api/exports/{export_id}/download")

        assert response.status_code == 400
        data = response.json()
        assert "revoked" in data["detail"].lower()

    async def test_download_expired_export_fails(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test downloading an expired export returns error."""
        export_id = uuid4()
        mock_export = create_mock_export(
            user_id=mock_admin_principal.user_id,
            status=ExportStatus.COMPLETED,
            s3_key="exports/test-export.zip",
            file_size_bytes=10240,
            expires_at=datetime.now(UTC) - timedelta(days=1),  # Expired
        )
        mock_export.id = export_id

        mock_repo = AsyncMock()
        mock_repo.get_by_id_and_user = AsyncMock(return_value=mock_export)

        with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
            response = await admin_client.get(f"/api/exports/{export_id}/download")

        assert response.status_code == 400
        data = response.json()
        assert "expired" in data["detail"].lower()

    async def test_download_nonexistent_export_returns_404(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test downloading a non-existent export returns 404."""
        export_id = uuid4()

        mock_repo = AsyncMock()
        mock_repo.get_by_id_and_user = AsyncMock(return_value=None)

        with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
            response = await admin_client.get(f"/api/exports/{export_id}/download")

        assert response.status_code == 404

    async def test_download_url_structure(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test that download response contains proper URL structure."""
        export_id = uuid4()
        mock_export = create_mock_export(
            user_id=mock_admin_principal.user_id,
            status=ExportStatus.COMPLETED,
            s3_key="exports/test-export.zip",
            file_size_bytes=10240,
        )
        mock_export.id = export_id

        mock_repo = AsyncMock()
        mock_repo.get_by_id_and_user = AsyncMock(return_value=mock_export)

        expected_url = "https://bucket.s3.amazonaws.com/exports/test-export.zip?X-Amz-Signature=xyz"
        mock_file_storage = AsyncMock()
        mock_file_storage.generate_download_url = AsyncMock(return_value=expected_url)

        with (
            patch("src.routers.exports.ExportRepository", return_value=mock_repo),
            patch(
                "src.routers.exports.get_file_storage_service",
                return_value=mock_file_storage,
            ),
        ):
            response = await admin_client.get(f"/api/exports/{export_id}/download")

        assert response.status_code == 200
        data = response.json()
        assert data["download_url"] == expected_url
        assert data["expires_in_seconds"] == 3600  # 1 hour as per router


@pytest.mark.integration
class TestExportsUserIsolation:
    """Tests for user isolation of exports."""

    async def test_user_only_sees_own_exports(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test that user only sees their own exports in list."""
        mock_export = create_mock_export(user_id=mock_admin_principal.user_id)

        mock_repo = AsyncMock()
        mock_repo.get_by_user = AsyncMock(return_value=[mock_export])

        with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
            response = await admin_client.get("/api/exports")

        assert response.status_code == 200
        # Verify repository was called with correct user_id
        mock_repo.get_by_user.assert_called_once()
        call_args = mock_repo.get_by_user.call_args[0]
        assert call_args[0] == mock_admin_principal.user_id

    async def test_cannot_get_other_users_export_by_id(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test that user cannot access another user's export by ID."""
        other_user_export_id = uuid4()

        mock_repo = AsyncMock()
        # Repository enforces user scope - returns None for other user's export
        mock_repo.get_by_id_and_user = AsyncMock(return_value=None)

        with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
            response = await admin_client.get(f"/api/exports/{other_user_export_id}")

        assert response.status_code == 404

    async def test_cannot_revoke_other_users_export(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test that user cannot revoke another user's export."""
        other_user_export_id = uuid4()

        mock_repo = AsyncMock()
        mock_repo.get_by_id_and_user = AsyncMock(return_value=None)

        with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
            response = await admin_client.delete(f"/api/exports/{other_user_export_id}")

        assert response.status_code == 404

    async def test_cannot_download_other_users_export(
        self, admin_client: AsyncClient, mock_admin_principal
    ):
        """Test that user cannot download another user's export."""
        other_user_export_id = uuid4()

        mock_repo = AsyncMock()
        mock_repo.get_by_id_and_user = AsyncMock(return_value=None)

        with patch("src.routers.exports.ExportRepository", return_value=mock_repo):
            response = await admin_client.get(
                f"/api/exports/{other_user_export_id}/download"
            )

        assert response.status_code == 404
