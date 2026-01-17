"""Add is_active soft delete column to type tables

Revision ID: 015
Revises: 014
Create Date: 2026-01-13 00:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "015"
down_revision: str | None = "014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add is_active column to custom_asset_types
    op.add_column(
        "custom_asset_types",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    # Add is_active column to configuration_types
    op.add_column(
        "configuration_types",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    # Add is_active column to configuration_statuses
    op.add_column(
        "configuration_statuses",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("custom_asset_types", "is_active")
    op.drop_column("configuration_types", "is_active")
    op.drop_column("configuration_statuses", "is_active")
