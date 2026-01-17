"""
Session ORM model.

Represents user sessions for refresh token management.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.orm.base import Base

if TYPE_CHECKING:
    from src.models.orm.user import User


class Session(Base):
    """User session database table."""

    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    refresh_token_hash: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
    )
    # Optional metadata
    user_agent: Mapped[str | None] = mapped_column(String(512), default=None)
    ip_address: Mapped[str | None] = mapped_column(String(45), default=None)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")

    @property
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return datetime.now(UTC) > self.expires_at

    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_refresh_token_hash", "refresh_token_hash"),
    )
