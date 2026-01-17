"""Tests for mutation application endpoint."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from httpx import ASGITransport, AsyncClient

from src.core.auth import UserPrincipal, get_current_active_user
from src.main import app
from src.models.enums import UserRole
from src.models.orm.organization import Organization
from src.models.orm.document import Document
from src.models.orm.custom_asset import CustomAsset


def create_mock_user(
    user_id=None,
    role=UserRole.CONTRIBUTOR,
    email="test@example.com",
    name="Test User",
) -> UserPrincipal:
    """Create a mock UserPrincipal for testing."""
    return UserPrincipal(
        user_id=user_id or uuid4(),
        email=email,
        name=name,
        role=role,
        is_active=True,
        is_verified=True,
    )


@pytest_asyncio.fixture
async def client():
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def contributor_user():
    """Create a CONTRIBUTOR user."""
    return create_mock_user(
        role=UserRole.CONTRIBUTOR, email="contributor@example.com"
    )


@pytest.fixture
def reader_user():
    """Create a READER user."""
    return create_mock_user(role=UserRole.READER, email="reader@example.com")


@pytest.mark.integration
class TestApplyDocumentMutation:
    """Tests for applying document mutations."""

    @pytest.mark.asyncio
    async def test_apply_document_mutation_success(
        self, client: AsyncClient, contributor_user
    ):
        """Test successfully applying a document mutation."""
        # Arrange
        org_id = uuid4()
        doc_id = uuid4()

        # Mock organization
        mock_org = MagicMock(spec=Organization)
        mock_org.id = org_id
        mock_org.name = "Test Org"
        mock_org.is_enabled = True

        # Mock document
        mock_document = MagicMock(spec=Document)
        mock_document.id = doc_id
        mock_document.name = "Test Doc"
        mock_document.path = "/test"
        mock_document.content = "# Original"
        mock_document.organization_id = org_id
        mock_document.updated_by_user_id = contributor_user.user_id
        mock_document.is_enabled = True

        # Mock database session
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        request_payload = {
            "conversation_id": str(uuid4()),
            "request_id": str(uuid4()),
            "entity_type": "document",
            "entity_id": str(doc_id),
            "organization_id": str(org_id),
            "mutation": {
                "content": "# Updated Content\n\nThis is the cleaned up document.",
                "summary": "Fixed formatting and structure",
            },
        }

        # Override auth
        app.dependency_overrides[get_current_active_user] = lambda: contributor_user

        # Mock database dependency
        from src.core.database import get_db
        async def mock_get_db():
            yield mock_db
        app.dependency_overrides[get_db] = mock_get_db

        try:
            with patch("src.routers.search.OrganizationRepository") as mock_org_repo_cls:
                with patch("src.routers.search.DocumentRepository") as mock_doc_repo_cls:
                    # Setup mocks
                    mock_org_repo = mock_org_repo_cls.return_value
                    mock_org_repo.get_by_id = AsyncMock(return_value=mock_org)

                    mock_doc_repo = mock_doc_repo_cls.return_value
                    mock_doc_repo.get_by_id = AsyncMock(return_value=mock_document)

                    # Act
                    response = await client.post(
                        "/api/search/chat/apply",
                        json=request_payload,
                    )

                    # Assert
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["entity_id"] == str(doc_id)
                    assert f"documents/{org_id}/{doc_id}" in data["link"]

                    # Verify document content was updated
                    assert (
                        mock_document.content
                        == request_payload["mutation"]["content"]
                    )
                    assert (
                        mock_document.updated_by_user_id == contributor_user.user_id
                    )

                    # Verify db.commit and db.refresh were called
                    mock_db.commit.assert_called_once()
                    mock_db.refresh.assert_called_once_with(mock_document)

        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    @pytest.mark.asyncio
    async def test_apply_document_mutation_reader_role_forbidden(
        self, client: AsyncClient, reader_user
    ):
        """Test that Reader role cannot apply mutations."""
        request_payload = {
            "conversation_id": str(uuid4()),
            "request_id": str(uuid4()),
            "entity_type": "document",
            "entity_id": str(uuid4()),
            "organization_id": str(uuid4()),
            "mutation": {"content": "# Updated", "summary": "Test"},
        }

        app.dependency_overrides[get_current_active_user] = lambda: reader_user

        try:
            response = await client.post(
                "/api/search/chat/apply",
                json=request_payload,
            )

            assert response.status_code == 403
            assert "permission" in response.json()["detail"].lower()

        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    @pytest.mark.asyncio
    async def test_apply_mutation_entity_not_found(
        self, client: AsyncClient, contributor_user
    ):
        """Test applying mutation to non-existent entity."""
        org_id = uuid4()
        doc_id = uuid4()

        # Mock organization exists
        mock_org = MagicMock(spec=Organization)
        mock_org.id = org_id
        mock_org.name = "Test Org"
        mock_org.is_enabled = True

        request_payload = {
            "conversation_id": str(uuid4()),
            "request_id": str(uuid4()),
            "entity_type": "document",
            "entity_id": str(doc_id),
            "organization_id": str(org_id),
            "mutation": {"content": "# Test", "summary": "Test"},
        }

        app.dependency_overrides[get_current_active_user] = lambda: contributor_user

        try:
            with patch("src.routers.search.OrganizationRepository") as mock_org_repo_cls:
                with patch(
                    "src.routers.search.DocumentRepository"
                ) as mock_doc_repo_cls:
                    mock_org_repo = mock_org_repo_cls.return_value
                    mock_org_repo.get_by_id = AsyncMock(return_value=mock_org)

                    mock_doc_repo = mock_doc_repo_cls.return_value
                    mock_doc_repo.get_by_id = AsyncMock(return_value=None)

                    response = await client.post(
                        "/api/search/chat/apply",
                        json=request_payload,
                    )

                    assert response.status_code == 404

        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    @pytest.mark.asyncio
    async def test_apply_mutation_wrong_organization(
        self, client: AsyncClient, contributor_user
    ):
        """Test applying mutation to entity from different org."""
        org_id = uuid4()
        wrong_org_id = uuid4()
        doc_id = uuid4()

        # Mock organization
        mock_org = MagicMock(spec=Organization)
        mock_org.id = org_id
        mock_org.name = "Test Org"
        mock_org.is_enabled = True

        # Mock document that belongs to wrong_org
        mock_document = MagicMock(spec=Document)
        mock_document.id = doc_id
        mock_document.name = "Test Doc"
        mock_document.path = "/test"
        mock_document.content = "# Original"
        mock_document.organization_id = wrong_org_id  # Different org
        mock_document.updated_by_user_id = contributor_user.user_id
        mock_document.is_enabled = True

        request_payload = {
            "conversation_id": str(uuid4()),
            "request_id": str(uuid4()),
            "entity_type": "document",
            "entity_id": str(doc_id),
            "organization_id": str(org_id),
            "mutation": {"content": "# Test", "summary": "Test"},
        }

        app.dependency_overrides[get_current_active_user] = lambda: contributor_user

        try:
            with patch("src.routers.search.OrganizationRepository") as mock_org_repo_cls:
                with patch(
                    "src.routers.search.DocumentRepository"
                ) as mock_doc_repo_cls:
                    mock_org_repo = mock_org_repo_cls.return_value
                    mock_org_repo.get_by_id = AsyncMock(return_value=mock_org)

                    mock_doc_repo = mock_doc_repo_cls.return_value
                    mock_doc_repo.get_by_id = AsyncMock(return_value=mock_document)

                    response = await client.post(
                        "/api/search/chat/apply",
                        json=request_payload,
                    )

                    # Should return 404 because document belongs to different org
                    assert response.status_code == 404

        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.integration
class TestApplyAssetMutation:
    """Tests for applying custom asset mutations."""

    @pytest.mark.asyncio
    async def test_apply_asset_mutation_success(
        self, client: AsyncClient, contributor_user
    ):
        """Test successfully applying a custom asset mutation."""
        org_id = uuid4()
        asset_id = uuid4()

        # Mock organization
        mock_org = MagicMock(spec=Organization)
        mock_org.id = org_id
        mock_org.name = "Test Org"
        mock_org.is_enabled = True

        # Mock custom asset
        mock_asset = MagicMock(spec=CustomAsset)
        mock_asset.id = asset_id
        mock_asset.custom_asset_type_id = uuid4()
        mock_asset.organization_id = org_id
        mock_asset.values = {"ip_address": "10.0.0.1", "location": "DC1"}
        mock_asset.updated_by_user_id = contributor_user.user_id
        mock_asset.is_enabled = True

        # Mock database session
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        request_payload = {
            "conversation_id": str(uuid4()),
            "request_id": str(uuid4()),
            "entity_type": "custom_asset",
            "entity_id": str(asset_id),
            "organization_id": str(org_id),
            "mutation": {
                "field_updates": {"ip_address": "10.0.0.5", "location": "DC2"},
                "summary": "Updated IP and location",
            },
        }

        app.dependency_overrides[get_current_active_user] = lambda: contributor_user

        # Mock database dependency
        from src.core.database import get_db
        async def mock_get_db():
            yield mock_db
        app.dependency_overrides[get_db] = mock_get_db

        try:
            with patch("src.routers.search.OrganizationRepository") as mock_org_repo_cls:
                with patch(
                    "src.routers.search.CustomAssetRepository"
                ) as mock_asset_repo_cls:
                    mock_org_repo = mock_org_repo_cls.return_value
                    mock_org_repo.get_by_id = AsyncMock(return_value=mock_org)

                    mock_asset_repo = mock_asset_repo_cls.return_value
                    mock_asset_repo.get_by_id = AsyncMock(return_value=mock_asset)

                    response = await client.post(
                        "/api/search/chat/apply",
                        json=request_payload,
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True

                    # Verify asset was updated
                    assert mock_asset.values["ip_address"] == "10.0.0.5"
                    assert mock_asset.values["location"] == "DC2"
                    assert mock_asset.updated_by_user_id == contributor_user.user_id

                    # Verify db.commit and db.refresh were called
                    mock_db.commit.assert_called_once()
                    mock_db.refresh.assert_called_once_with(mock_asset)

        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    @pytest.mark.asyncio
    async def test_apply_asset_mutation_reader_role_forbidden(
        self, client: AsyncClient, reader_user
    ):
        """Test that Reader role cannot apply asset mutations."""
        request_payload = {
            "conversation_id": str(uuid4()),
            "request_id": str(uuid4()),
            "entity_type": "custom_asset",
            "entity_id": str(uuid4()),
            "organization_id": str(uuid4()),
            "mutation": {
                "field_updates": {"ip_address": "10.0.0.5"},
                "summary": "Test",
            },
        }

        app.dependency_overrides[get_current_active_user] = lambda: reader_user

        try:
            response = await client.post(
                "/api/search/chat/apply",
                json=request_payload,
            )

            assert response.status_code == 403
            assert "permission" in response.json()["detail"].lower()

        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
