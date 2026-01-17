"""Integration tests for full mutation flow."""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.auth import UserPrincipal, get_current_active_user
from src.main import app
from src.models.enums import UserRole
from src.models.orm.custom_asset import CustomAsset
from src.models.orm.document import Document
from src.models.orm.organization import Organization
from src.services.llm.base import LLMStreamChunk, ToolCall


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


@pytest.mark.integration
class TestFullDocumentMutationFlow:
    """Test complete flow: chat with mutation intent → preview → apply."""

    @pytest.mark.asyncio
    async def test_full_document_mutation_flow(
        self, client: AsyncClient, contributor_user
    ):
        """Test complete flow: chat with mutation intent → preview → apply → verify changes."""

        # Setup test data
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
        mock_document.name = "Test Document"
        mock_document.path = "/test"
        mock_document.content = "# Original Content\n\nThis is messy."
        mock_document.organization_id = org_id
        mock_document.updated_by_user_id = contributor_user.user_id
        mock_document.is_enabled = True

        # Mock database session
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Override auth
        app.dependency_overrides[get_current_active_user] = lambda: contributor_user

        # Mock database dependency
        from src.core.database import get_db
        async def mock_get_db():
            yield mock_db
        app.dependency_overrides[get_db] = mock_get_db

        try:
            # =========================================================================
            # Step 1: Send chat message with mutation intent
            # =========================================================================

            # Mock LLM to return tool call for mutation
            async def mock_stream(*args, **kwargs):
                """Mock LLM stream response with tool call."""
                # First yield a tool call for modify_entity
                yield LLMStreamChunk(
                    type="tool_call",
                    tool_call=ToolCall(
                        id="call_123",
                        name="modify_entity",
                        arguments={
                            "entity_type": "document",
                            "entity_id": str(doc_id),
                            "organization_id": str(org_id),
                            "intent": "cleanup",
                            "changes_summary": "Fixed formatting and structure",
                            "content": "# Clean Document\n\nNice formatting."
                        }
                    )
                )
                # Then signal completion
                yield LLMStreamChunk(type="done")

            with patch("src.routers.search.get_completions_config") as mock_config:
                with patch("src.services.ai_chat.get_llm_client") as mock_get_client:
                    with patch("src.routers.search.get_embeddings_service") as mock_embeddings_svc:
                        # Setup LLM client mock
                        mock_config.return_value = MagicMock()
                        mock_client = MagicMock()
                        mock_client.stream = mock_stream
                        mock_get_client.return_value = mock_client

                        # Setup embeddings service mock (for search context)
                        mock_embeddings = MagicMock()
                        mock_embeddings.search = AsyncMock(return_value=[])
                        mock_embeddings_svc.return_value = mock_embeddings

                        # Mock organization repository
                        with patch("src.routers.search.OrganizationRepository") as mock_org_repo_cls:
                            mock_org_repo = mock_org_repo_cls.return_value
                            mock_org_repo.get_by_id = AsyncMock(return_value=mock_org)
                            mock_org_repo.get_all = AsyncMock(return_value=[mock_org])

                            # Send chat request
                            chat_response = await client.post(
                                "/api/search/chat",
                                json={
                                    "message": "Can you clean up this document?",
                                    "conversation_id": None,
                                    "history": [],
                                    "org_id": str(org_id)
                                }
                            )

                            assert chat_response.status_code == 200
                            chat_data = chat_response.json()
                            assert "request_id" in chat_data
                            assert "conversation_id" in chat_data
                            request_id = chat_data["request_id"]
                            conversation_id = chat_data["conversation_id"]

            # =========================================================================
            # Step 2: Apply the mutation
            # =========================================================================

            with patch("src.routers.search.OrganizationRepository") as mock_org_repo_cls:
                with patch("src.routers.search.DocumentRepository") as mock_doc_repo_cls:
                    # Setup repository mocks
                    mock_org_repo = mock_org_repo_cls.return_value
                    mock_org_repo.get_by_id = AsyncMock(return_value=mock_org)

                    mock_doc_repo = mock_doc_repo_cls.return_value
                    mock_doc_repo.get_by_id = AsyncMock(return_value=mock_document)

                    # Apply mutation
                    apply_response = await client.post(
                        "/api/search/chat/apply",
                        json={
                            "conversation_id": conversation_id,
                            "request_id": request_id,
                            "entity_type": "document",
                            "entity_id": str(doc_id),
                            "organization_id": str(org_id),
                            "mutation": {
                                "content": "# Clean Document\n\nNice formatting.",
                                "summary": "Fixed formatting and structure"
                            }
                        }
                    )

                    assert apply_response.status_code == 200
                    apply_data = apply_response.json()
                    assert apply_data["success"] is True
                    assert apply_data["entity_id"] == str(doc_id)
                    assert f"documents/{org_id}/{doc_id}" in apply_data["link"]

                    # =========================================================================
                    # Step 3: Verify document was updated in database
                    # =========================================================================

                    # Verify document content was updated
                    assert mock_document.content == "# Clean Document\n\nNice formatting."
                    assert mock_document.updated_by_user_id == contributor_user.user_id

                    # Verify database operations were called
                    mock_db.commit.assert_called_once()
                    mock_db.refresh.assert_called_once_with(mock_document)

        finally:
            # Clean up dependency overrides
            app.dependency_overrides.pop(get_current_active_user, None)
            app.dependency_overrides.pop(get_db, None)

    @pytest.mark.asyncio
    async def test_mutation_flow_with_conversational_context(
        self, client: AsyncClient, contributor_user
    ):
        """Test mutation flow with conversation history."""

        # Setup test data
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
        mock_document.name = "API Documentation"
        mock_document.path = "/docs"
        mock_document.content = "# API\n\nEndpoints here"
        mock_document.organization_id = org_id
        mock_document.updated_by_user_id = contributor_user.user_id
        mock_document.is_enabled = True

        # Mock database session
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Override dependencies
        app.dependency_overrides[get_current_active_user] = lambda: contributor_user

        from src.core.database import get_db
        async def mock_get_db():
            yield mock_db
        app.dependency_overrides[get_db] = mock_get_db

        try:
            # Mock LLM with conversational context
            async def mock_stream(*args, **kwargs):
                """Mock LLM stream with contextual tool call."""
                yield LLMStreamChunk(
                    type="tool_call",
                    tool_call=ToolCall(
                        id="call_456",
                        name="modify_entity",
                        arguments={
                            "entity_type": "document",
                            "entity_id": str(doc_id),
                            "organization_id": str(org_id),
                            "intent": "enhancement",
                            "changes_summary": "Added authentication section as requested",
                            "content": "# API\n\n## Authentication\n\nUse Bearer tokens.\n\n## Endpoints\n\nEndpoints here"
                        }
                    )
                )
                yield LLMStreamChunk(type="done")

            with patch("src.routers.search.get_completions_config") as mock_config:
                with patch("src.services.ai_chat.get_llm_client") as mock_get_client:
                    with patch("src.routers.search.get_embeddings_service") as mock_embeddings_svc:
                        mock_config.return_value = MagicMock()
                        mock_client = MagicMock()
                        mock_client.stream = mock_stream
                        mock_get_client.return_value = mock_client

                        mock_embeddings = MagicMock()
                        mock_embeddings.search = AsyncMock(return_value=[])
                        mock_embeddings_svc.return_value = mock_embeddings

                        with patch("src.routers.search.OrganizationRepository") as mock_org_repo_cls:
                            mock_org_repo = mock_org_repo_cls.return_value
                            mock_org_repo.get_by_id = AsyncMock(return_value=mock_org)
                            mock_org_repo.get_all = AsyncMock(return_value=[mock_org])

                            # Send chat with history
                            chat_response = await client.post(
                                "/api/search/chat",
                                json={
                                    "message": "Add an authentication section",
                                    "conversation_id": str(uuid4()),
                                    "history": [
                                        {"role": "user", "content": "Show me the API docs"},
                                        {"role": "assistant", "content": "Here's the API documentation..."}
                                    ],
                                    "org_id": str(org_id)
                                }
                            )

                            assert chat_response.status_code == 200
                            chat_data = chat_response.json()
                            request_id = chat_data["request_id"]
                            conversation_id = chat_data["conversation_id"]

            # Apply the mutation
            with patch("src.routers.search.OrganizationRepository") as mock_org_repo_cls:
                with patch("src.routers.search.DocumentRepository") as mock_doc_repo_cls:
                    mock_org_repo = mock_org_repo_cls.return_value
                    mock_org_repo.get_by_id = AsyncMock(return_value=mock_org)

                    mock_doc_repo = mock_doc_repo_cls.return_value
                    mock_doc_repo.get_by_id = AsyncMock(return_value=mock_document)

                    apply_response = await client.post(
                        "/api/search/chat/apply",
                        json={
                            "conversation_id": conversation_id,
                            "request_id": request_id,
                            "entity_type": "document",
                            "entity_id": str(doc_id),
                            "organization_id": str(org_id),
                            "mutation": {
                                "content": "# API\n\n## Authentication\n\nUse Bearer tokens.\n\n## Endpoints\n\nEndpoints here",
                                "summary": "Added authentication section as requested"
                            }
                        }
                    )

                    assert apply_response.status_code == 200
                    apply_data = apply_response.json()
                    assert apply_data["success"] is True

                    # Verify the enhanced content
                    assert "Authentication" in mock_document.content
                    assert "Bearer tokens" in mock_document.content

        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
            app.dependency_overrides.pop(get_db, None)


@pytest.mark.integration
class TestFullAssetMutationFlow:
    """Test complete flow for custom asset mutations."""

    @pytest.mark.asyncio
    async def test_full_asset_mutation_flow(
        self, client: AsyncClient, contributor_user
    ):
        """Test complete flow: chat with asset mutation intent → apply → verify changes."""

        # Setup test data
        org_id = uuid4()
        asset_id = uuid4()
        asset_type_id = uuid4()

        # Mock organization
        mock_org = MagicMock(spec=Organization)
        mock_org.id = org_id
        mock_org.name = "Test Org"
        mock_org.is_enabled = True

        # Mock custom asset
        mock_asset = MagicMock(spec=CustomAsset)
        mock_asset.id = asset_id
        mock_asset.custom_asset_type_id = asset_type_id
        mock_asset.organization_id = org_id
        mock_asset.values = {
            "ip_address": "10.0.0.1",
            "location": "DC1",
            "status": "active"
        }
        mock_asset.updated_by_user_id = contributor_user.user_id
        mock_asset.is_enabled = True

        # Mock database session
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Override dependencies
        app.dependency_overrides[get_current_active_user] = lambda: contributor_user

        from src.core.database import get_db
        async def mock_get_db():
            yield mock_db
        app.dependency_overrides[get_db] = mock_get_db

        try:
            # =========================================================================
            # Step 1: Send chat message for asset update
            # =========================================================================

            async def mock_stream(*args, **kwargs):
                """Mock LLM stream response with asset mutation tool call."""
                yield LLMStreamChunk(
                    type="tool_call",
                    tool_call=ToolCall(
                        id="call_789",
                        name="modify_entity",
                        arguments={
                            "entity_type": "custom_asset",
                            "entity_id": str(asset_id),
                            "organization_id": str(org_id),
                            "intent": "update",
                            "changes_summary": "Updated IP address and moved to DC2",
                            "field_updates": {
                                "ip_address": "10.0.0.5",
                                "location": "DC2"
                            }
                        }
                    )
                )
                yield LLMStreamChunk(type="done")

            with patch("src.routers.search.get_completions_config") as mock_config:
                with patch("src.services.ai_chat.get_llm_client") as mock_get_client:
                    with patch("src.routers.search.get_embeddings_service") as mock_embeddings_svc:
                        mock_config.return_value = MagicMock()
                        mock_client = MagicMock()
                        mock_client.stream = mock_stream
                        mock_get_client.return_value = mock_client

                        mock_embeddings = MagicMock()
                        mock_embeddings.search = AsyncMock(return_value=[])
                        mock_embeddings_svc.return_value = mock_embeddings

                        with patch("src.routers.search.OrganizationRepository") as mock_org_repo_cls:
                            mock_org_repo = mock_org_repo_cls.return_value
                            mock_org_repo.get_by_id = AsyncMock(return_value=mock_org)
                            mock_org_repo.get_all = AsyncMock(return_value=[mock_org])

                            chat_response = await client.post(
                                "/api/search/chat",
                                json={
                                    "message": "Update the server IP to 10.0.0.5 and move it to DC2",
                                    "conversation_id": None,
                                    "history": [],
                                    "org_id": str(org_id)
                                }
                            )

                            assert chat_response.status_code == 200
                            chat_data = chat_response.json()
                            request_id = chat_data["request_id"]
                            conversation_id = chat_data["conversation_id"]

            # =========================================================================
            # Step 2: Apply the asset mutation
            # =========================================================================

            with patch("src.routers.search.OrganizationRepository") as mock_org_repo_cls:
                with patch("src.routers.search.CustomAssetRepository") as mock_asset_repo_cls:
                    mock_org_repo = mock_org_repo_cls.return_value
                    mock_org_repo.get_by_id = AsyncMock(return_value=mock_org)

                    mock_asset_repo = mock_asset_repo_cls.return_value
                    mock_asset_repo.get_by_id = AsyncMock(return_value=mock_asset)

                    apply_response = await client.post(
                        "/api/search/chat/apply",
                        json={
                            "conversation_id": conversation_id,
                            "request_id": request_id,
                            "entity_type": "custom_asset",
                            "entity_id": str(asset_id),
                            "organization_id": str(org_id),
                            "mutation": {
                                "field_updates": {
                                    "ip_address": "10.0.0.5",
                                    "location": "DC2"
                                },
                                "summary": "Updated IP address and moved to DC2"
                            }
                        }
                    )

                    assert apply_response.status_code == 200
                    apply_data = apply_response.json()
                    assert apply_data["success"] is True
                    assert apply_data["entity_id"] == str(asset_id)

                    # =========================================================================
                    # Step 3: Verify asset was updated in database
                    # =========================================================================

                    # Verify field updates were applied
                    assert mock_asset.values["ip_address"] == "10.0.0.5"
                    assert mock_asset.values["location"] == "DC2"
                    assert mock_asset.values["status"] == "active"  # Unchanged field preserved
                    assert mock_asset.updated_by_user_id == contributor_user.user_id

                    # Verify database operations
                    mock_db.commit.assert_called_once()
                    mock_db.refresh.assert_called_once_with(mock_asset)

        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
            app.dependency_overrides.pop(get_db, None)


@pytest.mark.integration
class TestMutationFlowErrorHandling:
    """Test error handling in mutation flow."""

    @pytest.mark.asyncio
    async def test_apply_mutation_for_nonexistent_document(
        self, client: AsyncClient, contributor_user
    ):
        """Test applying mutation to non-existent document returns 404."""
        org_id = uuid4()
        doc_id = uuid4()

        mock_org = MagicMock(spec=Organization)
        mock_org.id = org_id
        mock_org.name = "Test Org"
        mock_org.is_enabled = True

        app.dependency_overrides[get_current_active_user] = lambda: contributor_user

        try:
            with patch("src.routers.search.OrganizationRepository") as mock_org_repo_cls:
                with patch("src.routers.search.DocumentRepository") as mock_doc_repo_cls:
                    mock_org_repo = mock_org_repo_cls.return_value
                    mock_org_repo.get_by_id = AsyncMock(return_value=mock_org)

                    mock_doc_repo = mock_doc_repo_cls.return_value
                    mock_doc_repo.get_by_id = AsyncMock(return_value=None)

                    response = await client.post(
                        "/api/search/chat/apply",
                        json={
                            "conversation_id": str(uuid4()),
                            "request_id": str(uuid4()),
                            "entity_type": "document",
                            "entity_id": str(doc_id),
                            "organization_id": str(org_id),
                            "mutation": {
                                "content": "# Test",
                                "summary": "Test update"
                            }
                        }
                    )

                    assert response.status_code == 404

        finally:
            app.dependency_overrides.pop(get_current_active_user, None)

    @pytest.mark.asyncio
    async def test_apply_mutation_wrong_organization(
        self, client: AsyncClient, contributor_user
    ):
        """Test applying mutation to document from different org returns 404."""
        org_id = uuid4()
        wrong_org_id = uuid4()
        doc_id = uuid4()

        mock_org = MagicMock(spec=Organization)
        mock_org.id = org_id
        mock_org.name = "Test Org"
        mock_org.is_enabled = True

        # Document belongs to different org
        mock_document = MagicMock(spec=Document)
        mock_document.id = doc_id
        mock_document.organization_id = wrong_org_id
        mock_document.is_enabled = True

        app.dependency_overrides[get_current_active_user] = lambda: contributor_user

        try:
            with patch("src.routers.search.OrganizationRepository") as mock_org_repo_cls:
                with patch("src.routers.search.DocumentRepository") as mock_doc_repo_cls:
                    mock_org_repo = mock_org_repo_cls.return_value
                    mock_org_repo.get_by_id = AsyncMock(return_value=mock_org)

                    mock_doc_repo = mock_doc_repo_cls.return_value
                    mock_doc_repo.get_by_id = AsyncMock(return_value=mock_document)

                    response = await client.post(
                        "/api/search/chat/apply",
                        json={
                            "conversation_id": str(uuid4()),
                            "request_id": str(uuid4()),
                            "entity_type": "document",
                            "entity_id": str(doc_id),
                            "organization_id": str(org_id),
                            "mutation": {
                                "content": "# Test",
                                "summary": "Test update"
                            }
                        }
                    )

                    assert response.status_code == 404

        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
