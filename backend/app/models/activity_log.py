# =============================================================================
# Activity Log Model
# =============================================================================
"""
Activity log model for auditing port control actions.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.port_assignment import PortAssignment
    from app.models.simulator import Simulator
    from app.models.user import User

ActionType = Literal["enable", "disable", "auto_disable"]


class ActivityLog(Base):
    """Audit log entry for port control actions."""

    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    simulator_id: Mapped[int | None] = mapped_column(
        ForeignKey("simulators.id", ondelete="SET NULL"), nullable=True, index=True
    )
    port_assignment_id: Mapped[int | None] = mapped_column(
        ForeignKey("port_assignments.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # enable, disable, auto_disable
    vlan: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timeout_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )

    # Relationships
    user: Mapped["User | None"] = relationship("User", back_populates="activity_logs")
    simulator: Mapped["Simulator | None"] = relationship(
        "Simulator", back_populates="activity_logs"
    )
    port_assignment: Mapped["PortAssignment | None"] = relationship(
        "PortAssignment", back_populates="activity_logs"
    )

    @property
    def username(self) -> str:
        """Get username or 'System' for auto actions."""
        if self.user:
            return self.user.username
        return "System"

    @property
    def simulator_name(self) -> str | None:
        """Get simulator name if available."""
        if self.simulator:
            return self.simulator.name
        return None

    def __repr__(self) -> str:
        return (
            f"<ActivityLog(id={self.id}, action='{self.action}', "
            f"user='{self.username}', timestamp='{self.timestamp}')>"
        )
