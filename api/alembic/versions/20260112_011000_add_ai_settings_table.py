"""Add ai_settings table for OpenAI configuration

Revision ID: 011
Revises: 010
Create Date: 2026-01-12 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create ai_settings table (singleton - one row for platform config)
    op.create_table(
        "ai_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "openai_api_key",
            sa.Text(),
            nullable=True,
            comment="OpenAI API key (encrypted at database level)",
        ),
        sa.Column(
            "openai_model",
            sa.String(length=100),
            nullable=False,
            server_default="gpt-4o-mini",
            comment="OpenAI chat model to use",
        ),
        sa.Column(
            "embeddings_model",
            sa.String(length=100),
            nullable=False,
            server_default="text-embedding-3-small",
            comment="OpenAI embeddings model to use",
        ),
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
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ai_settings")
