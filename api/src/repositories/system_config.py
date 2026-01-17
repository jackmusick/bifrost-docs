"""Repository for SystemConfig model operations."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.orm.system_config import SystemConfig


class SystemConfigRepository:
    """Repository for system configuration operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_config(self, category: str, key: str) -> SystemConfig | None:
        """Get a configuration by category and key."""
        result = await self.session.execute(
            select(SystemConfig).where(
                SystemConfig.category == category,
                SystemConfig.key == key,
            )
        )
        return result.scalar_one_or_none()

    async def set_config(
        self, category: str, key: str, value_json: dict
    ) -> SystemConfig:
        """Set a configuration value, creating or updating as needed."""
        config = await self.get_config(category, key)

        if config is None:
            config = SystemConfig(
                category=category,
                key=key,
                value_json=value_json,
            )
            self.session.add(config)
        else:
            config.value_json = value_json

        await self.session.flush()
        await self.session.refresh(config)
        return config

    async def delete_config(self, category: str, key: str) -> bool:
        """Delete a configuration. Returns True if deleted, False if not found."""
        config = await self.get_config(category, key)
        if config is None:
            return False

        await self.session.delete(config)
        await self.session.flush()
        return True

    async def get_all_by_category(self, category: str) -> list[SystemConfig]:
        """Get all configurations in a category."""
        result = await self.session.execute(
            select(SystemConfig).where(SystemConfig.category == category)
        )
        return list(result.scalars().all())
