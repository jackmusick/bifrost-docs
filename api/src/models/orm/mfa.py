"""
MFA-related ORM models.

Represents MFA methods and recovery codes.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.enums import MFAMethodStatus, MFAMethodType
from src.models.orm.base import Base

if TYPE_CHECKING:
    from src.models.orm.user import User


class UserMFAMethod(Base):
    """User MFA method enrollment."""

    __tablename__ = "user_mfa_methods"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    method_type: Mapped[MFAMethodType] = mapped_column(
        sqlalchemy.Enum(
            MFAMethodType,
            name="mfa_method_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        )
    )
    status: Mapped[MFAMethodStatus] = mapped_column(
        sqlalchemy.Enum(
            MFAMethodStatus,
            name="mfa_method_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=MFAMethodStatus.PENDING,
    )
    encrypted_secret: Mapped[str | None] = mapped_column(Text, default=None)
    mfa_metadata: Mapped[dict] = mapped_column(JSONB, default={})
    last_used_counter: Mapped[int | None] = mapped_column(Integer, default=None)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="mfa_methods")

    __table_args__ = (
        Index("ix_user_mfa_methods_user_id", "user_id"),
        Index("ix_user_mfa_methods_user_status", "user_id", "status"),
    )


class MFARecoveryCode(Base):
    """MFA recovery codes."""

    __tablename__ = "mfa_recovery_codes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    code_hash: Mapped[str] = mapped_column(String(255))
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    used_from_ip: Mapped[str | None] = mapped_column(String(45), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="recovery_codes")

    __table_args__ = (
        Index("ix_mfa_recovery_codes_user_id", "user_id"),
        Index("ix_mfa_recovery_codes_user_unused", "user_id", "is_used"),
    )
