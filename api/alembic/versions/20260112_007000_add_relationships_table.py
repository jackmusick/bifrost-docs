"""Add relationships table

Revision ID: 007
Revises: 001
Create Date: 2026-01-12 07:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Relationships table
    op.create_table(
        "relationships",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column(
            "source_type",
            sa.String(length=50),
            nullable=False,
            comment="Entity type: password, configuration, location, document, custom_asset",
        ),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column(
            "target_type",
            sa.String(length=50),
            nullable=False,
            comment="Entity type: password, configuration, location, document, custom_asset",
        ),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
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
        sa.UniqueConstraint(
            "source_type",
            "source_id",
            "target_type",
            "target_id",
            name="uq_relationships_source_target",
        ),
    )
    op.create_index(
        "ix_relationships_organization_id",
        "relationships",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_relationships_source",
        "relationships",
        ["source_type", "source_id"],
        unique=False,
    )
    op.create_index(
        "ix_relationships_target",
        "relationships",
        ["target_type", "target_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("relationships")
