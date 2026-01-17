"""
Integration tests for relationships endpoints.

Tests the complete relationship management flow including:
- Creating relationships between entities
- Querying relationships bidirectionally
- Preventing duplicate relationships
- Resolved endpoint returning entity names
- Deleting relationships
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
from src.models.orm.relationship import Relationship


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
class TestRelationshipsEndpointsUnauthenticated:
    """Tests for relationships endpoints without authentication."""

    async def test_list_relationships_unauthenticated(self, client: AsyncClient, test_org_id):
        """Test that listing relationships requires authentication."""
        entity_id = uuid4()
        response = await client.get(
            f"/api/organizations/{test_org_id}/relationships",
            params={"entity_type": "password", "entity_id": str(entity_id)})
        assert response.status_code == 401

    async def test_create_relationship_unauthenticated(self, client: AsyncClient, test_org_id):
        """Test that creating relationships requires authentication."""
        response = await client.post(
            f"/api/organizations/{test_org_id}/relationships",
            json={
                "source_type": "password",
                "source_id": str(uuid4()),
                "target_type": "configuration",
                "target_id": str(uuid4()),
            })
        assert response.status_code == 401

    async def test_delete_relationship_unauthenticated(self, client: AsyncClient, test_org_id):
        """Test that deleting relationships requires authentication."""
        relationship_id = uuid4()
        response = await client.delete(
            f"/api/organizations/{test_org_id}/relationships/{relationship_id}"
        )
        assert response.status_code == 401

    async def test_resolved_relationships_unauthenticated(self, client: AsyncClient, test_org_id):
        """Test that resolved endpoint requires authentication."""
        entity_id = uuid4()
        response = await client.get(
            f"/api/organizations/{test_org_id}/relationships/resolved",
            params={"entity_type": "password", "entity_id": str(entity_id)})
        assert response.status_code == 401


@pytest.mark.integration
class TestRelationshipsCreate:
    """Tests for relationship creation."""

    async def test_create_relationship_success(self, test_user, test_org_id):
        """Test successful relationship creation."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        password_id = uuid4()
        config_id = uuid4()

        mock_rel_repo = AsyncMock()
        mock_rel_repo.find_existing = AsyncMock(return_value=None)
        created_rel = MagicMock(spec=Relationship)
        created_rel.id = uuid4()
        created_rel.organization_id = test_org_id
        created_rel.source_type = "configuration"  # Normalized alphabetically
        created_rel.source_id = config_id
        created_rel.target_type = "password"
        created_rel.target_id = password_id
        created_rel.created_at = MagicMock()
        mock_rel_repo.create_relationship = AsyncMock(return_value=created_rel)

        mock_resolver = AsyncMock()
        mock_resolver.get_entity_name = AsyncMock(return_value="Test Entity")

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch("src.routers.relationships.RelationshipRepository", return_value=mock_rel_repo), \
                     patch("src.routers.relationships.EntityResolver", return_value=mock_resolver):
                    response = await client.post(
                        f"/api/organizations/{test_org_id}/relationships",
                        json={
                            "source_type": "password",
                            "source_id": str(password_id),
                            "target_type": "configuration",
                            "target_id": str(config_id),
                        })

            assert response.status_code == 201
            data = response.json()
            assert "id" in data
            assert data["organization_id"] == str(test_org_id)
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_create_relationship_duplicate_rejected(self, test_user, test_org_id):
        """Test that duplicate relationships are rejected."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        password_id = uuid4()
        config_id = uuid4()

        # Simulate existing relationship
        existing_rel = MagicMock(spec=Relationship)
        existing_rel.id = uuid4()

        mock_rel_repo = AsyncMock()
        mock_rel_repo.find_existing = AsyncMock(return_value=existing_rel)

        mock_resolver = AsyncMock()
        mock_resolver.get_entity_name = AsyncMock(return_value="Test Entity")

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch("src.routers.relationships.RelationshipRepository", return_value=mock_rel_repo), \
                     patch("src.routers.relationships.EntityResolver", return_value=mock_resolver):
                    response = await client.post(
                        f"/api/organizations/{test_org_id}/relationships",
                        json={
                            "source_type": "password",
                            "source_id": str(password_id),
                            "target_type": "configuration",
                            "target_id": str(config_id),
                        })

            assert response.status_code == 409
            assert "already exists" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_create_relationship_self_reference_rejected(self, test_user, test_org_id):
        """Test that self-referencing relationships are rejected."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        entity_id = uuid4()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                response = await client.post(
                    f"/api/organizations/{test_org_id}/relationships",
                    json={
                        "source_type": "password",
                        "source_id": str(entity_id),
                        "target_type": "password",
                        "target_id": str(entity_id),
                    })

            assert response.status_code == 400
            assert "itself" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_create_relationship_invalid_entity_type(self, test_user, test_org_id):
        """Test that invalid entity types are rejected."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                response = await client.post(
                    f"/api/organizations/{test_org_id}/relationships",
                    json={
                        "source_type": "invalid_type",
                        "source_id": str(uuid4()),
                        "target_type": "password",
                        "target_id": str(uuid4()),
                    })

            assert response.status_code == 400
            assert "Invalid entity type" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_create_relationship_source_not_found(self, test_user, test_org_id):
        """Test that non-existent source entities are rejected."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        mock_resolver = AsyncMock()
        # Source not found, target found
        mock_resolver.get_entity_name = AsyncMock(side_effect=[None, "Target Name"])

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch("src.routers.relationships.EntityResolver", return_value=mock_resolver):
                    response = await client.post(
                        f"/api/organizations/{test_org_id}/relationships",
                        json={
                            "source_type": "password",
                            "source_id": str(uuid4()),
                            "target_type": "configuration",
                            "target_id": str(uuid4()),
                        })

            assert response.status_code == 404
            assert "Source entity not found" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.integration
class TestRelationshipsBidirectional:
    """Tests for bidirectional relationship queries."""

    async def test_query_from_source_side(self, test_user, test_org_id):
        """Test querying relationships from the source entity."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        password_id = uuid4()
        config_id = uuid4()

        # Create mock relationship where password is source
        mock_rel = MagicMock(spec=Relationship)
        mock_rel.id = uuid4()
        mock_rel.organization_id = test_org_id
        mock_rel.source_type = "configuration"
        mock_rel.source_id = config_id
        mock_rel.target_type = "password"
        mock_rel.target_id = password_id
        mock_rel.created_at = MagicMock()

        mock_rel_repo = AsyncMock()
        mock_rel_repo.get_for_entity = AsyncMock(return_value=[mock_rel])

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch("src.routers.relationships.RelationshipRepository", return_value=mock_rel_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/relationships",
                        params={"entity_type": "password", "entity_id": str(password_id)})

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["target_id"] == str(password_id)
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_query_from_target_side(self, test_user, test_org_id):
        """Test querying relationships from the target entity."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        password_id = uuid4()
        config_id = uuid4()

        # Create mock relationship where configuration is source
        mock_rel = MagicMock(spec=Relationship)
        mock_rel.id = uuid4()
        mock_rel.organization_id = test_org_id
        mock_rel.source_type = "configuration"
        mock_rel.source_id = config_id
        mock_rel.target_type = "password"
        mock_rel.target_id = password_id
        mock_rel.created_at = MagicMock()

        mock_rel_repo = AsyncMock()
        mock_rel_repo.get_for_entity = AsyncMock(return_value=[mock_rel])

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch("src.routers.relationships.RelationshipRepository", return_value=mock_rel_repo):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/relationships",
                        params={"entity_type": "configuration", "entity_id": str(config_id)})

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["source_id"] == str(config_id)
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.integration
class TestRelationshipsResolved:
    """Tests for resolved relationships endpoint."""

    async def test_resolved_returns_entity_names(self, test_user, test_org_id):
        """Test that resolved endpoint returns entity names."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        password_id = uuid4()
        config_id = uuid4()

        # Create mock relationship
        mock_rel = MagicMock(spec=Relationship)
        mock_rel.id = uuid4()
        mock_rel.organization_id = test_org_id
        mock_rel.source_type = "configuration"
        mock_rel.source_id = config_id
        mock_rel.target_type = "password"
        mock_rel.target_id = password_id
        mock_rel.created_at = MagicMock()

        mock_rel_repo = AsyncMock()
        mock_rel_repo.get_for_entity = AsyncMock(return_value=[mock_rel])

        mock_resolver = AsyncMock()
        mock_resolver.get_entity_name = AsyncMock(return_value="Web Server 01")

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch("src.routers.relationships.RelationshipRepository", return_value=mock_rel_repo), \
                     patch("src.routers.relationships.EntityResolver", return_value=mock_resolver):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/relationships/resolved",
                        params={"entity_type": "password", "entity_id": str(password_id)})

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert len(data["items"]) == 1
            assert data["items"][0]["name"] == "Web Server 01"
            assert data["items"][0]["entity_type"] == "configuration"
            assert data["items"][0]["entity_id"] == str(config_id)
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_resolved_excludes_deleted_entities(self, test_user, test_org_id):
        """Test that resolved endpoint excludes entities that no longer exist."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        password_id = uuid4()
        config_id = uuid4()

        # Create mock relationship
        mock_rel = MagicMock(spec=Relationship)
        mock_rel.id = uuid4()
        mock_rel.organization_id = test_org_id
        mock_rel.source_type = "configuration"
        mock_rel.source_id = config_id
        mock_rel.target_type = "password"
        mock_rel.target_id = password_id
        mock_rel.created_at = MagicMock()

        mock_rel_repo = AsyncMock()
        mock_rel_repo.get_for_entity = AsyncMock(return_value=[mock_rel])

        mock_resolver = AsyncMock()
        # Entity no longer exists
        mock_resolver.get_entity_name = AsyncMock(return_value=None)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch("src.routers.relationships.RelationshipRepository", return_value=mock_rel_repo), \
                     patch("src.routers.relationships.EntityResolver", return_value=mock_resolver):
                    response = await client.get(
                        f"/api/organizations/{test_org_id}/relationships/resolved",
                        params={"entity_type": "password", "entity_id": str(password_id)})

            assert response.status_code == 200
            data = response.json()
            assert data["items"] == []
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.integration
class TestRelationshipsDelete:
    """Tests for relationship deletion."""

    async def test_delete_relationship_success(self, test_user, test_org_id):
        """Test successful relationship deletion."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        relationship_id = uuid4()

        mock_rel = MagicMock(spec=Relationship)
        mock_rel.id = relationship_id
        mock_rel.source_type = "password"
        mock_rel.source_id = uuid4()
        mock_rel.target_type = "configuration"
        mock_rel.target_id = uuid4()

        mock_rel_repo = AsyncMock()
        mock_rel_repo.get_by_id_and_org = AsyncMock(return_value=mock_rel)
        mock_rel_repo.delete = AsyncMock()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch("src.routers.relationships.RelationshipRepository", return_value=mock_rel_repo):
                    response = await client.delete(
                        f"/api/organizations/{test_org_id}/relationships/{relationship_id}"
                    )

            assert response.status_code == 204
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_delete_relationship_not_found(self, test_user, test_org_id):
        """Test deleting a non-existent relationship returns 404."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        relationship_id = uuid4()

        mock_rel_repo = AsyncMock()
        mock_rel_repo.get_by_id_and_org = AsyncMock(return_value=None)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                with patch("src.routers.relationships.RelationshipRepository", return_value=mock_rel_repo):
                    response = await client.delete(
                        f"/api/organizations/{test_org_id}/relationships/{relationship_id}"
                    )

            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.integration
class TestRelationshipsOrganizationIsolation:
    """Tests for organization-level relationship isolation."""

    async def test_cannot_access_other_org_relationships(self, test_user, other_org_id):
        """Test that users cannot access relationships from other organizations."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        entity_id = uuid4()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                response = await client.get(
                    f"/api/organizations/{other_org_id}/relationships",
                    params={"entity_type": "password", "entity_id": str(entity_id)})

            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_cannot_create_in_other_org(self, test_user, other_org_id):
        """Test that users cannot create relationships in other organizations."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                response = await client.post(
                    f"/api/organizations/{other_org_id}/relationships",
                    json={
                        "source_type": "password",
                        "source_id": str(uuid4()),
                        "target_type": "configuration",
                        "target_id": str(uuid4()),
                    })

            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    async def test_cannot_delete_from_other_org(self, test_user, other_org_id):
        """Test that users cannot delete relationships from other organizations."""
        app.dependency_overrides[get_current_active_user] = lambda: test_user

        relationship_id = uuid4()

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test") as client:
                response = await client.delete(
                    f"/api/organizations/{other_org_id}/relationships/{relationship_id}"
                )

            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
