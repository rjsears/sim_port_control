# backend/app/models/discovered_port.py
"""
Discovered port model for tracking switch ports found during scanning.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.port_assignment import PortAssignment
    from app.models.switch import Switch

DiscoveredPortStatus = Literal["available", "assigned", "error", "in_use"]


class DiscoveredPort(Base):
    """A port discovered on a switch during scanning."""

    __tablename__ = "discovered_ports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    switch_id: Mapped[int] = mapped_column(
        ForeignKey("switches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    port_name: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g., "GigabitEthernet1/0/7"
    short_name: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "Gi1/0/7"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="available")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    switch: Mapped["Switch"] = relationship("Switch", back_populates="discovered_ports")
    port_assignment: Mapped["PortAssignment | None"] = relationship(
        "PortAssignment", back_populates="discovered_port", uselist=False
    )

    @property
    def is_available(self) -> bool:
        """Check if port can be assigned."""
        return self.status == "available"

    @property
    def is_assigned(self) -> bool:
        """Check if port is assigned to a simulator."""
        return self.status == "assigned"

    def __repr__(self) -> str:
        return f"<DiscoveredPort(id={self.id}, port='{self.short_name}', status='{self.status}')>"
