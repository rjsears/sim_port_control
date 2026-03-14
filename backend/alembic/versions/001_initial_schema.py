"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="simtech"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    # Simulators table
    op.create_table(
        "simulators",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("short_name", sa.String(length=20), nullable=False),
        sa.Column("icon_path", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Switches table
    op.create_table(
        "switches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_encrypted", sa.Text(), nullable=False),
        sa.Column("device_type", sa.String(length=50), nullable=False, server_default="cisco_ios"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # User-Simulator assignments
    op.create_table(
        "user_simulator_assignments",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("simulator_id", sa.Integer(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["simulator_id"], ["simulators.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "simulator_id"),
    )

    # Port assignments table
    op.create_table(
        "port_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("simulator_id", sa.Integer(), nullable=False),
        sa.Column("switch_id", sa.Integer(), nullable=False),
        sa.Column("port_number", sa.String(length=20), nullable=False),
        sa.Column("vlan", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("timeout_hours", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="disabled"),
        sa.Column("enabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_disable_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enabled_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["enabled_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["simulator_id"], ["simulators.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["switch_id"], ["switches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("switch_id", "port_number", name="uq_switch_port"),
    )
    op.create_index(
        op.f("ix_port_assignments_simulator_id"),
        "port_assignments",
        ["simulator_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_port_assignments_switch_id"),
        "port_assignments",
        ["switch_id"],
        unique=False,
    )

    # Activity logs table
    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("simulator_id", sa.Integer(), nullable=True),
        sa.Column("port_assignment_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("vlan", sa.Integer(), nullable=True),
        sa.Column("timeout_hours", sa.Integer(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["port_assignment_id"], ["port_assignments.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["simulator_id"], ["simulators.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_activity_logs_simulator_id"),
        "activity_logs",
        ["simulator_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_activity_logs_timestamp"),
        "activity_logs",
        ["timestamp"],
        unique=False,
    )
    op.create_index(op.f("ix_activity_logs_user_id"), "activity_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_activity_logs_user_id"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_timestamp"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_simulator_id"), table_name="activity_logs")
    op.drop_table("activity_logs")
    op.drop_index(op.f("ix_port_assignments_switch_id"), table_name="port_assignments")
    op.drop_index(op.f("ix_port_assignments_simulator_id"), table_name="port_assignments")
    op.drop_table("port_assignments")
    op.drop_table("user_simulator_assignments")
    op.drop_table("switches")
    op.drop_table("simulators")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")
