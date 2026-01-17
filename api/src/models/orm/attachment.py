"""
Attachment ORM model.

Represents file attachments linked to various entities in Bifrost Docs.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.enums import EntityType
from src.models.orm.base import Base

if TYPE_CHECKING:
    from src.models.orm.organization import Organization


class Attachment(Base):
    """Attachment database table."""

    __tablename__ = "attachments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[EntityType] = mapped_column(
        String(50),
        nullable=False,
    )
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship()

    __table_args__ = (
        Index("ix_attachments_organization_id", "organization_id"),
        Index("ix_attachments_entity", "organization_id", "entity_type", "entity_id"),
        Index("ix_attachments_s3_key", "s3_key"),
    )
