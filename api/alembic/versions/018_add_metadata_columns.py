"""Add metadata JSONB columns to entities for external system tracking

Revision ID: 018
Revises: 017
Create Date: 2026-01-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "018"
down_revision: str | None = "017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add metadata column to organizations
    op.add_column(
        "organizations",
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index(
        "ix_organizations_metadata_itglue_id",
        "organizations",
        [sa.text("(metadata->>'itglue_id')")],
        postgresql_where=sa.text("metadata->>'itglue_id' IS NOT NULL"),
    )

    # Add metadata column to documents
    op.add_column(
        "documents",
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index(
        "ix_documents_metadata_itglue_id",
        "documents",
        [sa.text("(metadata->>'itglue_id')")],
        postgresql_where=sa.text("metadata->>'itglue_id' IS NOT NULL"),
    )

    # Add metadata column to configurations
    op.add_column(
        "configurations",
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index(
        "ix_configurations_metadata_itglue_id",
        "configurations",
        [sa.text("(metadata->>'itglue_id')")],
        postgresql_where=sa.text("metadata->>'itglue_id' IS NOT NULL"),
    )

    # Add metadata column to passwords
    op.add_column(
        "passwords",
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index(
        "ix_passwords_metadata_itglue_id",
        "passwords",
        [sa.text("(metadata->>'itglue_id')")],
        postgresql_where=sa.text("metadata->>'itglue_id' IS NOT NULL"),
    )

    # Add metadata column to locations
    op.add_column(
        "locations",
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index(
        "ix_locations_metadata_itglue_id",
        "locations",
        [sa.text("(metadata->>'itglue_id')")],
        postgresql_where=sa.text("metadata->>'itglue_id' IS NOT NULL"),
    )

    # Add metadata column to custom_assets
    op.add_column(
        "custom_assets",
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index(
        "ix_custom_assets_metadata_itglue_id",
        "custom_assets",
        [sa.text("(metadata->>'itglue_id')")],
        postgresql_where=sa.text("metadata->>'itglue_id' IS NOT NULL"),
    )


def downgrade() -> None:
    # Drop indexes and columns in reverse order
    op.drop_index("ix_custom_assets_metadata_itglue_id", table_name="custom_assets")
    op.drop_column("custom_assets", "metadata")

    op.drop_index("ix_locations_metadata_itglue_id", table_name="locations")
    op.drop_column("locations", "metadata")

    op.drop_index("ix_passwords_metadata_itglue_id", table_name="passwords")
    op.drop_column("passwords", "metadata")

    op.drop_index("ix_configurations_metadata_itglue_id", table_name="configurations")
    op.drop_column("configurations", "metadata")

    op.drop_index("ix_documents_metadata_itglue_id", table_name="documents")
    op.drop_column("documents", "metadata")

    op.drop_index("ix_organizations_metadata_itglue_id", table_name="organizations")
    op.drop_column("organizations", "metadata")
