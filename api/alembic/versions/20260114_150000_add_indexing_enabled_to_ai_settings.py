"""Add indexing_enabled column to ai_settings

This migration adds an indexing_enabled column to allow disabling automatic
indexing during large data migrations. When disabled, entity creates/updates
will skip the search indexing step, which can significantly speed up bulk
imports and migrations.

Changes:
1. Add indexing_enabled column to ai_settings (Boolean, NOT NULL, DEFAULT true)

Revision ID: 20260114_150000
Revises: 20260114_140000
Create Date: 2026-01-14 15:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260114_150000"
down_revision: str | None = "20260114_140000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ==========================================================================
    # Add indexing_enabled column to ai_settings
    # ==========================================================================
    # This allows administrators to disable automatic indexing during migrations.
    # Default is True so existing deployments continue indexing as before.

    op.add_column(
        "ai_settings",
        sa.Column("indexing_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade() -> None:
    # ==========================================================================
    # Drop indexing_enabled column
    # ==========================================================================

    op.drop_column("ai_settings", "indexing_enabled")
