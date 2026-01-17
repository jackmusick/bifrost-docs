"""
Password ORM model.

Represents encrypted passwords stored for organizations.
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


class Password(Base):
    """Password database table for storing encrypted passwords."""

    __tablename__ = "passwords"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true", default=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    totp_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
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

    # Relationships
    organization: Mapped["Organization"] = relationship()
    updated_by_user: Mapped["User | None"] = relationship()

    __table_args__ = (
        Index("ix_passwords_organization_id", "organization_id"),
        Index("ix_passwords_name", "name"),
    )
