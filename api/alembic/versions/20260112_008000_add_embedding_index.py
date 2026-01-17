"""Add embedding_index table for vector search

Revision ID: 008
Revises: 006
Create Date: 2026-01-12 08:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create embedding_index table
    op.create_table(
        "embedding_index",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column(
            "entity_type",
            sa.String(length=50),
            nullable=False,
            comment="Type of entity: password, configuration, location, document, custom_asset",
        ),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column(
            "content_hash",
            sa.String(length=32),
            nullable=False,
            comment="MD5 hash of searchable_text to detect changes",
        ),
        sa.Column(
            "embedding",
            Vector(1536),
            nullable=False,
        ),
        sa.Column(
            "searchable_text",
            sa.Text(),
            nullable=False,
            comment="The text that was embedded",
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
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "entity_id", name="uq_embedding_entity"),
    )

    # Create indexes
    op.create_index(
        "ix_embedding_index_organization_id",
        "embedding_index",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_embedding_index_entity_type",
        "embedding_index",
        ["entity_type"],
        unique=False,
    )

    # Create vector similarity index using ivfflat for cosine distance
    # Note: For production with large datasets, consider:
    # 1. Increasing lists parameter (sqrt(n_vectors) is a good starting point)
    # 2. Running ANALYZE on the table after initial load
    # 3. Rebuilding index periodically as data grows
    op.execute("""
        CREATE INDEX ix_embedding_index_embedding
        ON embedding_index
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_embedding_index_embedding")
    op.drop_index("ix_embedding_index_entity_type", table_name="embedding_index")
    op.drop_index("ix_embedding_index_organization_id", table_name="embedding_index")

    # Drop table
    op.drop_table("embedding_index")

    # Note: We don't drop the vector extension as other tables might use it
