"""Add user role enum and migrate from is_superuser/user_type

Revision ID: 013
Revises: 012
Create Date: 2026-01-13 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create the enum type
    op.execute("CREATE TYPE user_role AS ENUM ('owner', 'administrator', 'contributor', 'reader')")

    # Add role column with default
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.Enum("owner", "administrator", "contributor", "reader", name="user_role", create_type=False),
            nullable=False,
            server_default="contributor",
        ),
    )

    # Migrate existing data: is_superuser=True -> owner, else contributor
    op.execute("""
        UPDATE users
        SET role = CASE
            WHEN is_superuser = true THEN 'owner'::user_role
            ELSE 'contributor'::user_role
        END
    """)

    # Drop old columns
    op.drop_column("users", "is_superuser")
    op.drop_column("users", "user_type")

    # Drop old enum if exists
    op.execute("DROP TYPE IF EXISTS user_type")


def downgrade() -> None:
    # Re-create old enum
    op.execute("CREATE TYPE user_type AS ENUM ('PLATFORM', 'ORG')")

    # Re-create old columns
    op.add_column(
        "users",
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "users",
        sa.Column(
            "user_type",
            sa.Enum("PLATFORM", "ORG", name="user_type", create_type=False),
            nullable=False,
            server_default="ORG",
        ),
    )

    # Migrate back: owner -> is_superuser=true, PLATFORM
    op.execute("""
        UPDATE users
        SET is_superuser = (role = 'owner'),
            user_type = CASE WHEN role = 'owner' THEN 'PLATFORM'::user_type ELSE 'ORG'::user_type END
    """)

    # Drop role column and enum
    op.drop_column("users", "role")
    op.execute("DROP TYPE user_role")
