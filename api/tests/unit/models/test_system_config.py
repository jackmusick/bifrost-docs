"""Tests for SystemConfig ORM model."""
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.models.orm.system_config import SystemConfig

__all__: list[str] = []


@pytest.mark.unit
class TestSystemConfigModel:
    """Tests for SystemConfig model."""

    def test_create_system_config(self) -> None:
        """Test creating a SystemConfig instance."""
        config = SystemConfig(
            category="llm",
            key="completions_config",
            value_json={"provider": "openai", "model": "gpt-4o"},
        )
        assert config.category == "llm"
        assert config.key == "completions_config"
        assert config.value_json is not None
        assert config.value_json["provider"] == "openai"

    def test_system_config_with_explicit_id(self) -> None:
        """Test creating a SystemConfig with explicit id and timestamps."""
        test_id = uuid4()
        test_time = datetime.now(UTC)
        config = SystemConfig(
            id=test_id,
            category="test",
            key="test_key",
            value_json={},
            created_at=test_time,
            updated_at=test_time,
        )
        assert config.id == test_id
        assert config.created_at == test_time
        assert config.updated_at == test_time

    def test_system_config_table_name(self) -> None:
        """Test that SystemConfig has correct table name."""
        assert SystemConfig.__tablename__ == "system_configs"

    def test_system_config_repr(self) -> None:
        """Test SystemConfig string representation."""
        config = SystemConfig(
            category="llm",
            key="completions_config",
            value_json={},
        )
        # Model doesn't define __repr__, so it uses default SQLAlchemy repr
        assert "SystemConfig" in repr(config)

    def test_system_config_optional_fields(self) -> None:
        """Test SystemConfig optional fields."""
        config = SystemConfig(
            category="test",
            key="test_key",
            value_json={"setting": "value"},
        )
        # Optional fields should be None by default
        assert config.organization_id is None
        assert config.value_bytes is None
        assert config.created_by is None
        assert config.updated_by is None

    def test_system_config_with_organization(self) -> None:
        """Test SystemConfig with organization_id."""
        org_id = uuid4()
        config = SystemConfig(
            category="org_specific",
            key="setting",
            value_json={"enabled": True},
            organization_id=org_id,
        )
        assert config.organization_id == org_id

    def test_system_config_value_json_types(self) -> None:
        """Test SystemConfig accepts various JSON structures."""
        # Nested dict
        config1 = SystemConfig(
            category="llm",
            key="config",
            value_json={
                "provider": "openai",
                "settings": {"model": "gpt-4o", "temperature": 0.7},
            },
        )
        assert config1.value_json is not None
        assert config1.value_json["settings"]["model"] == "gpt-4o"

        # List in JSON
        config2 = SystemConfig(
            category="features",
            key="enabled",
            value_json={"features": ["feature1", "feature2"]},
        )
        assert config2.value_json is not None
        assert "feature1" in config2.value_json["features"]
