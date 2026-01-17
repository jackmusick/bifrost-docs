"""Add passwords table

Revision ID: 002
Revises: 001
Create Date: 2026-01-12 00:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Passwords table
    op.create_table(
        "passwords",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("password_encrypted", sa.Text(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_passwords_organization_id", "passwords", ["organization_id"], unique=False)
    op.create_index("ix_passwords_name", "passwords", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_passwords_name", table_name="passwords")
    op.drop_index("ix_passwords_organization_id", table_name="passwords")
    op.drop_table("passwords")
