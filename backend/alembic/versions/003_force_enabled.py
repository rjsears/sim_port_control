# =============================================================================
# Migration: Add force_enabled fields to port_assignments
# =============================================================================
"""
Add force_enabled, force_enabled_by_id, force_enabled_at, force_enabled_reason
to port_assignments table for maintenance mode functionality.

Revision ID: 003
Revises: 002
Create Date: 2026-03-12
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add force_enabled columns."""
    op.add_column(
        "port_assignments",
        sa.Column("force_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "port_assignments",
        sa.Column("force_enabled_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "port_assignments",
        sa.Column("force_enabled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "port_assignments",
        sa.Column("force_enabled_reason", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    """Remove force_enabled columns."""
    op.drop_column("port_assignments", "force_enabled_reason")
    op.drop_column("port_assignments", "force_enabled_at")
    op.drop_column("port_assignments", "force_enabled_by_id")
    op.drop_column("port_assignments", "force_enabled")
