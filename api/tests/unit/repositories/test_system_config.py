"""Tests for SystemConfig repository."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.models.orm.system_config import SystemConfig
from src.repositories.system_config import SystemConfigRepository


@pytest.mark.unit
@pytest.mark.asyncio
class TestSystemConfigRepository:
    """Tests for SystemConfigRepository."""

    async def test_get_config_returns_none_when_not_found(self):
        """Test get_config returns None when config doesn't exist."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = SystemConfigRepository(mock_session)
        result = await repo.get_config("llm", "completions_config")

        assert result is None

    async def test_get_config_returns_config_when_found(self):
        """Test get_config returns config when it exists."""
        mock_session = AsyncMock()
        config = SystemConfig(
            id=uuid4(),
            category="llm",
            key="completions_config",
            value_json={"provider": "openai"},
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = config
        mock_session.execute.return_value = mock_result

        repo = SystemConfigRepository(mock_session)
        result = await repo.get_config("llm", "completions_config")

        assert result == config

    async def test_set_config_creates_new_config(self):
        """Test set_config creates config when it doesn't exist."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.refresh = AsyncMock()

        repo = SystemConfigRepository(mock_session)
        result = await repo.set_config("llm", "completions_config", {"provider": "openai"})

        mock_session.add.assert_called_once()
        assert result.category == "llm"
        assert result.key == "completions_config"
        assert result.value_json is not None
        assert result.value_json["provider"] == "openai"

    async def test_set_config_updates_existing_config(self):
        """Test set_config updates config when it exists."""
        mock_session = AsyncMock()
        existing = SystemConfig(
            id=uuid4(),
            category="llm",
            key="completions_config",
            value_json={"provider": "openai"},
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = mock_result
        mock_session.refresh = AsyncMock()

        repo = SystemConfigRepository(mock_session)
        result = await repo.set_config("llm", "completions_config", {"provider": "anthropic"})

        assert result.value_json is not None
        assert result.value_json["provider"] == "anthropic"
        mock_session.add.assert_not_called()

    async def test_delete_config(self):
        """Test delete_config removes config."""
        mock_session = AsyncMock()
        existing = SystemConfig(
            id=uuid4(),
            category="llm",
            key="completions_config",
            value_json={},
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = mock_result

        repo = SystemConfigRepository(mock_session)
        result = await repo.delete_config("llm", "completions_config")

        assert result is True
        mock_session.delete.assert_called_once_with(existing)

    async def test_delete_config_returns_false_when_not_found(self):
        """Test delete_config returns False when config doesn't exist."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = SystemConfigRepository(mock_session)
        result = await repo.delete_config("llm", "nonexistent")

        assert result is False
        mock_session.delete.assert_not_called()

    async def test_get_all_by_category(self):
        """Test get_all_by_category returns all configs in category."""
        mock_session = AsyncMock()
        configs = [
            SystemConfig(id=uuid4(), category="llm", key="config1", value_json={}),
            SystemConfig(id=uuid4(), category="llm", key="config2", value_json={}),
        ]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = configs
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = SystemConfigRepository(mock_session)
        result = await repo.get_all_by_category("llm")

        assert len(result) == 2
        assert result[0].category == "llm"
        assert result[1].category == "llm"
