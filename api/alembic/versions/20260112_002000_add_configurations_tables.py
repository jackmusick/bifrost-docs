"""Add configurations tables

Revision ID: 007
Revises: 006
Create Date: 2026-01-12 02:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Configuration Types table
    op.create_table(
        "configuration_types",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_configuration_types_organization_id",
        "configuration_types",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_configuration_types_name",
        "configuration_types",
        ["name"],
        unique=False,
    )

    # Configuration Statuses table
    op.create_table(
        "configuration_statuses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_configuration_statuses_organization_id",
        "configuration_statuses",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_configuration_statuses_name",
        "configuration_statuses",
        ["name"],
        unique=False,
    )

    # Configurations table
    op.create_table(
        "configurations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("configuration_type_id", sa.UUID(), nullable=True),
        sa.Column("configuration_status_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("serial_number", sa.String(length=255), nullable=True),
        sa.Column("asset_tag", sa.String(length=255), nullable=True),
        sa.Column("manufacturer", sa.String(length=255), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("mac_address", sa.String(length=17), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["configuration_type_id"],
            ["configuration_types.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["configuration_status_id"],
            ["configuration_statuses.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_configurations_organization_id",
        "configurations",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_configurations_configuration_type_id",
        "configurations",
        ["configuration_type_id"],
        unique=False,
    )
    op.create_index(
        "ix_configurations_configuration_status_id",
        "configurations",
        ["configuration_status_id"],
        unique=False,
    )
    op.create_index(
        "ix_configurations_name",
        "configurations",
        ["name"],
        unique=False,
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index("ix_configurations_name", table_name="configurations")
    op.drop_index("ix_configurations_configuration_status_id", table_name="configurations")
    op.drop_index("ix_configurations_configuration_type_id", table_name="configurations")
    op.drop_index("ix_configurations_organization_id", table_name="configurations")
    op.drop_table("configurations")

    op.drop_index("ix_configuration_statuses_name", table_name="configuration_statuses")
    op.drop_index("ix_configuration_statuses_organization_id", table_name="configuration_statuses")
    op.drop_table("configuration_statuses")

    op.drop_index("ix_configuration_types_name", table_name="configuration_types")
    op.drop_index("ix_configuration_types_organization_id", table_name="configuration_types")
    op.drop_table("configuration_types")
