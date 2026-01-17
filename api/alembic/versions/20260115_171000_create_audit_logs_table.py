"""Create audit_logs table

Comprehensive audit logging table for tracking:
- Entity mutations (create, update, delete)
- Password views (sensitive access)
- Auth events (login, logout, failed login)
- User management events

Revision ID: 20260115_171000
Revises: 20260115_170000
Create Date: 2026-01-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260115_171000"
down_revision: str | None = "20260115_170000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),

        # What happened
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),

        # Who did it
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_api_key_id", sa.UUID(), sa.ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_label", sa.String(100), nullable=True),

        # When
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),

        # Constraint: valid actor based on type
        sa.CheckConstraint(
            "(actor_type = 'user' AND actor_user_id IS NOT NULL) OR "
            "(actor_type = 'api_key' AND actor_api_key_id IS NOT NULL) OR "
            "(actor_type = 'system')",
            name="valid_actor",
        ),
    )

    # Indexes for common query patterns
    op.create_index(
        "ix_audit_logs_org_created",
        "audit_logs",
        ["organization_id", sa.text("created_at DESC")],
        postgresql_where=sa.text("organization_id IS NOT NULL"),
    )
    op.create_index(
        "ix_audit_logs_system_created",
        "audit_logs",
        [sa.text("created_at DESC")],
        postgresql_where=sa.text("organization_id IS NULL"),
    )
    op.create_index(
        "ix_audit_logs_entity",
        "audit_logs",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "ix_audit_logs_actor_user",
        "audit_logs",
        ["actor_user_id"],
        postgresql_where=sa.text("actor_user_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_actor_user", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_index("ix_audit_logs_system_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_org_created", table_name="audit_logs")
    op.drop_table("audit_logs")
