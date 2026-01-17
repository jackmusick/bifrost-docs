"""Add attachments table.

Revision ID: 20260112_005000
Revises: 20260112_000000
Create Date: 2026-01-12

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create attachments table."""
    op.create_table(
        "attachments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("s3_key", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
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
        sa.UniqueConstraint("s3_key"),
    )

    # Create indexes for efficient queries
    op.create_index(
        "ix_attachments_organization_id",
        "attachments",
        ["organization_id"],
    )
    op.create_index(
        "ix_attachments_entity",
        "attachments",
        ["organization_id", "entity_type", "entity_id"],
    )
    op.create_index(
        "ix_attachments_s3_key",
        "attachments",
        ["s3_key"],
    )


def downgrade() -> None:
    """Drop attachments table."""
    op.drop_index("ix_attachments_s3_key", table_name="attachments")
    op.drop_index("ix_attachments_entity", table_name="attachments")
    op.drop_index("ix_attachments_organization_id", table_name="attachments")
    op.drop_table("attachments")
