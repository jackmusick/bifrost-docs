"""Add documents table

Revision ID: 002
Revises: 001
Create Date: 2026-01-12 00:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column(
            "path",
            sa.String(length=1024),
            nullable=False,
            comment="Virtual folder path, e.g., /Infrastructure/Network/Diagrams",
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
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
        "ix_documents_organization_id",
        "documents",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_documents_organization_path",
        "documents",
        ["organization_id", "path"],
        unique=False,
    )
    op.create_index(
        "ix_documents_name",
        "documents",
        ["name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_documents_name", table_name="documents")
    op.drop_index("ix_documents_organization_path", table_name="documents")
    op.drop_index("ix_documents_organization_id", table_name="documents")
    op.drop_table("documents")
