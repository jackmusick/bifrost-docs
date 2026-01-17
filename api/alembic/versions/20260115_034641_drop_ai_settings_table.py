"""Drop ai_settings table.

This migration removes the ai_settings table as part of the multi-provider LLM
support feature. LLM configuration is now stored in the system_configs table.

Revision ID: 0b2220bd70bb
Revises: 20260114_160000
Create Date: 2026-01-15 03:46:41.201615+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0b2220bd70bb'
down_revision: str | None = '20260114_160000'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("ai_settings")


def downgrade() -> None:
    # Recreate ai_settings table
    op.create_table(
        "ai_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("openai_api_key", sa.Text(), nullable=True),
        sa.Column("openai_model", sa.String(100), nullable=False, server_default="gpt-4o-mini"),
        sa.Column("embeddings_model", sa.String(100), nullable=False, server_default="text-embedding-3-small"),
        sa.Column("indexing_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
