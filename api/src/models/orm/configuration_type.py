"""
Configuration Type ORM model.

Represents types of configurations (e.g., Server, Workstation, Network Device).
These are global types shared across all organizations.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.orm.base import Base

if TYPE_CHECKING:
    from src.models.orm.configuration import Configuration


class ConfigurationType(Base):
    """Configuration type database table (global, not org-scoped)."""

    __tablename__ = "configuration_types"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    # Relationships
    configurations: Mapped[list["Configuration"]] = relationship(
        back_populates="configuration_type"
    )

    __table_args__ = (Index("ix_configuration_types_name", "name"),)
