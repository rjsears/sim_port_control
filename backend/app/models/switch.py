# =============================================================================
# Switch Model
# =============================================================================
"""
Cisco switch model for network device management.
Credentials are encrypted using Fernet symmetric encryption.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.discovered_port import DiscoveredPort
    from app.models.port_assignment import PortAssignment


class Switch(Base):
    """Cisco network switch with SSH access credentials."""

    __tablename__ = "switches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)  # IPv4 or IPv6
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet encrypted
    device_type: Mapped[str] = mapped_column(String(50), nullable=False, default="cisco_ios")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    port_assignments: Mapped[list["PortAssignment"]] = relationship(
        "PortAssignment", back_populates="switch", cascade="all, delete-orphan"
    )
    discovered_ports: Mapped[list["DiscoveredPort"]] = relationship(
        "DiscoveredPort", back_populates="switch", cascade="all, delete-orphan"
    )

    @property
    def port_count(self) -> int:
        """Count of configured port assignments."""
        return len(self.port_assignments)

    def __repr__(self) -> str:
        return f"<Switch(id={self.id}, name='{self.name}', ip='{self.ip_address}')>"
