"""
Custom Asset ORM model.

Represents instances of custom assets in the Bifrost Docs platform.
Each custom asset belongs to a custom asset type and stores field values
according to the type's field definitions.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.orm.base import Base

if TYPE_CHECKING:
    from src.models.orm.custom_asset_type import CustomAssetType
    from src.models.orm.organization import Organization
    from src.models.orm.user import User


class CustomAsset(Base):
    """Custom asset database table."""

    __tablename__ = "custom_assets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true", default=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    custom_asset_type_id: Mapped[UUID] = mapped_column(
        ForeignKey("custom_asset_types.id", ondelete="CASCADE"),
        nullable=False,
    )
    values: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
    )
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

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="custom_assets")
    custom_asset_type: Mapped["CustomAssetType"] = relationship(back_populates="custom_assets")
    updated_by_user: Mapped["User | None"] = relationship()

    __table_args__ = (
        Index("ix_custom_assets_organization_id", "organization_id"),
        Index("ix_custom_assets_custom_asset_type_id", "custom_asset_type_id"),
    )
