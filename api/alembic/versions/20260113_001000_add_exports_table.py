"""Add exports table for data export tracking

Revision ID: 014
Revises: 013
Create Date: 2026-01-13 00:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Exports table for tracking data export jobs
    op.create_table(
        "exports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("organization_ids", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("s3_key", sa.String(length=500), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_exports_user_id", "exports", ["user_id"], unique=False)
    op.create_index("ix_exports_status", "exports", ["status"], unique=False)
    op.create_index("ix_exports_created_at", "exports", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_exports_created_at", table_name="exports")
    op.drop_index("ix_exports_status", table_name="exports")
    op.drop_index("ix_exports_user_id", table_name="exports")
    op.drop_table("exports")
