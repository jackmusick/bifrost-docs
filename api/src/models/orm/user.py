"""
User ORM model.

Represents users in the Bifrost Docs platform.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy
from sqlalchemy import Boolean, DateTime, Index, LargeBinary, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.enums import UserRole
from src.models.orm.base import Base

if TYPE_CHECKING:
    from src.models.orm.api_key import APIKey
    from src.models.orm.mfa import MFARecoveryCode, UserMFAMethod
    from src.models.orm.passkey import UserPasskey
    from src.models.orm.session import Session
    from src.models.orm.user_oauth_account import UserOAuthAccount
    from src.models.orm.user_preferences import UserPreferences


class User(Base):
    """User database table."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    name: Mapped[str | None] = mapped_column(String(255), default=None)
    hashed_password: Mapped[str | None] = mapped_column(String(1024), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[UserRole] = mapped_column(
        sqlalchemy.Enum(
            UserRole,
            name="user_role",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=UserRole.CONTRIBUTOR,
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
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

    # WebAuthn/Passkeys
    webauthn_user_id: Mapped[bytes | None] = mapped_column(LargeBinary(64), default=None)

    # Relationships
    sessions: Mapped[list["Session"]] = relationship(back_populates="user")
    passkeys: Mapped[list["UserPasskey"]] = relationship(back_populates="user")
    mfa_methods: Mapped[list["UserMFAMethod"]] = relationship(back_populates="user")
    recovery_codes: Mapped[list["MFARecoveryCode"]] = relationship(back_populates="user")
    api_keys: Mapped[list["APIKey"]] = relationship(back_populates="user")
    oauth_accounts: Mapped[list["UserOAuthAccount"]] = relationship(back_populates="user")
    preferences: Mapped[list["UserPreferences"]] = relationship(back_populates="user")

    __table_args__ = (Index("ix_users_email", "email"),)
