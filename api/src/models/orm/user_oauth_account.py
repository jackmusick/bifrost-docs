"""
UserOAuthAccount ORM model.

Represents OAuth/SSO accounts linked to users.
Allows users to login via external identity providers.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.orm.base import Base

if TYPE_CHECKING:
    from src.models.orm.user import User


class UserOAuthAccount(Base):
    """
    OAuth account linked to a user.

    Each user can have multiple OAuth accounts (e.g., Microsoft + Google).
    Identified by provider + provider_user_id (unique across all users).
    """

    __tablename__ = "user_oauth_accounts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="OAuth provider name (microsoft, google, oidc)",
    )
    provider_user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User ID from the OAuth provider",
    )
    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        comment="Email from OAuth provider (may differ from user.email)",
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful login via this OAuth account",
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

    # Relationships
    user: Mapped["User"] = relationship(  # noqa: F821
        back_populates="oauth_accounts"
    )

    __table_args__ = (
        # Unique constraint: one provider account can only be linked to one user
        Index(
            "ix_user_oauth_accounts_provider_user",
            "provider_id",
            "provider_user_id",
            unique=True,
        ),
        # Index for looking up all OAuth accounts for a user
        Index("ix_user_oauth_accounts_user_id", "user_id"),
    )
