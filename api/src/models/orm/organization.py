"""
Organization ORM model.

Represents tenant organizations in the Bifrost Docs platform.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.orm.base import Base

if TYPE_CHECKING:
    from src.models.orm.custom_asset import CustomAsset
    from src.models.orm.document import Document
    from src.models.orm.location import Location
    from src.models.orm.user import User


class Organization(Base):
    """Organization database table."""

    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true", default=True)
    name: Mapped[str] = mapped_column(String(255))
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
    custom_assets: Mapped[list["CustomAsset"]] = relationship(back_populates="organization")
    documents: Mapped[list["Document"]] = relationship(back_populates="organization")
    locations: Mapped[list["Location"]] = relationship(back_populates="organization")
    updated_by_user: Mapped["User | None"] = relationship()

    __table_args__ = (Index("ix_organizations_name", "name"),)
