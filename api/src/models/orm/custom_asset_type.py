"""
Custom Asset Type ORM model.

Represents custom asset type definitions (schemas) in the Bifrost Docs platform.
Each custom asset type defines the field structure for a category of custom assets.
These are global types shared across all organizations.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.orm.base import Base

if TYPE_CHECKING:
    from src.models.orm.custom_asset import CustomAsset


class CustomAssetType(Base):
    """Custom asset type database table (global, not org-scoped)."""

    __tablename__ = "custom_asset_types"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    fields: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="[]",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    display_field_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
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
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    # Relationships
    custom_assets: Mapped[list["CustomAsset"]] = relationship(
        back_populates="custom_asset_type",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("ix_custom_asset_types_name", "name"),)
