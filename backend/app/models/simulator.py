# =============================================================================
# Simulator Model
# =============================================================================
"""
Flight simulator model representing devices that need network access control.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.activity_log import ActivityLog
    from app.models.port_assignment import PortAssignment
    from app.models.user import UserSimulatorAssignment


class Simulator(Base):
    """Flight simulator or FTD requiring network access control."""

    __tablename__ = "simulators"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    short_name: Mapped[str] = mapped_column(String(20), nullable=False)
    icon_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    port_assignments: Mapped[list["PortAssignment"]] = relationship(
        "PortAssignment", back_populates="simulator", cascade="all, delete-orphan"
    )
    user_assignments: Mapped[list["UserSimulatorAssignment"]] = relationship(
        "UserSimulatorAssignment", back_populates="simulator", cascade="all, delete-orphan"
    )
    activity_logs: Mapped[list["ActivityLog"]] = relationship(
        "ActivityLog", back_populates="simulator"
    )

    @property
    def has_active_ports(self) -> bool:
        """Check if any port is currently enabled."""
        return any(port.status == "enabled" for port in self.port_assignments)

    @property
    def active_port_count(self) -> int:
        """Count of currently enabled ports."""
        return sum(1 for port in self.port_assignments if port.status == "enabled")

    def __repr__(self) -> str:
        return f"<Simulator(id={self.id}, name='{self.name}', short_name='{self.short_name}')>"
