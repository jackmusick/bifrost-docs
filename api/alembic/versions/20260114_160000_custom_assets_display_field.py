"""Add display_field_key to custom_asset_types and migrate name to values

Revision ID: 20260114_160000
Revises: 20260114_150000
Create Date: 2026-01-14 16:00:00.000000

This migration:
1. Adds display_field_key column to custom_asset_types
2. Migrates existing custom_assets.name values into the values JSON field
3. Drops the name column from custom_assets
4. Drops the ix_custom_assets_name index
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260114_160000"
down_revision: str | None = "20260114_150000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add display_field_key column to custom_asset_types
    op.add_column(
        "custom_asset_types",
        sa.Column("display_field_key", sa.String(255), nullable=True),
    )

    # 2. Migrate name values into the values JSON field for custom_assets
    # This uses raw SQL to update the JSONB field, adding "name" key with the current name value
    op.execute(
        """
        UPDATE custom_assets
        SET values = values || jsonb_build_object('name', name)
        WHERE name IS NOT NULL AND name != '' AND NOT (values ? 'name')
        """
    )

    # 3. Drop the ix_custom_assets_name index
    op.drop_index("ix_custom_assets_name", table_name="custom_assets")

    # 4. Drop the name column from custom_assets
    op.drop_column("custom_assets", "name")


def downgrade() -> None:
    # 1. Add name column back to custom_assets
    op.add_column(
        "custom_assets",
        sa.Column("name", sa.String(255), nullable=True),
    )

    # 2. Restore name from values JSON field
    op.execute(
        """
        UPDATE custom_assets
        SET name = COALESCE(values->>'name', 'Unnamed Asset')
        """
    )

    # 3. Make name column non-nullable
    op.alter_column("custom_assets", "name", nullable=False)

    # 4. Recreate the ix_custom_assets_name index
    op.create_index("ix_custom_assets_name", "custom_assets", ["name"])

    # 5. Drop display_field_key column from custom_asset_types
    op.drop_column("custom_asset_types", "display_field_key")
