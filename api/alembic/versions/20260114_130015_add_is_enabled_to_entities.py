"""Add is_enabled column to entities

This migration adds an is_enabled column to support archived/disabled entities
from IT Glue migration. This is Phase 1 of a larger feature to soft-delete
entities rather than hard-deleting them.

Changes:
1. Add is_enabled column to organizations (Boolean, NOT NULL, DEFAULT true)
2. Add is_enabled column to configurations (Boolean, NOT NULL, DEFAULT true)
3. Add is_enabled column to documents (Boolean, NOT NULL, DEFAULT true)
4. Add is_enabled column to locations (Boolean, NOT NULL, DEFAULT true)
5. Add is_enabled column to passwords (Boolean, NOT NULL, DEFAULT true)
6. Add is_enabled column to custom_assets (Boolean, NOT NULL, DEFAULT true)
7. Create partial indexes on is_enabled = false for all 6 tables

Revision ID: 9af382cc87c4
Revises: 020
Create Date: 2026-01-14 13:00:15.017680+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9af382cc87c4"
down_revision: str | None = "020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ==========================================================================
    # Add is_enabled column to all tables
    # ==========================================================================

    op.add_column(
        "organizations",
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "configurations",
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "documents",
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "locations",
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "passwords",
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "custom_assets",
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )

    # ==========================================================================
    # Create partial indexes for disabled entities (is_enabled = false)
    # ==========================================================================

    op.create_index(
        "ix_organizations_is_enabled",
        "organizations",
        ["is_enabled"],
        postgresql_where=sa.text("is_enabled = false"),
    )
    op.create_index(
        "ix_configurations_is_enabled",
        "configurations",
        ["is_enabled"],
        postgresql_where=sa.text("is_enabled = false"),
    )
    op.create_index(
        "ix_documents_is_enabled",
        "documents",
        ["is_enabled"],
        postgresql_where=sa.text("is_enabled = false"),
    )
    op.create_index(
        "ix_locations_is_enabled",
        "locations",
        ["is_enabled"],
        postgresql_where=sa.text("is_enabled = false"),
    )
    op.create_index(
        "ix_passwords_is_enabled",
        "passwords",
        ["is_enabled"],
        postgresql_where=sa.text("is_enabled = false"),
    )
    op.create_index(
        "ix_custom_assets_is_enabled",
        "custom_assets",
        ["is_enabled"],
        postgresql_where=sa.text("is_enabled = false"),
    )


def downgrade() -> None:
    # ==========================================================================
    # Drop partial indexes
    # ==========================================================================

    op.drop_index("ix_custom_assets_is_enabled", table_name="custom_assets")
    op.drop_index("ix_passwords_is_enabled", table_name="passwords")
    op.drop_index("ix_locations_is_enabled", table_name="locations")
    op.drop_index("ix_documents_is_enabled", table_name="documents")
    op.drop_index("ix_configurations_is_enabled", table_name="configurations")
    op.drop_index("ix_organizations_is_enabled", table_name="organizations")

    # ==========================================================================
    # Drop is_enabled columns
    # ==========================================================================

    op.drop_column("custom_assets", "is_enabled")
    op.drop_column("passwords", "is_enabled")
    op.drop_column("locations", "is_enabled")
    op.drop_column("documents", "is_enabled")
    op.drop_column("configurations", "is_enabled")
    op.drop_column("organizations", "is_enabled")
