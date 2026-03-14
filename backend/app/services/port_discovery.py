# backend/app/services/port_discovery.py
"""
Port discovery service for scanning switches and managing discovered ports.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.activity_log import ActivityLog
from app.models.discovered_port import DiscoveredPort
from app.models.port_assignment import PortAssignment
from app.models.simulator import Simulator
from app.models.switch import Switch
from app.services.cisco_ssh import CiscoSSHError, CiscoSSHService

logger = logging.getLogger(__name__)


class PortDiscoveryError(Exception):
    """Exception for port discovery operations."""

    pass


class PortDiscoveryService:
    """Service for discovering and managing switch ports."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize service with database session."""
        self.db = db

    async def get_switch(self, switch_id: int) -> Switch | None:
        """Get switch by ID with discovered ports."""
        result = await self.db.execute(
            select(Switch)
            .where(Switch.id == switch_id)
            .options(selectinload(Switch.discovered_ports))
        )
        return result.scalar_one_or_none()

    async def scan_switch(self, switch_id: int) -> dict:
        """
        Scan a switch for available ports.

        Args:
            switch_id: ID of the switch to scan.

        Returns:
            Dict with scan results.
        """
        switch = await self.get_switch(switch_id)
        if not switch:
            return {
                "success": False,
                "message": "Switch not found",
                "ports_found": 0,
                "new_ports": 0,
                "removed_ports": 0,
            }

        try:
            ssh_service = CiscoSSHService(switch)
            discovered = await ssh_service.discover_ports_async()
        except CiscoSSHError as e:
            logger.error(f"SSH error scanning switch {switch.name}: {e}")
            return {
                "success": False,
                "message": str(e),
                "ports_found": 0,
                "new_ports": 0,
                "removed_ports": 0,
            }

        # Get existing discovered ports for this switch
        existing_ports = {p.short_name: p for p in switch.discovered_ports}
        discovered_names = {p["short_name"] for p in discovered}

        new_count = 0
        removed_count = 0

        # Add new ports
        for port_data in discovered:
            if port_data["short_name"] not in existing_ports:
                new_port = DiscoveredPort(
                    switch_id=switch_id,
                    port_name=port_data["port_name"],
                    short_name=port_data["short_name"],
                    description=port_data["description"],
                    status="available",
                    discovered_at=datetime.now(UTC),
                    last_verified_at=datetime.now(UTC),
                )
                self.db.add(new_port)
                new_count += 1
                logger.info(f"Discovered new port: {port_data['short_name']} on {switch.name}")
            else:
                # Update existing port
                existing = existing_ports[port_data["short_name"]]
                if existing.status == "available":
                    existing.description = port_data["description"]
                    existing.last_verified_at = datetime.now(UTC)

        # Mark ports that disappeared as error (if they were available)
        for short_name, port in existing_ports.items():
            if short_name not in discovered_names and port.status == "available":
                port.status = "error"
                port.error_message = "Port not found during scan"
                removed_count += 1
                logger.warning(f"Port {short_name} not found on {switch.name}")

        await self.db.commit()

        return {
            "success": True,
            "message": f"Scan complete. Found {len(discovered)} available ports.",
            "ports_found": len(discovered),
            "new_ports": new_count,
            "removed_ports": removed_count,
        }

    async def get_discovered_ports(
        self, switch_id: int | None = None, status: str | None = None
    ) -> list[DiscoveredPort]:
        """Get discovered ports, optionally filtered."""
        query = select(DiscoveredPort).options(
            selectinload(DiscoveredPort.switch),
            selectinload(DiscoveredPort.port_assignment).selectinload(PortAssignment.simulator),
        )

        if switch_id:
            query = query.where(DiscoveredPort.switch_id == switch_id)
        if status:
            query = query.where(DiscoveredPort.status == status)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def assign_port(
        self,
        discovered_port_id: int,
        simulator_id: int,
        vlan: int,
        timeout_hours: int,
        user_id: int,
    ) -> dict:
        """
        Assign a discovered port to a simulator.

        Args:
            discovered_port_id: ID of the discovered port.
            simulator_id: ID of the simulator to assign to.
            vlan: VLAN ID.
            timeout_hours: Default timeout in hours.
            user_id: ID of user performing the action.

        Returns:
            Dict with assignment result.
        """
        # Get discovered port
        result = await self.db.execute(
            select(DiscoveredPort)
            .where(DiscoveredPort.id == discovered_port_id)
            .options(selectinload(DiscoveredPort.switch))
        )
        discovered_port = result.scalar_one_or_none()

        if not discovered_port:
            return {"success": False, "message": "Port not found", "port_id": None}

        if discovered_port.status != "available":
            return {
                "success": False,
                "message": f"Port is not available (status: {discovered_port.status})",
                "port_id": None,
            }

        # Get simulator
        result = await self.db.execute(select(Simulator).where(Simulator.id == simulator_id))
        simulator = result.scalar_one_or_none()

        if not simulator:
            return {"success": False, "message": "Simulator not found", "port_id": None}

        # Configure port on switch
        try:
            ssh_service = CiscoSSHService(discovered_port.switch)
            await ssh_service.configure_port_assign_async(
                discovered_port.short_name, simulator.short_name, vlan
            )
        except CiscoSSHError as e:
            logger.error(f"Failed to configure port: {e}")
            return {"success": False, "message": f"SSH error: {e}", "port_id": None}

        # Verify configuration - port should still be admin down but with correct description
        try:
            state = await ssh_service.verify_port_state_async(discovered_port.short_name)
            expected_desc = f"SIMPORT:{simulator.short_name}"

            # Port should remain admin down after assignment (user enables explicitly)
            if not state["is_admin_down"]:
                logger.warning(
                    f"Port {discovered_port.short_name} unexpectedly up after assignment"
                )

            if state["description"] != expected_desc:
                logger.warning(
                    f"Description mismatch: expected '{expected_desc}', got '{state['description']}'"
                )
        except CiscoSSHError as e:
            logger.error(f"Verification failed: {e}")
            discovered_port.status = "error"
            discovered_port.error_message = f"Verification failed: {e}"
            await self.db.commit()
            return {"success": False, "message": f"Verification failed: {e}", "port_id": None}

        # Create port assignment - starts disabled, user enables when needed
        port_assignment = PortAssignment(
            simulator_id=simulator_id,
            switch_id=discovered_port.switch_id,
            discovered_port_id=discovered_port_id,
            port_number=discovered_port.short_name,
            vlan=vlan,
            timeout_hours=timeout_hours,
            status="disabled",  # User enables explicitly
        )
        self.db.add(port_assignment)

        # Update discovered port status
        discovered_port.status = "assigned"
        discovered_port.last_verified_at = datetime.now(UTC)
        discovered_port.error_message = None

        # Log activity
        log_entry = ActivityLog(
            user_id=user_id,
            simulator_id=simulator_id,
            action="port_assigned",
            vlan=vlan,
            details={
                "port": discovered_port.short_name,
                "switch": discovered_port.switch.name,
            },
        )
        self.db.add(log_entry)

        await self.db.commit()
        await self.db.refresh(port_assignment)

        logger.info(f"Assigned port {discovered_port.short_name} to {simulator.name}")
        return {
            "success": True,
            "message": f"Port assigned to {simulator.name}",
            "port_id": port_assignment.id,
        }

    async def release_port(self, port_assignment_id: int, user_id: int | None = None) -> dict:
        """
        Release a port back to available.

        Args:
            port_assignment_id: ID of the port assignment to release.
            user_id: ID of user performing the action.

        Returns:
            Dict with release result.
        """
        # Get port assignment with related data
        result = await self.db.execute(
            select(PortAssignment)
            .where(PortAssignment.id == port_assignment_id)
            .options(
                selectinload(PortAssignment.switch),
                selectinload(PortAssignment.simulator),
                selectinload(PortAssignment.discovered_port),
            )
        )
        assignment = result.scalar_one_or_none()

        if not assignment:
            return {"success": False, "message": "Port assignment not found"}

        # Release port on switch
        try:
            ssh_service = CiscoSSHService(assignment.switch)
            await ssh_service.configure_port_release_async(assignment.port_number, assignment.vlan)
        except CiscoSSHError as e:
            logger.error(f"Failed to release port: {e}")
            return {"success": False, "message": f"SSH error: {e}"}

        # Verify release
        try:
            state = await ssh_service.verify_port_state_async(assignment.port_number)

            if not state["is_admin_down"]:
                if assignment.discovered_port:
                    assignment.discovered_port.status = "error"
                    assignment.discovered_port.error_message = "Port not admin down after release"
                await self.db.commit()
                return {"success": False, "message": "Verification failed: port not disabled"}

            if state["description"] != "Available":
                logger.warning(f"Description not reset: {state['description']}")
        except CiscoSSHError as e:
            logger.error(f"Verification failed: {e}")
            if assignment.discovered_port:
                assignment.discovered_port.status = "error"
                assignment.discovered_port.error_message = f"Verification failed: {e}"
            await self.db.commit()
            return {"success": False, "message": f"Verification failed: {e}"}

        # Update discovered port
        if assignment.discovered_port:
            assignment.discovered_port.status = "available"
            assignment.discovered_port.last_verified_at = datetime.now(UTC)
            assignment.discovered_port.error_message = None

        # Log activity
        log_entry = ActivityLog(
            user_id=user_id,
            simulator_id=assignment.simulator_id,
            action="port_released",
            vlan=assignment.vlan,
            details={
                "port": assignment.port_number,
                "switch": assignment.switch.name,
            },
        )
        self.db.add(log_entry)

        # Delete assignment
        await self.db.delete(assignment)
        await self.db.commit()

        logger.info(f"Released port {assignment.port_number}")
        return {"success": True, "message": "Port released to available"}
