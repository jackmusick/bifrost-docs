"""Initial auth tables

Revision ID: 001
Revises:
Create Date: 2026-01-12 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum types using raw SQL with DO block for IF NOT EXISTS
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE user_type AS ENUM ('PLATFORM', 'ORG');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE mfa_method_type AS ENUM ('totp');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE mfa_method_status AS ENUM ('pending', 'active', 'disabled');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Organizations table
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
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
    op.create_index("ix_organizations_name", "organizations", ["name"], unique=False)

    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("hashed_password", sa.String(length=1024), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, default=False),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "user_type",
            postgresql.ENUM("PLATFORM", "ORG", name="user_type", create_type=False),
            nullable=False,
            server_default="ORG",
        ),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("webauthn_user_id", sa.LargeBinary(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # User-Organization junction table
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

    # Sessions table
    op.create_table(
        "sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"], unique=False)
    op.create_index(
        "ix_sessions_refresh_token_hash", "sessions", ["refresh_token_hash"], unique=False
    )

    # User passkeys table
    op.create_table(
        "user_passkeys",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("credential_id", sa.LargeBinary(), nullable=False),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("sign_count", sa.Integer(), nullable=False, default=0),
        sa.Column("transports", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("device_type", sa.String(length=50), nullable=False),
        sa.Column("backed_up", sa.Boolean(), nullable=False, default=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("credential_id"),
    )
    op.create_index("ix_user_passkeys_user_id", "user_passkeys", ["user_id"], unique=False)
    op.create_index(
        "ix_user_passkeys_credential_id", "user_passkeys", ["credential_id"], unique=True
    )

    # User MFA methods table
    op.create_table(
        "user_mfa_methods",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "method_type",
            postgresql.ENUM("totp", name="mfa_method_type", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM("pending", "active", "disabled", name="mfa_method_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("encrypted_secret", sa.Text(), nullable=True),
        sa.Column("mfa_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("last_used_counter", sa.Integer(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_mfa_methods_user_id", "user_mfa_methods", ["user_id"], unique=False)
    op.create_index(
        "ix_user_mfa_methods_user_status", "user_mfa_methods", ["user_id", "status"], unique=False
    )

    # MFA recovery codes table
    op.create_table(
        "mfa_recovery_codes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, default=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_from_ip", sa.String(length=45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mfa_recovery_codes_user_id", "mfa_recovery_codes", ["user_id"], unique=False)
    op.create_index(
        "ix_mfa_recovery_codes_user_unused",
        "mfa_recovery_codes",
        ["user_id", "is_used"],
        unique=False,
    )

    # API keys table
    op.create_table(
        "api_keys",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"], unique=False)
    op.create_index("ix_api_keys_organization_id", "api_keys", ["organization_id"], unique=False)
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("api_keys")
    op.drop_table("mfa_recovery_codes")
    op.drop_table("user_mfa_methods")
    op.drop_table("user_passkeys")
    op.drop_table("sessions")
    op.drop_table("user_organizations")
    op.drop_table("users")
    op.drop_table("organizations")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS mfa_method_status")
    op.execute("DROP TYPE IF EXISTS mfa_method_type")
    op.execute("DROP TYPE IF EXISTS user_type")
