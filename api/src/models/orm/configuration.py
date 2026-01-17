"""
Configuration ORM model.

Represents IT assets/configurations (servers, workstations, network devices, etc.).
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.orm.base import Base

if TYPE_CHECKING:
    from src.models.orm.configuration_status import ConfigurationStatus
    from src.models.orm.configuration_type import ConfigurationType
    from src.models.orm.organization import Organization
    from src.models.orm.user import User


class Configuration(Base):
    """Configuration database table."""

    __tablename__ = "configurations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true", default=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    configuration_type_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("configuration_types.id", ondelete="SET NULL"),
        nullable=True,
    )
    configuration_status_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("configuration_statuses.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255))  # hostname or friendly name
    serial_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    asset_tag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6 max
    mac_address: Mapped[str | None] = mapped_column(String(17), nullable=True)  # XX:XX:XX:XX:XX:XX
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
        onupdate=lambda: datetime.now(UTC),
    )
    updated_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )
    interfaces: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    # Relationships
    organization: Mapped["Organization"] = relationship()
    configuration_type: Mapped["ConfigurationType | None"] = relationship(
        back_populates="configurations"
    )
    configuration_status: Mapped["ConfigurationStatus | None"] = relationship(
        back_populates="configurations"
    )
    updated_by_user: Mapped["User | None"] = relationship()

    __table_args__ = (
        Index("ix_configurations_organization_id", "organization_id"),
        Index("ix_configurations_configuration_type_id", "configuration_type_id"),
        Index("ix_configurations_configuration_status_id", "configuration_status_id"),
        Index("ix_configurations_name", "name"),
    )
