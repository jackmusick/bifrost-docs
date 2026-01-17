"""
Passkey (WebAuthn) ORM model.

Represents WebAuthn passkey credentials for passwordless authentication.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.orm.base import Base

if TYPE_CHECKING:
    from src.models.orm.user import User


class UserPasskey(Base):
    """WebAuthn passkey credentials for passwordless authentication."""

    __tablename__ = "user_passkeys"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))

    # WebAuthn credential data (required for verification)
    credential_id: Mapped[bytes] = mapped_column(sqlalchemy.LargeBinary, unique=True)
    public_key: Mapped[bytes] = mapped_column(sqlalchemy.LargeBinary)
    sign_count: Mapped[int] = mapped_column(Integer, default=0)

    # Credential metadata
    transports: Mapped[list] = mapped_column(JSONB, default=[])  # usb, nfc, ble, internal
    device_type: Mapped[str] = mapped_column(String(50))  # singleDevice, multiDevice
    backed_up: Mapped[bool] = mapped_column(Boolean, default=False)

    # User-facing info
    name: Mapped[str] = mapped_column(String(255))  # "MacBook Pro Touch ID"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="passkeys")

    __table_args__ = (
        Index("ix_user_passkeys_user_id", "user_id"),
        Index("ix_user_passkeys_credential_id", "credential_id", unique=True),
    )
