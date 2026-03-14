# backend/alembic/versions/002_discovered_ports.py
"""Add discovered_ports table and link to port_assignments.

Revision ID: 002
Revises: 001
Create Date: 2026-03-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovered_ports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("switch_id", sa.Integer(), nullable=False),
        sa.Column("port_name", sa.String(50), nullable=False),
        sa.Column("short_name", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="available"),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(["switch_id"], ["switches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_discovered_ports_switch_id", "discovered_ports", ["switch_id"])
    op.create_index("ix_discovered_ports_status", "discovered_ports", ["status"])

    op.add_column(
        "port_assignments",
        sa.Column("discovered_port_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_port_assignments_discovered_port",
        "port_assignments",
        "discovered_ports",
        ["discovered_port_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_port_assignments_discovered_port_id", "port_assignments", ["discovered_port_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_port_assignments_discovered_port_id", table_name="port_assignments")
    op.drop_constraint(
        "fk_port_assignments_discovered_port", "port_assignments", type_="foreignkey"
    )
    op.drop_column("port_assignments", "discovered_port_id")
    op.drop_index("ix_discovered_ports_status", table_name="discovered_ports")
    op.drop_index("ix_discovered_ports_switch_id", table_name="discovered_ports")
    op.drop_table("discovered_ports")
