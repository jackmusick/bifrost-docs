"""Add user_preferences table for persisting UI preferences

Revision ID: 016
Revises: 015
Create Date: 2026-01-13 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "016"
down_revision: str | None = "015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create user_preferences table for storing per-user UI preferences
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "entity_type",
            sa.String(length=100),
            nullable=False,
            comment="Entity type identifier (e.g., 'passwords', 'configurations', 'custom_asset_{uuid}')",
        ),
        sa.Column(
            "preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
            comment="Preferences data: {columns: {visible: [], order: [], widths: {}}}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_preferences_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "entity_type",
            name="uq_user_preferences_user_entity",
        ),
    )

    # Create index for faster lookups by user_id
    op.create_index(
        "ix_user_preferences_user_id",
        "user_preferences",
        ["user_id"],
    )

    # Create index for faster lookups by user_id + entity_type
    op.create_index(
        "ix_user_preferences_user_entity",
        "user_preferences",
        ["user_id", "entity_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_preferences_user_entity", table_name="user_preferences")
    op.drop_index("ix_user_preferences_user_id", table_name="user_preferences")
    op.drop_table("user_preferences")
