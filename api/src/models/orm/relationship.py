"""
Relationship ORM model.

Represents bidirectional relationships between entities in the Bifrost Docs platform.
A universal junction table that links any entity to any other entity.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.orm.base import Base

if TYPE_CHECKING:
    from src.models.orm.organization import Organization


class Relationship(Base):
    """Relationship database table for linking entities."""

    __tablename__ = "relationships"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Entity type: password, configuration, location, document, custom_asset",
    )
    source_id: Mapped[UUID] = mapped_column(nullable=False)
    target_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Entity type: password, configuration, location, document, custom_asset",
    )
    target_id: Mapped[UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship()

    __table_args__ = (
        # Unique constraint to prevent duplicate relationships
        # Normalized storage: source_type < target_type, or if same, source_id < target_id
        UniqueConstraint(
            "source_type",
            "source_id",
            "target_type",
            "target_id",
            name="uq_relationships_source_target",
        ),
        Index("ix_relationships_organization_id", "organization_id"),
        Index("ix_relationships_source", "source_type", "source_id"),
        Index("ix_relationships_target", "target_type", "target_id"),
    )
