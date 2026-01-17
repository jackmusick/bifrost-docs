"""Remove user-organization scoping

This migration removes the user-organization junction table and the organization_id
column from api_keys, as part of Phase 1 of removing user-org scoping.

Changes:
1. Drops foreign key constraint api_keys_organization_id_fkey from api_keys
2. Drops index ix_api_keys_organization_id from api_keys
3. Drops column organization_id from api_keys
4. Drops table user_organizations

Revision ID: 020
Revises: 019
Create Date: 2026-01-13 00:50:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "020"
down_revision: str | None = "019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ==========================================================================
    # api_keys - remove organization_id column
    # ==========================================================================

    # Drop the organization_id index
    op.drop_index("ix_api_keys_organization_id", table_name="api_keys")

    # Drop the foreign key constraint
    op.drop_constraint(
        "api_keys_organization_id_fkey",
        "api_keys",
        type_="foreignkey",
    )

    # Drop the organization_id column
    op.drop_column("api_keys", "organization_id")

    # ==========================================================================
    # user_organizations - drop the junction table
    # ==========================================================================

    op.drop_table("user_organizations")


def downgrade() -> None:
    # ==========================================================================
    # user_organizations - recreate the junction table
    # ==========================================================================

    op.create_table(
        "user_organizations",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "organization_id"),
    )
    op.create_index("ix_user_organizations_user_id", "user_organizations", ["user_id"], unique=False)
    op.create_index(
        "ix_user_organizations_organization_id",
        "user_organizations",
        ["organization_id"],
        unique=False,
    )

    # ==========================================================================
    # api_keys - restore organization_id column
    # ==========================================================================

    # Add back the organization_id column (nullable for existing data)
    op.add_column(
        "api_keys",
        sa.Column("organization_id", sa.UUID(), nullable=True),
    )

    # Add back the foreign key constraint
    op.create_foreign_key(
        "api_keys_organization_id_fkey",
        "api_keys",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Add back the index
    op.create_index(
        "ix_api_keys_organization_id",
        "api_keys",
        ["organization_id"],
        unique=False,
    )
