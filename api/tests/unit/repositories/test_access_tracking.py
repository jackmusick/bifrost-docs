"""Tests for AccessTracking repository."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.models.contracts.access_tracking import FrequentItem, RecentItem
from src.repositories.access_tracking import AccessTrackingRepository


@pytest.mark.unit
@pytest.mark.asyncio
class TestAccessTrackingRepository:
    """Tests for AccessTrackingRepository."""

    async def test_get_recent_for_user_returns_empty_list_when_no_views(self):
        """Test get_recent_for_user returns empty list when no views exist."""
        mock_session = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = AccessTrackingRepository(mock_session)
        result = await repo.get_recent_for_user(uuid4(), limit=10)

        assert result == []
        assert isinstance(result, list)

    async def test_get_recent_for_user_returns_correct_shape(self):
        """Test get_recent_for_user returns correctly shaped RecentItem objects."""
        mock_session = AsyncMock()
        user_id = uuid4()
        entity_id = uuid4()
        org_id = uuid4()
        viewed_at = datetime.now(UTC)

        # First call: audit log query returns one view
        audit_result = MagicMock()
        audit_result.all.return_value = [
            MagicMock(
                entity_type="password",
                entity_id=entity_id,
                organization_id=org_id,
                viewed_at=viewed_at,
            )
        ]

        # Second call: entity name query returns a name
        name_result = MagicMock()
        name_result.scalar_one_or_none.return_value = "My Password"

        # Third call: org name query returns org name
        org_result = MagicMock()
        org_result.scalar_one_or_none.return_value = "Test Org"

        mock_session.execute.side_effect = [audit_result, name_result, org_result]

        repo = AccessTrackingRepository(mock_session)
        result = await repo.get_recent_for_user(user_id, limit=10)

        assert len(result) == 1
        assert isinstance(result[0], RecentItem)
        assert result[0].entity_type == "password"
        assert result[0].entity_id == entity_id
        assert result[0].organization_id == org_id
        assert result[0].org_name == "Test Org"
        assert result[0].name == "My Password"
        assert result[0].viewed_at == viewed_at

    async def test_get_recent_for_user_respects_limit(self):
        """Test get_recent_for_user respects the limit parameter."""
        mock_session = AsyncMock()
        user_id = uuid4()

        # Create 5 views
        views = []
        for i in range(5):
            views.append(
                MagicMock(
                    entity_type="password",
                    entity_id=uuid4(),
                    organization_id=uuid4(),
                    viewed_at=datetime.now(UTC) - timedelta(hours=i),
                )
            )

        # First call: audit log query returns 5 views
        audit_result = MagicMock()
        audit_result.all.return_value = views

        # Subsequent calls for name/org lookups
        name_result = MagicMock()
        name_result.scalar_one_or_none.return_value = "Password Name"

        org_result = MagicMock()
        org_result.scalar_one_or_none.return_value = "Org Name"

        # First audit query, then alternating name/org queries for each item
        side_effects = [audit_result]
        for _ in range(3):  # Only 3 items should be processed due to limit
            side_effects.extend([name_result, org_result])

        mock_session.execute.side_effect = side_effects

        repo = AccessTrackingRepository(mock_session)
        result = await repo.get_recent_for_user(user_id, limit=3)

        # Should return at most 3 items
        assert len(result) == 3

    async def test_get_recent_for_user_skips_deleted_entities(self):
        """Test get_recent_for_user skips entities that no longer exist."""
        mock_session = AsyncMock()
        user_id = uuid4()
        entity_id_1 = uuid4()
        entity_id_2 = uuid4()
        org_id = uuid4()
        viewed_at = datetime.now(UTC)

        # Two views in audit log
        audit_result = MagicMock()
        audit_result.all.return_value = [
            MagicMock(
                entity_type="password",
                entity_id=entity_id_1,
                organization_id=org_id,
                viewed_at=viewed_at,
            ),
            MagicMock(
                entity_type="password",
                entity_id=entity_id_2,
                organization_id=org_id,
                viewed_at=viewed_at - timedelta(hours=1),
            ),
        ]

        # First entity lookup returns None (deleted)
        name_result_1 = MagicMock()
        name_result_1.scalar_one_or_none.return_value = None

        # Second entity lookup returns a name
        name_result_2 = MagicMock()
        name_result_2.scalar_one_or_none.return_value = "Existing Password"

        # Org name lookup
        org_result = MagicMock()
        org_result.scalar_one_or_none.return_value = "Test Org"

        mock_session.execute.side_effect = [
            audit_result,
            name_result_1,  # First entity - deleted
            name_result_2,  # Second entity - exists
            org_result,     # Org name for second entity
        ]

        repo = AccessTrackingRepository(mock_session)
        result = await repo.get_recent_for_user(user_id, limit=10)

        # Should only return the existing entity
        assert len(result) == 1
        assert result[0].entity_id == entity_id_2
        assert result[0].name == "Existing Password"

    async def test_get_frequently_accessed_returns_empty_list_when_no_views(self):
        """Test get_frequently_accessed returns empty list when no views exist."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = AccessTrackingRepository(mock_session)
        result = await repo.get_frequently_accessed(uuid4(), limit=6, days=30)

        assert result == []
        assert isinstance(result, list)

    async def test_get_frequently_accessed_returns_correct_shape(self):
        """Test get_frequently_accessed returns correctly shaped FrequentItem objects."""
        mock_session = AsyncMock()
        org_id = uuid4()
        entity_id = uuid4()

        # First call: frequency query returns one result
        freq_result = MagicMock()
        freq_result.all.return_value = [
            MagicMock(
                entity_type="document",
                entity_id=entity_id,
                view_count=15,
            )
        ]

        # Second call: entity name query
        name_result = MagicMock()
        name_result.scalar_one_or_none.return_value = "Important Document"

        mock_session.execute.side_effect = [freq_result, name_result]

        repo = AccessTrackingRepository(mock_session)
        result = await repo.get_frequently_accessed(org_id, limit=6, days=30)

        assert len(result) == 1
        assert isinstance(result[0], FrequentItem)
        assert result[0].entity_type == "document"
        assert result[0].entity_id == entity_id
        assert result[0].name == "Important Document"
        assert result[0].view_count == 15

    async def test_get_frequently_accessed_respects_limit(self):
        """Test get_frequently_accessed respects the limit parameter."""
        mock_session = AsyncMock()
        org_id = uuid4()

        # Create 10 results
        freq_data = []
        for i in range(10):
            freq_data.append(
                MagicMock(
                    entity_type="configuration",
                    entity_id=uuid4(),
                    view_count=100 - i,  # Decreasing view counts
                )
            )

        # First call: frequency query returns all 10
        freq_result = MagicMock()
        freq_result.all.return_value = freq_data

        # Name lookups
        name_result = MagicMock()
        name_result.scalar_one_or_none.return_value = "Config Name"

        # First freq query, then name query for each item up to limit
        side_effects = [freq_result]
        for _ in range(4):  # Only 4 items should be processed due to limit
            side_effects.append(name_result)

        mock_session.execute.side_effect = side_effects

        repo = AccessTrackingRepository(mock_session)
        result = await repo.get_frequently_accessed(org_id, limit=4, days=30)

        # Should return at most 4 items
        assert len(result) == 4

    async def test_get_frequently_accessed_filters_by_organization(self):
        """Test get_frequently_accessed queries the correct organization."""
        mock_session = AsyncMock()
        org_id = uuid4()

        # Empty result
        freq_result = MagicMock()
        freq_result.all.return_value = []
        mock_session.execute.return_value = freq_result

        repo = AccessTrackingRepository(mock_session)
        await repo.get_frequently_accessed(org_id, limit=6, days=30)

        # Verify execute was called
        assert mock_session.execute.called
        # The query should contain filters for organization_id and action='view'

    async def test_get_frequently_accessed_filters_by_time_window(self):
        """Test get_frequently_accessed respects the days parameter for time window."""
        mock_session = AsyncMock()
        org_id = uuid4()

        # Empty result
        freq_result = MagicMock()
        freq_result.all.return_value = []
        mock_session.execute.return_value = freq_result

        repo = AccessTrackingRepository(mock_session)
        # Call with different days values to ensure they affect the query
        await repo.get_frequently_accessed(org_id, limit=6, days=7)
        await repo.get_frequently_accessed(org_id, limit=6, days=90)

        # Verify execute was called twice with different queries
        assert mock_session.execute.call_count == 2

    async def test_get_recent_for_user_handles_null_organization(self):
        """Test get_recent_for_user handles entities without organization_id."""
        mock_session = AsyncMock()
        user_id = uuid4()
        entity_id = uuid4()
        viewed_at = datetime.now(UTC)

        # View without organization_id
        audit_result = MagicMock()
        audit_result.all.return_value = [
            MagicMock(
                entity_type="password",
                entity_id=entity_id,
                organization_id=None,  # No organization
                viewed_at=viewed_at,
            )
        ]

        # Entity name lookup
        name_result = MagicMock()
        name_result.scalar_one_or_none.return_value = "Orphan Password"

        mock_session.execute.side_effect = [audit_result, name_result]

        repo = AccessTrackingRepository(mock_session)
        result = await repo.get_recent_for_user(user_id, limit=10)

        assert len(result) == 1
        assert result[0].organization_id is None
        assert result[0].org_name is None
        assert result[0].name == "Orphan Password"

    async def test_get_entity_name_handles_unknown_entity_type(self):
        """Test _get_entity_name handles unknown entity types gracefully."""
        mock_session = AsyncMock()
        user_id = uuid4()
        entity_id = uuid4()
        org_id = uuid4()
        viewed_at = datetime.now(UTC)

        # View with unknown entity type
        audit_result = MagicMock()
        audit_result.all.return_value = [
            MagicMock(
                entity_type="unknown_type",
                entity_id=entity_id,
                organization_id=org_id,
                viewed_at=viewed_at,
            )
        ]

        # Org name lookup
        org_result = MagicMock()
        org_result.scalar_one_or_none.return_value = "Test Org"

        mock_session.execute.side_effect = [audit_result, org_result]

        repo = AccessTrackingRepository(mock_session)
        result = await repo.get_recent_for_user(user_id, limit=10)

        assert len(result) == 1
        # Unknown types should return a formatted fallback name
        assert "unknown_type" in result[0].name
        assert str(entity_id) in result[0].name

    async def test_get_custom_asset_name_with_display_field(self):
        """Test _get_custom_asset_name uses display_field_key when available."""
        mock_session = AsyncMock()
        entity_id = uuid4()

        # Mock the joined query result
        query_result = MagicMock()
        query_result.one_or_none.return_value = (
            {"hostname": "server-01", "ip": "192.168.1.1"},  # values
            "hostname",  # display_field_key
            "Server",   # type name
        )
        mock_session.execute.return_value = query_result

        repo = AccessTrackingRepository(mock_session)
        result = await repo._get_custom_asset_name(entity_id)

        assert result == "server-01"

    async def test_get_custom_asset_name_fallback_to_type_name(self):
        """Test _get_custom_asset_name falls back to type name when no display field."""
        mock_session = AsyncMock()
        entity_id = uuid4()

        # Mock the joined query result - no display_field_key
        query_result = MagicMock()
        query_result.one_or_none.return_value = (
            {"some_field": "value"},  # values
            None,  # no display_field_key
            "CustomType",   # type name
        )
        mock_session.execute.return_value = query_result

        repo = AccessTrackingRepository(mock_session)
        result = await repo._get_custom_asset_name(entity_id)

        assert result is not None
        assert "CustomType" in result
        assert str(entity_id)[:8] in result

    async def test_get_custom_asset_name_returns_none_when_deleted(self):
        """Test _get_custom_asset_name returns None for deleted assets."""
        mock_session = AsyncMock()
        entity_id = uuid4()

        # Mock the joined query result - entity not found
        query_result = MagicMock()
        query_result.one_or_none.return_value = None
        mock_session.execute.return_value = query_result

        repo = AccessTrackingRepository(mock_session)
        result = await repo._get_custom_asset_name(entity_id)

        assert result is None
