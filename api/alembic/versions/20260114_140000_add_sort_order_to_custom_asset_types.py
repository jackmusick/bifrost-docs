"""Add sort_order column to custom_asset_types

This migration adds a sort_order column to custom_asset_types to support
drag-and-drop reordering in the settings UI.

Changes:
1. Add sort_order column to custom_asset_types (INTEGER, NOT NULL, DEFAULT 0)
2. Initialize sort_order based on current created_at order
3. Update index to include sort_order for better query performance

Revision ID: 20260114_140000
Revises: 9af382cc87c4
Create Date: 2026-01-14 14:00:00.000000+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260114_140000"
down_revision: str | None = "9af382cc87c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ==========================================================================
    # Add sort_order column to custom_asset_types
    # ==========================================================================

    op.add_column(
        "custom_asset_types",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )

    # ==========================================================================
    # Initialize sort_order based on current created_at order
    # ==========================================================================
    # This sets sort_order to 1, 2, 3, ... based on the order assets were created

    op.execute(
        """
        WITH ordered AS (
          SELECT id, ROW_NUMBER() OVER (ORDER BY created_at) as rn
          FROM custom_asset_types
        )
        UPDATE custom_asset_types
        SET sort_order = ordered.rn
        FROM ordered
        WHERE custom_asset_types.id = ordered.id;
        """
    )

    # ==========================================================================
    # Create index for sort_order to improve query performance
    # ==========================================================================

    op.create_index(
        "ix_custom_asset_types_sort_order",
        "custom_asset_types",
        ["sort_order"],
    )


def downgrade() -> None:
    # ==========================================================================
    # Drop sort_order index and column
    # ==========================================================================

    op.drop_index("ix_custom_asset_types_sort_order", table_name="custom_asset_types")
    op.drop_column("custom_asset_types", "sort_order")
