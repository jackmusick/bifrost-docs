"""Make ConfigurationType, ConfigurationStatus, and CustomAssetType global

These type/template models are now global across all organizations,
not per-org scoped. This migration:
1. Drops the organization_id foreign key constraints and indexes
2. Removes the organization_id columns
3. Adds unique constraints on name for global uniqueness

Revision ID: 010
Revises: 009
Create Date: 2026-01-12 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ==========================================================================
    # configuration_types - make global
    # ==========================================================================

    # Drop the organization_id index
    op.drop_index("ix_configuration_types_organization_id", table_name="configuration_types")

    # Drop the foreign key constraint
    op.drop_constraint(
        "configuration_types_organization_id_fkey",
        "configuration_types",
        type_="foreignkey",
    )

    # Drop the organization_id column
    op.drop_column("configuration_types", "organization_id")

    # Add unique constraint on name
    op.create_unique_constraint(
        "uq_configuration_types_name",
        "configuration_types",
        ["name"],
    )

    # ==========================================================================
    # configuration_statuses - make global
    # ==========================================================================

    # Drop the organization_id index
    op.drop_index("ix_configuration_statuses_organization_id", table_name="configuration_statuses")

    # Drop the foreign key constraint
    op.drop_constraint(
        "configuration_statuses_organization_id_fkey",
        "configuration_statuses",
        type_="foreignkey",
    )

    # Drop the organization_id column
    op.drop_column("configuration_statuses", "organization_id")

    # Add unique constraint on name
    op.create_unique_constraint(
        "uq_configuration_statuses_name",
        "configuration_statuses",
        ["name"],
    )

    # ==========================================================================
    # custom_asset_types - make global
    # ==========================================================================

    # Drop the organization_id index
    op.drop_index("ix_custom_asset_types_organization_id", table_name="custom_asset_types")

    # Drop the foreign key constraint
    op.drop_constraint(
        "custom_asset_types_organization_id_fkey",
        "custom_asset_types",
        type_="foreignkey",
    )

    # Drop the organization_id column
    op.drop_column("custom_asset_types", "organization_id")

    # Add unique constraint on name
    op.create_unique_constraint(
        "uq_custom_asset_types_name",
        "custom_asset_types",
        ["name"],
    )


def downgrade() -> None:
    # ==========================================================================
    # custom_asset_types - restore organization scoping
    # ==========================================================================

    # Drop unique constraint on name
    op.drop_constraint("uq_custom_asset_types_name", "custom_asset_types", type_="unique")

    # Add back the organization_id column (nullable for existing data)
    op.add_column(
        "custom_asset_types",
        sa.Column("organization_id", sa.UUID(), nullable=True),
    )

    # Add back the foreign key constraint
    op.create_foreign_key(
        "custom_asset_types_organization_id_fkey",
        "custom_asset_types",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Add back the index
    op.create_index(
        "ix_custom_asset_types_organization_id",
        "custom_asset_types",
        ["organization_id"],
        unique=False,
    )

    # ==========================================================================
    # configuration_statuses - restore organization scoping
    # ==========================================================================

    # Drop unique constraint on name
    op.drop_constraint("uq_configuration_statuses_name", "configuration_statuses", type_="unique")

    # Add back the organization_id column (nullable for existing data)
    op.add_column(
        "configuration_statuses",
        sa.Column("organization_id", sa.UUID(), nullable=True),
    )

    # Add back the foreign key constraint
    op.create_foreign_key(
        "configuration_statuses_organization_id_fkey",
        "configuration_statuses",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Add back the index
    op.create_index(
        "ix_configuration_statuses_organization_id",
        "configuration_statuses",
        ["organization_id"],
        unique=False,
    )

    # ==========================================================================
    # configuration_types - restore organization scoping
    # ==========================================================================

    # Drop unique constraint on name
    op.drop_constraint("uq_configuration_types_name", "configuration_types", type_="unique")

    # Add back the organization_id column (nullable for existing data)
    op.add_column(
        "configuration_types",
        sa.Column("organization_id", sa.UUID(), nullable=True),
    )

    # Add back the foreign key constraint
    op.create_foreign_key(
        "configuration_types_organization_id_fkey",
        "configuration_types",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Add back the index
    op.create_index(
        "ix_configuration_types_organization_id",
        "configuration_types",
        ["organization_id"],
        unique=False,
    )
