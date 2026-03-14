# =============================================================================
# User Model
# =============================================================================
"""
User model for authentication and authorization.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.activity_log import ActivityLog
    from app.models.simulator import Simulator

UserRole = Literal["admin", "simtech"]


class User(Base):
    """User account for system access."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="simtech")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    simulator_assignments: Mapped[list["UserSimulatorAssignment"]] = relationship(
        "UserSimulatorAssignment", back_populates="user", cascade="all, delete-orphan"
    )
    activity_logs: Mapped[list["ActivityLog"]] = relationship("ActivityLog", back_populates="user")

    @property
    def assigned_simulators(self) -> list["Simulator"]:
        """Get list of simulators assigned to this user."""
        return [assignment.simulator for assignment in self.simulator_assignments]

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == "admin"

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class UserSimulatorAssignment(Base):
    """Association table for user-simulator assignments."""

    __tablename__ = "user_simulator_assignments"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    simulator_id: Mapped[int] = mapped_column(
        ForeignKey("simulators.id", ondelete="CASCADE"), primary_key=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="simulator_assignments")
    simulator: Mapped["Simulator"] = relationship("Simulator", back_populates="user_assignments")

    def __repr__(self) -> str:
        return (
            f"<UserSimulatorAssignment(user_id={self.user_id}, simulator_id={self.simulator_id})>"
        )
