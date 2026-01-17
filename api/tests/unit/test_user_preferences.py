"""
Unit tests for UserPreferences repository.

Tests the repository methods in isolation using mocked database sessions.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.models.orm.user_preferences import UserPreferences
from src.repositories.user_preferences import UserPreferencesRepository


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    return session


@pytest.fixture
def sample_user_id():
    """Sample user UUID."""
    return uuid4()


@pytest.fixture
def sample_entity_type():
    """Sample entity type."""
    return "passwords"


@pytest.fixture
def sample_preferences():
    """Sample preferences data."""
    return {
        "columns": {
            "visible": ["name", "username", "url"],
            "order": ["name", "username", "url", "notes", "created_at"],
            "widths": {"name": 200, "username": 150},
        }
    }


@pytest.fixture
def sample_user_preferences(sample_user_id, sample_entity_type, sample_preferences):
    """Create a sample UserPreferences ORM object."""
    return UserPreferences(
        id=uuid4(),
        user_id=sample_user_id,
        entity_type=sample_entity_type,
        preferences=sample_preferences,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.mark.unit
class TestUserPreferencesRepository:
    """Tests for UserPreferencesRepository."""

    @pytest.mark.asyncio
    async def test_get_by_user_and_entity_returns_preferences(
        self,
        mock_session,
        sample_user_id,
        sample_entity_type,
        sample_user_preferences,
    ):
        """Test getting preferences by user and entity type."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user_preferences
        mock_session.execute.return_value = mock_result

        repo = UserPreferencesRepository(mock_session)

        # Act
        result = await repo.get_by_user_and_entity(sample_user_id, sample_entity_type)

        # Assert
        assert result is not None
        assert result.user_id == sample_user_id
        assert result.entity_type == sample_entity_type
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_user_and_entity_returns_none_when_not_found(
        self,
        mock_session,
        sample_user_id,
        sample_entity_type,
    ):
        """Test getting preferences returns None when not found."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = UserPreferencesRepository(mock_session)

        # Act
        result = await repo.get_by_user_and_entity(sample_user_id, sample_entity_type)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_creates_new_preferences(
        self,
        mock_session,
        sample_user_id,
        sample_entity_type,
        sample_preferences,
        sample_user_preferences,
    ):
        """Test upserting creates new preferences when they don't exist."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = sample_user_preferences
        mock_session.execute.return_value = mock_result

        repo = UserPreferencesRepository(mock_session)

        # Act
        result = await repo.upsert(sample_user_id, sample_entity_type, sample_preferences)

        # Assert
        assert result is not None
        assert result.user_id == sample_user_id
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_by_user_and_entity_returns_true_when_deleted(
        self,
        mock_session,
        sample_user_id,
        sample_entity_type,
    ):
        """Test deleting preferences returns True when record is deleted."""
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        repo = UserPreferencesRepository(mock_session)

        # Act
        result = await repo.delete_by_user_and_entity(sample_user_id, sample_entity_type)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_by_user_and_entity_returns_false_when_not_found(
        self,
        mock_session,
        sample_user_id,
        sample_entity_type,
    ):
        """Test deleting preferences returns False when not found."""
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        repo = UserPreferencesRepository(mock_session)

        # Act
        result = await repo.delete_by_user_and_entity(sample_user_id, sample_entity_type)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_get_all_for_user_returns_list(
        self,
        mock_session,
        sample_user_id,
        sample_user_preferences,
    ):
        """Test getting all preferences for a user returns a list."""
        # Arrange
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_user_preferences]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = UserPreferencesRepository(mock_session)

        # Act
        result = await repo.get_all_for_user(sample_user_id)

        # Assert
        assert len(result) == 1
        assert result[0].user_id == sample_user_id


@pytest.mark.unit
class TestPreferencesDataStructure:
    """Tests for preferences data structure validation."""

    def test_column_preferences_structure(self, sample_preferences):
        """Test that column preferences have expected structure."""
        assert "columns" in sample_preferences
        columns = sample_preferences["columns"]
        assert "visible" in columns
        assert "order" in columns
        assert "widths" in columns
        assert isinstance(columns["visible"], list)
        assert isinstance(columns["order"], list)
        assert isinstance(columns["widths"], dict)

    def test_empty_preferences_structure(self):
        """Test that empty preferences are valid."""
        empty_prefs = {"columns": {"visible": [], "order": [], "widths": {}}}
        assert empty_prefs["columns"]["visible"] == []
        assert empty_prefs["columns"]["order"] == []
        assert empty_prefs["columns"]["widths"] == {}
