# =============================================================================
# Port Control Service
# =============================================================================
"""
High-level service for port control operations.
Orchestrates database updates, SSH commands, and scheduling.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.activity_log import ActivityLog
from app.models.port_assignment import PortAssignment
from app.models.user import User
from app.services.cisco_ssh import CiscoSSHError, CiscoSSHService
from app.services.scheduler import get_scheduler_service

logger = logging.getLogger(__name__)


class PortControlError(Exception):
    """Exception for port control operations."""

    pass


class PortControlService:
    """Service for managing port enable/disable operations."""

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize service.

        Args:
            db: Database session.
        """
        self.db = db
        self.scheduler = get_scheduler_service()

    async def get_port_assignment(self, port_id: int) -> PortAssignment | None:
        """Get a port assignment by ID with related data."""
        result = await self.db.execute(
            select(PortAssignment)
            .where(PortAssignment.id == port_id)
            .options(
                selectinload(PortAssignment.switch),
                selectinload(PortAssignment.simulator),
                selectinload(PortAssignment.enabled_by),
            )
        )
        return result.scalar_one_or_none()

    async def enable_port(
        self,
        port: PortAssignment,
        user: User,
        timeout_hours: float | None = None,
        vlan: int | None = None,
    ) -> PortAssignment:
        """
        Enable a switch port.

        Args:
            port: Port assignment to enable.
            user: User performing the action.
            timeout_hours: Override default timeout (in hours).
            vlan: Override default VLAN.

        Returns:
            Updated port assignment.

        Raises:
            PortControlError: If operation fails.
        """
        # Use defaults if not specified
        timeout = timeout_hours or port.timeout_hours
        vlan_id = vlan or port.vlan

        logger.info(
            f"Enabling port {port.port_number} on {port.switch.name} "
            f"for {port.simulator.name} by {user.username}"
        )

        # Execute SSH command (async to avoid blocking event loop)
        try:
            ssh_service = CiscoSSHService(port.switch)
            await ssh_service.enable_port_async(port.port_number, vlan_id)
        except CiscoSSHError as e:
            logger.error(f"SSH error enabling port: {e}")
            raise PortControlError(f"Failed to enable port: {e}") from e

        # Update database
        now = datetime.now(UTC)
        auto_disable_at = now + timedelta(hours=timeout)

        port.status = "enabled"
        port.enabled_at = now
        port.auto_disable_at = auto_disable_at
        port.enabled_by_user_id = user.id
        port.vlan = vlan_id

        # Log activity
        log_entry = ActivityLog(
            user_id=user.id,
            simulator_id=port.simulator_id,
            port_assignment_id=port.id,
            action="enable",
            vlan=vlan_id,
            timeout_hours=timeout,
            details={
                "switch_name": port.switch.name,
                "port_number": port.port_number,
            },
        )
        self.db.add(log_entry)

        # Schedule auto-disable (unless force-enabled)
        if not port.force_enabled:
            self.scheduler.schedule_port_disable(port.id, auto_disable_at)
        else:
            logger.info(f"Port {port.id} is force-enabled, skipping auto-disable scheduling")

        try:
            await self.db.commit()
        except Exception as e:
            logger.critical(
                f"DATABASE COMMIT FAILED after SSH enable succeeded for port {port.id} "
                f"({port.switch.name}:{port.port_number}). Port may be in inconsistent state. "
                f"Manual verification required. Error: {e}"
            )
            raise PortControlError(
                f"Database update failed after port was enabled via SSH. "
                f"Port {port.port_number} may need manual verification."
            ) from e

        await self.db.refresh(port)

        logger.info(
            f"Port {port.port_number} enabled, auto-disable scheduled for {auto_disable_at}"
        )
        return port

    async def disable_port(
        self,
        port: PortAssignment,
        user: User | None = None,
        is_auto: bool = False,
    ) -> PortAssignment:
        """
        Disable a switch port.

        Args:
            port: Port assignment to disable.
            user: User performing the action (None for auto-disable).
            is_auto: Whether this is an automatic disable.

        Returns:
            Updated port assignment.

        Raises:
            PortControlError: If operation fails.
        """
        action = "timed_auto_disable" if is_auto else "disable"
        actor = "System" if is_auto else (user.username if user else "Unknown")

        logger.info(
            f"Disabling port {port.port_number} on {port.switch.name} "
            f"for {port.simulator.name} by {actor}"
        )

        # Execute SSH command (async to avoid blocking event loop)
        try:
            ssh_service = CiscoSSHService(port.switch)
            await ssh_service.disable_port_async(port.port_number)
        except CiscoSSHError as e:
            logger.error(f"SSH error disabling port: {e}")
            raise PortControlError(f"Failed to disable port: {e}") from e

        # Cancel any scheduled auto-disable
        self.scheduler.cancel_port_disable(port.id)

        # Update database
        port.status = "disabled"
        port.enabled_at = None
        port.auto_disable_at = None
        port.enabled_by_user_id = None
        # Clear force-enabled when disabling
        port.force_enabled = False
        port.force_enabled_by_id = None
        port.force_enabled_at = None
        port.force_enabled_reason = None

        # Log activity
        log_entry = ActivityLog(
            user_id=user.id if user else None,
            simulator_id=port.simulator_id,
            port_assignment_id=port.id,
            action=action,
            vlan=port.vlan,
            details={
                "switch_name": port.switch.name,
                "port_number": port.port_number,
                "is_auto": is_auto,
            },
        )
        self.db.add(log_entry)

        try:
            await self.db.commit()
        except Exception as e:
            logger.critical(
                f"DATABASE COMMIT FAILED after SSH disable succeeded for port {port.id} "
                f"({port.switch.name}:{port.port_number}). Port may be in inconsistent state. "
                f"Manual verification required. Error: {e}"
            )
            raise PortControlError(
                f"Database update failed after port was disabled via SSH. "
                f"Port {port.port_number} may need manual verification."
            ) from e

        await self.db.refresh(port)

        logger.info(f"Port {port.port_number} disabled")
        return port

    async def set_force_enabled(
        self,
        port: PortAssignment,
        user: User,
        enabled: bool,
        reason: str | None = None,
    ) -> PortAssignment:
        """
        Set or clear force-enabled (maintenance mode) on a port.

        Args:
            port: Port assignment to modify.
            user: Admin user performing the action.
            enabled: True to enable maintenance mode, False to disable.
            reason: Reason for force-enabling (required when enabled=True).

        Returns:
            Updated port assignment.
        """
        now = datetime.now(UTC)

        if enabled:
            logger.info(
                f"Force-enabling port {port.port_number} on {port.switch.name} "
                f"by {user.username}. Reason: {reason}"
            )

            # If port is not currently enabled, enable it on the switch first
            if port.status != "enabled":
                logger.info(f"Port is disabled, enabling via SSH before force-enable")
                try:
                    ssh_service = CiscoSSHService(port.switch)
                    await ssh_service.enable_port_async(port.port_number, port.vlan)
                    port.status = "enabled"
                    port.enabled_at = now
                    port.enabled_by_user_id = user.id
                except CiscoSSHError as e:
                    logger.error(f"SSH error enabling port for force-enable: {e}")
                    raise PortControlError(f"Failed to enable port: {e}") from e

            port.force_enabled = True
            port.force_enabled_by_id = user.id
            port.force_enabled_at = now
            port.force_enabled_reason = reason

            # Cancel any pending auto-disable
            self.scheduler.cancel_port_disable(port.id)

            # Log activity
            log_entry = ActivityLog(
                user_id=user.id,
                simulator_id=port.simulator_id,
                port_assignment_id=port.id,
                action="force_enable",
                vlan=port.vlan,
                details={
                    "switch_name": port.switch.name,
                    "port_number": port.port_number,
                    "reason": reason,
                },
            )
        else:
            logger.info(
                f"Clearing force-enabled on port {port.port_number} on {port.switch.name} "
                f"by {user.username}"
            )
            port.force_enabled = False
            port.force_enabled_by_id = None
            port.force_enabled_at = None
            port.force_enabled_reason = None

            # If port is still enabled, reschedule auto-disable
            if port.status == "enabled" and port.auto_disable_at:
                if port.auto_disable_at > now:
                    self.scheduler.schedule_port_disable(port.id, port.auto_disable_at)
                else:
                    # Auto-disable time has passed, schedule immediate disable
                    self.scheduler.schedule_port_disable(port.id, now + timedelta(seconds=5))

            # Log activity
            log_entry = ActivityLog(
                user_id=user.id,
                simulator_id=port.simulator_id,
                port_assignment_id=port.id,
                action="force_disable",
                vlan=port.vlan,
                details={
                    "switch_name": port.switch.name,
                    "port_number": port.port_number,
                },
            )

        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(port)

        return port

    async def check_user_access(self, user: User, port: PortAssignment) -> bool:
        """
        Check if a user has access to control a port.

        Args:
            user: User to check.
            port: Port assignment to check access for.

        Returns:
            True if user has access, False otherwise.
        """
        # Admins have access to all ports
        if user.is_admin:
            return True

        # SimTechs can only control assigned simulators
        assigned_ids = [sim.id for sim in user.assigned_simulators]
        return port.simulator_id in assigned_ids
