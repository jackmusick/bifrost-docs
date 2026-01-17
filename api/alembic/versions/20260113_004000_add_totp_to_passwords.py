"""Add totp_secret_encrypted to passwords table

Revision ID: 017
Revises: 016
Create Date: 2026-01-13 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "017"
down_revision: str | None = "016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add totp_secret_encrypted column for storing encrypted TOTP secrets
    op.add_column(
        "passwords",
        sa.Column("totp_secret_encrypted", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("passwords", "totp_secret_encrypted")
