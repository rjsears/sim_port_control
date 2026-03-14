# =============================================================================
# Port Assignment Model
# =============================================================================
"""
Port assignment model linking simulators to switch ports.
Tracks current state and timeout configuration.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.activity_log import ActivityLog
    from app.models.discovered_port import DiscoveredPort
    from app.models.simulator import Simulator
    from app.models.switch import Switch
    from app.models.user import User

PortStatus = Literal["enabled", "disabled"]


class PortAssignment(Base):
    """Assignment of a switch port to a simulator."""

    __tablename__ = "port_assignments"
    __table_args__ = (UniqueConstraint("switch_id", "port_number", name="uq_switch_port"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    simulator_id: Mapped[int] = mapped_column(
        ForeignKey("simulators.id", ondelete="CASCADE"), nullable=False, index=True
    )
    switch_id: Mapped[int] = mapped_column(
        ForeignKey("switches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    discovered_port_id: Mapped[int | None] = mapped_column(
        ForeignKey("discovered_ports.id", ondelete="SET NULL"), nullable=True, index=True
    )
    port_number: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "Gi0/1"
    vlan: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    timeout_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=4)

    # Current state
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="disabled")
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auto_disable_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enabled_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Force-enabled (maintenance mode) - bypasses auto-disable
    force_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    force_enabled_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    force_enabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    force_enabled_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    simulator: Mapped["Simulator"] = relationship("Simulator", back_populates="port_assignments")
    switch: Mapped["Switch"] = relationship("Switch", back_populates="port_assignments")
    enabled_by: Mapped["User | None"] = relationship("User", foreign_keys=[enabled_by_user_id])
    force_enabled_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[force_enabled_by_id]
    )
    activity_logs: Mapped[list["ActivityLog"]] = relationship(
        "ActivityLog", back_populates="port_assignment"
    )
    discovered_port: Mapped["DiscoveredPort | None"] = relationship(
        "DiscoveredPort", back_populates="port_assignment"
    )

    @property
    def is_enabled(self) -> bool:
        """Check if port is currently enabled."""
        return self.status == "enabled"

    @property
    def seconds_remaining(self) -> int | None:
        """Calculate seconds until auto-disable, or None if disabled."""
        if not self.is_enabled or not self.auto_disable_at:
            return None
        remaining = (
            self.auto_disable_at - datetime.now(self.auto_disable_at.tzinfo)
        ).total_seconds()
        return max(0, int(remaining))

    @property
    def full_port_name(self) -> str:
        """Get full port identifier including switch name."""
        return f"{self.switch.name}:{self.port_number}"

    def __repr__(self) -> str:
        return (
            f"<PortAssignment(id={self.id}, simulator='{self.simulator_id}', "
            f"port='{self.port_number}', status='{self.status}')>"
        )
