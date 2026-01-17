"""Add custom assets tables

Revision ID: 006
Revises: 001
Create Date: 2026-01-12 06:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Custom Asset Types table
    op.create_table(
        "custom_asset_types",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("fields", postgresql.JSONB(), server_default="[]", nullable=False),
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
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_custom_asset_types_organization_id",
        "custom_asset_types",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_custom_asset_types_name",
        "custom_asset_types",
        ["name"],
        unique=False,
    )

    # Custom Assets table
    op.create_table(
        "custom_assets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("custom_asset_type_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("values", postgresql.JSONB(), server_default="{}", nullable=False),
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
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["custom_asset_type_id"],
            ["custom_asset_types.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_custom_assets_organization_id",
        "custom_assets",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_custom_assets_custom_asset_type_id",
        "custom_assets",
        ["custom_asset_type_id"],
        unique=False,
    )
    op.create_index(
        "ix_custom_assets_name",
        "custom_assets",
        ["name"],
        unique=False,
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("custom_assets")
    op.drop_table("custom_asset_types")
