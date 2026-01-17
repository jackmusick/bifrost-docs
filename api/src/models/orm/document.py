"""
Document ORM model.

Represents documentation files in the Bifrost Docs platform.
Uses virtual paths (like S3) for folder structure - no separate folder table.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.orm.base import Base

if TYPE_CHECKING:
    from src.models.orm.organization import Organization
    from src.models.orm.user import User


class Document(Base):
    """Document database table."""

    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true", default=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        comment="Virtual folder path, e.g., /Infrastructure/Network/Diagrams",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
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
    organization: Mapped["Organization"] = relationship(back_populates="documents")
    updated_by_user: Mapped["User | None"] = relationship()

    __table_args__ = (
        Index("ix_documents_organization_id", "organization_id"),
        Index("ix_documents_organization_path", "organization_id", "path"),
        Index("ix_documents_name", "name"),
    )
