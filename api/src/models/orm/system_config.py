"""
SystemConfig ORM model.

Stores system-level configuration including OAuth SSO provider settings.
Uses category+key organization for different configuration types.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, LargeBinary, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.orm.base import Base


class SystemConfig(Base):
    """
    System-level configuration storage.

    Stores system settings like OAuth SSO configuration.
    Uses category+key for organization:
    - OAuth SSO: category='oauth_sso', key='microsoft_client_id', etc.

    value_json: For JSON config data (wraps values in {"value": ...})
    value_bytes: For binary data (future use)

    Client secrets are encrypted by the service layer before storage.
    """

    __tablename__ = "system_configs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    value_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
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
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_system_configs_category", "category"),
        Index("ix_system_configs_category_key", "category", "key"),
        Index("ix_system_configs_org_id", "organization_id"),
    )
