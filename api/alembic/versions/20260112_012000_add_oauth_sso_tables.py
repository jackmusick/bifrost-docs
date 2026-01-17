"""Add OAuth SSO tables

Revision ID: 012
Revises: 011
Create Date: 2026-01-12 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create system_configs table for OAuth provider configuration
    op.create_table(
        "system_configs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value_json", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("value_bytes", sa.LargeBinary(), nullable=True),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
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
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for system_configs
    op.create_index(
        "ix_system_configs_category",
        "system_configs",
        ["category"],
    )
    op.create_index(
        "ix_system_configs_category_key",
        "system_configs",
        ["category", "key"],
    )
    op.create_index(
        "ix_system_configs_org_id",
        "system_configs",
        ["organization_id"],
    )

    # Create user_oauth_accounts table for linking OAuth accounts to users
    op.create_table(
        "user_oauth_accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "provider_id",
            sa.String(length=50),
            nullable=False,
            comment="OAuth provider name (microsoft, google, oidc)",
        ),
        sa.Column(
            "provider_user_id",
            sa.String(length=255),
            nullable=False,
            comment="User ID from the OAuth provider",
        ),
        sa.Column(
            "email",
            sa.String(length=320),
            nullable=False,
            comment="Email from OAuth provider",
        ),
        sa.Column(
            "last_login",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last successful login via this OAuth account",
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

    # Create indexes for user_oauth_accounts
    op.create_index(
        "ix_user_oauth_accounts_provider_user",
        "user_oauth_accounts",
        ["provider_id", "provider_user_id"],
        unique=True,
    )
    op.create_index(
        "ix_user_oauth_accounts_user_id",
        "user_oauth_accounts",
        ["user_id"],
    )


def downgrade() -> None:
    # Drop user_oauth_accounts table and indexes
    op.drop_index("ix_user_oauth_accounts_user_id", table_name="user_oauth_accounts")
    op.drop_index(
        "ix_user_oauth_accounts_provider_user", table_name="user_oauth_accounts"
    )
    op.drop_table("user_oauth_accounts")

    # Drop system_configs table and indexes
    op.drop_index("ix_system_configs_org_id", table_name="system_configs")
    op.drop_index("ix_system_configs_category_key", table_name="system_configs")
    op.drop_index("ix_system_configs_category", table_name="system_configs")
    op.drop_table("system_configs")
