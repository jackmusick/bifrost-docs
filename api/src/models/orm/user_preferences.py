"""
User Preferences ORM model.

Stores per-user UI preferences such as column visibility, order, and widths
for DataTable components. Each user can have different preferences for different
entity types (passwords, configurations, custom_asset_{type_id}, etc.).
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.orm.base import Base

if TYPE_CHECKING:
    from src.models.orm.user import User


class UserPreferences(Base):
    """User preferences database table."""

    __tablename__ = "user_preferences"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Entity type identifier, e.g., "passwords", "configurations", "custom_asset_{uuid}"
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # Preferences JSON: {columns: {visible: [], order: [], widths: {}}}
    preferences: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
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
    user: Mapped["User"] = relationship(back_populates="preferences")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "entity_type",
            name="uq_user_preferences_user_entity",
        ),
    )
