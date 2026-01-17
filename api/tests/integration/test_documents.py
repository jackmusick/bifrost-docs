"""
Integration tests for documents endpoints.

Tests the complete document CRUD flow including:
- Creating documents at different paths
- Listing documents with path filter
- Getting distinct folder paths
- Moving documents (updating path)
- Organization access
"""

from unittest.mock import AsyncMock, patch
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
        base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_user_principal():
    """Create a mock user principal for authentication."""
    return UserPrincipal(
        user_id=uuid4(),
        email="test@example.com",
        name="Test User",
        role=UserRole.CONTRIBUTOR,
        is_active=True,
        is_verified=True,
    )


@pytest.fixture
def mock_superuser_principal():
    """Create a mock superuser principal for authentication."""
    return UserPrincipal(
        user_id=uuid4(),
        email="admin@example.com",
        name="Admin User",
        role=UserRole.OWNER,
        is_active=True,
        is_verified=True)


@pytest_asyncio.fixture
async def authenticated_client(mock_user_principal):
    """Create an async HTTP client with mocked authentication."""

    async def override_get_current_active_user():
        return mock_user_principal

    app.dependency_overrides[get_current_active_user] = override_get_current_active_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test") as ac:
        yield ac

    # Clean up
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def superuser_client(mock_superuser_principal):
    """Create an async HTTP client with mocked superuser authentication."""

    async def override_get_current_active_user():
        return mock_superuser_principal

    app.dependency_overrides[get_current_active_user] = override_get_current_active_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test") as ac:
        yield ac

    # Clean up
    app.dependency_overrides.clear()


@pytest.mark.integration
class TestDocumentsEndpointAuth:
    """Tests for document endpoint authentication."""

    async def test_unauthenticated_list_documents(self, client: AsyncClient):
        """Test that listing documents requires authentication."""
        org_id = uuid4()
        response = await client.get(f"/api/organizations/{org_id}/documents")
        assert response.status_code == 401

    async def test_unauthenticated_create_document(self, client: AsyncClient):
        """Test that creating documents requires authentication."""
        org_id = uuid4()
        response = await client.post(
            f"/api/organizations/{org_id}/documents",
            json={"path": "/Test", "name": "Test Doc", "content": "# Test"})
        assert response.status_code == 401

    async def test_unauthenticated_get_document(self, client: AsyncClient):
        """Test that getting a document requires authentication."""
        org_id = uuid4()
        doc_id = uuid4()
        response = await client.get(f"/api/organizations/{org_id}/documents/{doc_id}")
        assert response.status_code == 401

    async def test_unauthenticated_get_folders(self, client: AsyncClient):
        """Test that getting folders requires authentication."""
        org_id = uuid4()
        response = await client.get(f"/api/organizations/{org_id}/documents/folders")
        assert response.status_code == 401


@pytest.mark.integration
class TestDocumentsCRUD:
    """Tests for document CRUD operations with mocked authentication and database."""

    async def test_create_document_success(
        self, authenticated_client: AsyncClient, mock_user_principal
    ):
        """Test creating a document with valid data."""
        org_id = uuid4()

        mock_doc = AsyncMock()
        mock_doc.id = uuid4()
        mock_doc.organization_id = org_id
        mock_doc.path = "/Infrastructure/Network"
        mock_doc.name = "Network Diagram"
        mock_doc.content = "# Network Diagram\n\nDescription here."
        mock_doc.created_at = "2026-01-12T00:00:00Z"
        mock_doc.updated_at = "2026-01-12T00:00:00Z"

        mock_doc_repo = AsyncMock()
        mock_doc_repo.create = AsyncMock(return_value=mock_doc)

        with patch(
                "src.routers.documents.DocumentRepository", return_value=mock_doc_repo
            ):
            response = await authenticated_client.post(
                f"/api/organizations/{org_id}/documents",
                json={
                    "path": "/Infrastructure/Network",
                    "name": "Network Diagram",
                    "content": "# Network Diagram\n\nDescription here.",
                })

        assert response.status_code == 201
        data = response.json()
        assert data["path"] == "/Infrastructure/Network"
        assert data["name"] == "Network Diagram"
        assert "id" in data

    async def test_list_documents_success(
        self, authenticated_client: AsyncClient
    ):
        """Test listing documents for an organization."""
        org_id = uuid4()

        mock_doc1 = AsyncMock()
        mock_doc1.id = uuid4()
        mock_doc1.organization_id = org_id
        mock_doc1.path = "/Infrastructure"
        mock_doc1.name = "Overview"
        mock_doc1.content = "# Overview"
        mock_doc1.created_at = "2026-01-12T00:00:00Z"
        mock_doc1.updated_at = "2026-01-12T00:00:00Z"

        mock_doc2 = AsyncMock()
        mock_doc2.id = uuid4()
        mock_doc2.organization_id = org_id
        mock_doc2.path = "/Infrastructure/Network"
        mock_doc2.name = "Network Docs"
        mock_doc2.content = "# Network"
        mock_doc2.created_at = "2026-01-12T00:00:00Z"
        mock_doc2.updated_at = "2026-01-12T00:00:00Z"

        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_all_by_org = AsyncMock(return_value=[mock_doc1, mock_doc2])

        with patch(
                "src.routers.documents.DocumentRepository", return_value=mock_doc_repo
            ):
            response = await authenticated_client.get(
                f"/api/organizations/{org_id}/documents")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    async def test_list_documents_with_path_filter(
        self, authenticated_client: AsyncClient
    ):
        """Test listing documents filtered by path."""
        org_id = uuid4()

        mock_doc = AsyncMock()
        mock_doc.id = uuid4()
        mock_doc.organization_id = org_id
        mock_doc.path = "/Infrastructure/Network"
        mock_doc.name = "Network Docs"
        mock_doc.content = "# Network"
        mock_doc.created_at = "2026-01-12T00:00:00Z"
        mock_doc.updated_at = "2026-01-12T00:00:00Z"

        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_path = AsyncMock(return_value=[mock_doc])

        with patch(
                "src.routers.documents.DocumentRepository", return_value=mock_doc_repo
            ):
            response = await authenticated_client.get(
                f"/api/organizations/{org_id}/documents",
                params={"path": "/Infrastructure/Network"})

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["path"] == "/Infrastructure/Network"

    async def test_get_folders_success(
        self, authenticated_client: AsyncClient
    ):
        """Test getting distinct folder paths."""
        org_id = uuid4()

        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_distinct_paths = AsyncMock(
            return_value=["/Infrastructure", "/Infrastructure/Network", "/Policies"]
        )

        with patch(
                "src.routers.documents.DocumentRepository", return_value=mock_doc_repo
            ):
            response = await authenticated_client.get(
                f"/api/organizations/{org_id}/documents/folders")

        assert response.status_code == 200
        data = response.json()
        assert "folders" in data
        assert len(data["folders"]) == 3
        assert "/Infrastructure" in data["folders"]
        assert "/Policies" in data["folders"]

    async def test_get_document_success(
        self, authenticated_client: AsyncClient
    ):
        """Test getting a single document by ID."""
        org_id = uuid4()
        doc_id = uuid4()

        mock_doc = AsyncMock()
        mock_doc.id = doc_id
        mock_doc.organization_id = org_id
        mock_doc.path = "/Infrastructure"
        mock_doc.name = "Overview"
        mock_doc.content = "# Overview\n\nThis is the overview."
        mock_doc.created_at = "2026-01-12T00:00:00Z"
        mock_doc.updated_at = "2026-01-12T00:00:00Z"

        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id_and_org = AsyncMock(return_value=mock_doc)

        with patch(
                "src.routers.documents.DocumentRepository", return_value=mock_doc_repo
            ):
            response = await authenticated_client.get(
                f"/api/organizations/{org_id}/documents/{doc_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Overview"
        assert data["content"] == "# Overview\n\nThis is the overview."

    async def test_get_document_not_found(
        self, authenticated_client: AsyncClient
    ):
        """Test getting a non-existent document returns 404."""
        org_id = uuid4()
        doc_id = uuid4()

        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id_and_org = AsyncMock(return_value=None)

        with patch(
                "src.routers.documents.DocumentRepository", return_value=mock_doc_repo
            ):
            response = await authenticated_client.get(
                f"/api/organizations/{org_id}/documents/{doc_id}")

        assert response.status_code == 404

    async def test_update_document_success(
        self, authenticated_client: AsyncClient
    ):
        """Test updating a document."""
        org_id = uuid4()
        doc_id = uuid4()

        mock_doc = AsyncMock()
        mock_doc.id = doc_id
        mock_doc.organization_id = org_id
        mock_doc.path = "/Infrastructure"
        mock_doc.name = "Overview"
        mock_doc.content = "# Overview"
        mock_doc.created_at = "2026-01-12T00:00:00Z"
        mock_doc.updated_at = "2026-01-12T00:00:00Z"

        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id_and_org = AsyncMock(return_value=mock_doc)
        mock_doc_repo.update = AsyncMock(return_value=mock_doc)

        with patch(
                "src.routers.documents.DocumentRepository", return_value=mock_doc_repo
            ):
            response = await authenticated_client.put(
                f"/api/organizations/{org_id}/documents/{doc_id}",
                json={"name": "Updated Overview", "content": "# Updated Content"})

        assert response.status_code == 200

    async def test_move_document_by_updating_path(
        self, authenticated_client: AsyncClient
    ):
        """Test moving a document by updating its path."""
        org_id = uuid4()
        doc_id = uuid4()

        mock_doc = AsyncMock()
        mock_doc.id = doc_id
        mock_doc.organization_id = org_id
        mock_doc.path = "/OldPath"
        mock_doc.name = "Document"
        mock_doc.content = "# Content"
        mock_doc.created_at = "2026-01-12T00:00:00Z"
        mock_doc.updated_at = "2026-01-12T00:00:00Z"

        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_by_id_and_org = AsyncMock(return_value=mock_doc)

        # Simulate the path being updated
        async def update_doc(doc):
            doc.path = "/NewPath"
            return doc

        mock_doc_repo.update = AsyncMock(side_effect=update_doc)

        with patch(
                "src.routers.documents.DocumentRepository", return_value=mock_doc_repo
            ):
            response = await authenticated_client.put(
                f"/api/organizations/{org_id}/documents/{doc_id}",
                json={"path": "/NewPath"})

        assert response.status_code == 200
        data = response.json()
        assert data["path"] == "/NewPath"

    async def test_delete_document_success(
        self, authenticated_client: AsyncClient
    ):
        """Test deleting a document."""
        org_id = uuid4()
        doc_id = uuid4()

        mock_doc_repo = AsyncMock()
        mock_doc_repo.delete_by_id_and_org = AsyncMock(return_value=True)

        with patch(
                "src.routers.documents.DocumentRepository", return_value=mock_doc_repo
            ):
            response = await authenticated_client.delete(
                f"/api/organizations/{org_id}/documents/{doc_id}")

        assert response.status_code == 204

    async def test_delete_document_not_found(
        self, authenticated_client: AsyncClient
    ):
        """Test deleting a non-existent document returns 404."""
        org_id = uuid4()
        doc_id = uuid4()

        mock_doc_repo = AsyncMock()
        mock_doc_repo.delete_by_id_and_org = AsyncMock(return_value=False)

        with patch(
                "src.routers.documents.DocumentRepository", return_value=mock_doc_repo
            ):
            response = await authenticated_client.delete(
                f"/api/organizations/{org_id}/documents/{doc_id}")

        assert response.status_code == 404


@pytest.mark.integration
class TestDocumentsOrganizationAccess:
    """Tests for organization access after removing membership checks."""

    async def test_user_can_access_any_org_documents(
        self, authenticated_client: AsyncClient
    ):
        """Test that users can access documents from any organization (no membership check)."""
        other_org_id = uuid4()  # Different from user's org

        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_all_by_org = AsyncMock(return_value=[])

        with patch(
                "src.routers.documents.DocumentRepository", return_value=mock_doc_repo
            ):
            response = await authenticated_client.get(
                f"/api/organizations/{other_org_id}/documents")

        # Users can now access any organization
        assert response.status_code == 200

    async def test_superuser_can_access_any_org_documents(
        self, superuser_client: AsyncClient
    ):
        """Test that superusers can access documents from any organization."""
        any_org_id = uuid4()

        mock_doc_repo = AsyncMock()
        mock_doc_repo.get_all_by_org = AsyncMock(return_value=[])

        with patch(
                "src.routers.documents.DocumentRepository", return_value=mock_doc_repo
            ):
            response = await superuser_client.get(
                f"/api/organizations/{any_org_id}/documents")

        # Superuser can access
        assert response.status_code == 200
