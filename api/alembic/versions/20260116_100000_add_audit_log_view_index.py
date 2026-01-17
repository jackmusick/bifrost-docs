"""Add audit log view index for recent/frequent access queries.

This partial index speeds up queries that filter by user and action='view',
which is the pattern used by the AccessTrackingRepository for:
- Recent items viewed by a user
- Frequently viewed items

Revision ID: 20260116_100000
Revises: 20260115_171000
Create Date: 2026-01-16
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260116_100000"
down_revision: str | None = "20260115_171000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX idx_audit_logs_user_views
        ON audit_logs (actor_user_id, action, created_at DESC)
        WHERE action = 'view'
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_audit_logs_user_views")
