"""Add interfaces JSONB column to configurations for network interface data

Revision ID: 019
Revises: 018
Create Date: 2026-01-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "019"
down_revision: str | None = "018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "configurations",
        sa.Column("interfaces", JSONB, nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("configurations", "interfaces")
