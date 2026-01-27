"""Clean up disabled entities from embedding_index

This data migration removes all disabled entities from the embedding_index table.
Going forward, only enabled entities are indexed - disabled entities are removed
from the index when they are disabled.

Revision ID: 20260126_001000
Revises: 20260115_171000
Create Date: 2026-01-26
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260126_001000"
down_revision: str | None = "20260116_100000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove disabled entities from the embedding_index.

    The embedding_index should only contain enabled entities. This migration
    cleans up any disabled entities that were indexed before this change.
    """
    # Delete documents that are disabled
    op.execute("""
        DELETE FROM embedding_index ei
        USING documents d
        WHERE ei.entity_type = 'document'
          AND ei.entity_id = d.id
          AND d.is_enabled = false
    """)

    # Delete passwords that are disabled
    op.execute("""
        DELETE FROM embedding_index ei
        USING passwords p
        WHERE ei.entity_type = 'password'
          AND ei.entity_id = p.id
          AND p.is_enabled = false
    """)

    # Delete configurations that are disabled
    op.execute("""
        DELETE FROM embedding_index ei
        USING configurations c
        WHERE ei.entity_type = 'configuration'
          AND ei.entity_id = c.id
          AND c.is_enabled = false
    """)

    # Delete locations that are disabled
    op.execute("""
        DELETE FROM embedding_index ei
        USING locations l
        WHERE ei.entity_type = 'location'
          AND ei.entity_id = l.id
          AND l.is_enabled = false
    """)

    # Delete custom_assets that are disabled
    op.execute("""
        DELETE FROM embedding_index ei
        USING custom_assets ca
        WHERE ei.entity_type = 'custom_asset'
          AND ei.entity_id = ca.id
          AND ca.is_enabled = false
    """)


def downgrade() -> None:
    """No-op: cannot restore deleted index entries.

    The index entries can be recreated by re-enabling the entities or
    running a full reindex. This downgrade is intentionally a no-op.
    """
    pass
