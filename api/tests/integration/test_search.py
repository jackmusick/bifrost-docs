"""
Integration tests for the search functionality.

Note: These tests require a running database with pgvector extension
and optionally an OpenAI API key for full embedding tests.
Tests use mocks for OpenAI calls to avoid API costs during CI.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.models.contracts.search import SearchResponse, SearchResult
from src.services.embeddings import EmbeddingsService


class TestSearchResponse:
    """Tests for SearchResponse model."""

    def test_search_response_creation(self) -> None:
        """Test that SearchResponse can be created with valid data."""
        results = [
            SearchResult(
                entity_type="password",
                entity_id=str(uuid4()),
                organization_id=str(uuid4()),
                organization_name="Test Org",
                name="Test Password",
                snippet="This is a test password entry...",
                score=0.85,
            )
        ]

        response = SearchResponse(query="test", results=results)

        assert response.query == "test"
        assert len(response.results) == 1
        assert response.results[0].entity_type == "password"
        assert response.results[0].score == 0.85

    def test_search_result_score_bounds(self) -> None:
        """Test that SearchResult score must be between 0 and 1."""
        # Valid scores
        SearchResult(
            entity_type="document",
            entity_id=str(uuid4()),
            organization_id=str(uuid4()),
            organization_name="Test Org",
            name="Test Doc",
            snippet="Test",
            score=0.0,
        )

        SearchResult(
            entity_type="document",
            entity_id=str(uuid4()),
            organization_id=str(uuid4()),
            organization_name="Test Org",
            name="Test Doc",
            snippet="Test",
            score=1.0,
        )

        # Invalid scores should raise validation error
        with pytest.raises(ValidationError):
            SearchResult(
                entity_type="document",
                entity_id=str(uuid4()),
                organization_id=str(uuid4()),
                organization_name="Test Org",
                name="Test Doc",
                snippet="Test",
                score=-0.1,
            )

        with pytest.raises(ValidationError):
            SearchResult(
                entity_type="document",
                entity_id=str(uuid4()),
                organization_id=str(uuid4()),
                organization_name="Test Org",
                name="Test Doc",
                snippet="Test",
                score=1.1,
            )


class TestSearchResultEntityTypes:
    """Tests for SearchResult entity type validation."""

    @pytest.mark.parametrize(
        "entity_type",
        ["password", "configuration", "location", "document", "custom_asset"],
    )
    def test_valid_entity_types(self, entity_type: str) -> None:
        """Test that all valid entity types are accepted."""
        result = SearchResult(
            entity_type=entity_type,  # type: ignore[arg-type]
            entity_id=str(uuid4()),
            organization_id=str(uuid4()),
            organization_name="Test Org",
            name="Test Entity",
            snippet="Test snippet",
            score=0.5,
        )
        assert result.entity_type == entity_type

    def test_invalid_entity_type_raises(self) -> None:
        """Test that invalid entity types are rejected."""
        with pytest.raises(ValidationError):
            SearchResult(
                entity_type="invalid_type",  # type: ignore[arg-type]
                entity_id=str(uuid4()),
                organization_id=str(uuid4()),
                organization_name="Test Org",
                name="Test Entity",
                snippet="Test snippet",
                score=0.5,
            )


class TestEmbeddingsServiceIndexing:
    """Tests for the embeddings service indexing functions."""

    @pytest.mark.asyncio
    async def test_index_entity_generates_hash(self) -> None:
        """Test that indexing generates a content hash."""
        mock_db = AsyncMock()
        service = EmbeddingsService(mock_db)

        # Test hash generation
        text = "Test content for indexing"
        content_hash = service.compute_content_hash(text)

        assert len(content_hash) == 32
        assert all(c in "0123456789abcdef" for c in content_hash)

    @pytest.mark.asyncio
    async def test_index_entity_skip_unchanged(self) -> None:
        """Test that unchanged content is detected by hash comparison."""
        mock_db = AsyncMock()
        service = EmbeddingsService(mock_db)

        text1 = "Original content"
        text2 = "Original content"  # Same content
        text3 = "Modified content"  # Different content

        hash1 = service.compute_content_hash(text1)
        hash2 = service.compute_content_hash(text2)
        hash3 = service.compute_content_hash(text3)

        # Same content should produce same hash
        assert hash1 == hash2

        # Different content should produce different hash
        assert hash1 != hash3


class TestSearchIndexingHelper:
    """Tests for the search indexing helper functions."""

    @pytest.mark.asyncio
    async def test_remove_entity_from_search_handles_errors(self) -> None:
        """Test that removal silently handles errors."""
        from src.services.search_indexing import remove_entity_from_search

        with patch(
            "src.services.indexing_queue.enqueue_remove_entity"
        ) as mock_enqueue:
            # Mock enqueue to raise an error
            mock_enqueue.side_effect = Exception("Redis Error")

            # Should not raise, just return silently
            await remove_entity_from_search(
                db=AsyncMock(),
                entity_type="password",
                entity_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_index_entity_skips_when_indexing_disabled(self) -> None:
        """Test that indexing skips when indexing_enabled is False."""
        from src.services.search_indexing import index_entity_for_search

        with patch(
            "src.services.search_indexing.is_indexing_enabled"
        ) as mock_is_indexing_enabled:
            # Mock is_indexing_enabled to return False
            mock_is_indexing_enabled.return_value = False

            with patch(
                "src.services.indexing_queue.enqueue_index_entity"
            ) as mock_enqueue:
                # Should not call enqueue when indexing disabled
                await index_entity_for_search(
                    db=AsyncMock(),
                    entity_type="password",
                    entity_id=uuid4(),
                    org_id=uuid4(),
                )

                # Assert enqueue was never called
                mock_enqueue.assert_not_called()

    @pytest.mark.asyncio
    async def test_index_entity_proceeds_when_indexing_enabled(self) -> None:
        """Test that indexing proceeds when indexing_enabled is True."""
        from src.services.search_indexing import index_entity_for_search

        with patch(
            "src.services.search_indexing.is_indexing_enabled"
        ) as mock_is_indexing_enabled:
            # Mock is_indexing_enabled to return True
            mock_is_indexing_enabled.return_value = True

            with patch(
                "src.services.indexing_queue.enqueue_index_entity"
            ) as mock_enqueue:
                await index_entity_for_search(
                    db=AsyncMock(),
                    entity_type="password",
                    entity_id=uuid4(),
                    org_id=uuid4(),
                )

                # Assert enqueue was called
                mock_enqueue.assert_called_once()


class TestSearchEndpointContracts:
    """Tests for search endpoint contract validation."""

    def test_search_response_empty_results(self) -> None:
        """Test SearchResponse with empty results."""
        response = SearchResponse(query="nonexistent", results=[])

        assert response.query == "nonexistent"
        assert response.results == []

    def test_search_response_multiple_results(self) -> None:
        """Test SearchResponse with multiple results from different entity types."""
        results = [
            SearchResult(
                entity_type="password",
                entity_id=str(uuid4()),
                organization_id=str(uuid4()),
                organization_name="Org A",
                name="Admin Password",
                snippet="Administrator credentials for...",
                score=0.95,
            ),
            SearchResult(
                entity_type="configuration",
                entity_id=str(uuid4()),
                organization_id=str(uuid4()),
                organization_name="Org A",
                name="webserver-01",
                snippet="Primary web server configuration...",
                score=0.82,
            ),
            SearchResult(
                entity_type="document",
                entity_id=str(uuid4()),
                organization_id=str(uuid4()),
                organization_name="Org B",
                name="Network Diagram",
                snippet="Network topology documentation...",
                score=0.78,
            ),
        ]

        response = SearchResponse(query="admin server", results=results)

        assert len(response.results) == 3
        assert response.results[0].entity_type == "password"
        assert response.results[1].entity_type == "configuration"
        assert response.results[2].entity_type == "document"
        # Results should maintain order (by relevance)
        assert response.results[0].score > response.results[1].score
        assert response.results[1].score > response.results[2].score
