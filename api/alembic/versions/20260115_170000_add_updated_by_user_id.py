"""Add updated_by_user_id to core entities

Adds updated_by_user_id column (FK to users) to:
- documents
- passwords
- configurations
- locations
- custom_assets
- organizations

Revision ID: 20260115_170000
Revises: 0b2220bd70bb
Create Date: 2026-01-15

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260115_170000"
down_revision: str | None = "0b2220bd70bb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Core entities that need updated_by_user_id tracking
TABLES = [
    "documents",
    "passwords",
    "configurations",
    "locations",
    "custom_assets",
    "organizations",
]


def upgrade() -> None:
    # Add updated_by_user_id to all 6 core entities
    for table in TABLES:
        op.add_column(
            table,
            sa.Column(
                "updated_by_user_id",
                sa.UUID(),
                nullable=True,
            ),
        )
        op.create_foreign_key(
            f"fk_{table}_updated_by_user_id",
            table,
            "users",
            ["updated_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(
            f"ix_{table}_updated_by_user_id",
            table,
            ["updated_by_user_id"],
        )


def downgrade() -> None:
    for table in TABLES:
        op.drop_index(f"ix_{table}_updated_by_user_id", table_name=table)
        op.drop_constraint(f"fk_{table}_updated_by_user_id", table, type_="foreignkey")
        op.drop_column(table, "updated_by_user_id")
