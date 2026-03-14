# =============================================================================
# Cisco SSH Service
# =============================================================================
"""
Netmiko-based SSH service for controlling Cisco switch ports.

SSH operations are synchronous (Netmiko limitation) but can be run
in a thread pool for async compatibility.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)

from app.models.switch import Switch
from app.services.encryption import get_encryption_service

logger = logging.getLogger(__name__)

# Thread pool for SSH operations to avoid blocking the async event loop
_ssh_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ssh_worker")


class CiscoSSHError(Exception):
    """Base exception for Cisco SSH operations."""

    pass


class CiscoSSHService:
    """Service for SSH operations on Cisco switches."""

    def __init__(self, switch: Switch) -> None:
        """
        Initialize service with switch details.

        Args:
            switch: Switch model instance with connection details.
        """
        self.switch = switch
        self._encryption = get_encryption_service()

    def _get_device_params(self) -> dict[str, Any]:
        """Get Netmiko device connection parameters."""
        return {
            "device_type": self.switch.device_type,
            "host": self.switch.ip_address,
            "username": self.switch.username,
            "password": self._encryption.decrypt(self.switch.password_encrypted),
            "timeout": 30,
            "conn_timeout": 30,
        }

    def _connect(self) -> ConnectHandler:
        """
        Establish SSH connection to the switch.

        Returns:
            Netmiko ConnectHandler instance.

        Raises:
            CiscoSSHError: If connection fails.
        """
        try:
            logger.debug(f"Connecting to switch {self.switch.name} ({self.switch.ip_address})")
            return ConnectHandler(**self._get_device_params())
        except NetmikoAuthenticationException as e:
            logger.error(f"Authentication failed for switch {self.switch.name}: {e}")
            raise CiscoSSHError(f"Authentication failed: {e}") from e
        except NetmikoTimeoutException as e:
            logger.error(f"Connection timeout for switch {self.switch.name}: {e}")
            raise CiscoSSHError(f"Connection timeout: {e}") from e
        except Exception as e:
            logger.error(f"Connection error for switch {self.switch.name}: {e}")
            raise CiscoSSHError(f"Connection error: {e}") from e

    def test_connection(self) -> dict[str, Any]:
        """
        Test SSH connectivity and retrieve switch information.

        Returns:
            Dictionary with switch info (hostname, model, IOS version).

        Raises:
            CiscoSSHError: If connection or command fails.
        """
        try:
            with self._connect() as conn:
                # Get switch info
                output = conn.send_command("show version", use_textfsm=False)

                # Parse basic info from output
                info = {
                    "hostname": self.switch.name,
                    "connected": True,
                }

                # Try to extract model and version
                for line in output.split("\n"):
                    if "Model number" in line or "Model Number" in line:
                        info["model"] = line.split(":")[-1].strip()
                    elif (
                        "System image file" in line or "IOS" in line.upper()
                    ) and "version" in line.lower():
                        info["ios_version"] = line.strip()

                logger.info(f"Successfully connected to switch {self.switch.name}")
                return info

        except CiscoSSHError:
            raise
        except Exception as e:
            logger.error(f"Error testing connection to {self.switch.name}: {e}")
            raise CiscoSSHError(f"Test connection failed: {e}") from e

    def enable_port(self, port_number: str, vlan: int) -> bool:
        """
        Enable a switch port and configure VLAN.

        Args:
            port_number: Interface name (e.g., "Gi0/1").
            vlan: VLAN ID to assign.

        Returns:
            True if successful.

        Raises:
            CiscoSSHError: If operation fails.
        """
        commands = [
            f"interface {port_number}",
            "no shutdown",
            f"switchport access vlan {vlan}",
            "switchport mode access",
        ]

        try:
            with self._connect() as conn:
                logger.info(
                    f"Enabling port {port_number} on switch {self.switch.name} with VLAN {vlan}"
                )
                output = conn.send_config_set(commands)
                logger.debug(f"Command output: {output}")

                # Verify port is up
                status = conn.send_command(f"show interface {port_number} status")
                logger.debug(f"Port status: {status}")

                return True

        except CiscoSSHError:
            raise
        except Exception as e:
            logger.error(f"Error enabling port {port_number} on {self.switch.name}: {e}")
            raise CiscoSSHError(f"Failed to enable port: {e}") from e

    def disable_port(self, port_number: str) -> bool:
        """
        Disable a switch port.

        Args:
            port_number: Interface name (e.g., "Gi0/1").

        Returns:
            True if successful.

        Raises:
            CiscoSSHError: If operation fails.
        """
        commands = [
            f"interface {port_number}",
            "shutdown",
        ]

        try:
            with self._connect() as conn:
                logger.info(f"Disabling port {port_number} on switch {self.switch.name}")
                output = conn.send_config_set(commands)
                logger.debug(f"Command output: {output}")

                return True

        except CiscoSSHError:
            raise
        except Exception as e:
            logger.error(f"Error disabling port {port_number} on {self.switch.name}: {e}")
            raise CiscoSSHError(f"Failed to disable port: {e}") from e

    def get_port_status(self, port_number: str) -> dict[str, Any]:
        """
        Get current status of a switch port.

        Args:
            port_number: Interface name (e.g., "Gi0/1").

        Returns:
            Dictionary with port status info.

        Raises:
            CiscoSSHError: If operation fails.
        """
        try:
            with self._connect() as conn:
                output = conn.send_command(f"show interface {port_number} status")

                # Parse output with more robust handling
                status = {
                    "port": port_number,
                    "raw_output": output,
                    "name": "",
                    "admin_status": "unknown",
                    "vlan": "",
                }

                # Basic parsing - status line typically shows:
                # Port      Name     Status    Vlan     Duplex  Speed Type
                lines = output.strip().split("\n")
                for line in lines:
                    # Skip header lines
                    if line.startswith("Port") or line.startswith("-"):
                        continue
                    if port_number.lower() in line.lower():
                        parts = line.split()
                        if len(parts) >= 4:
                            # Handle case where Name column might be empty
                            try:
                                status["name"] = parts[1] if len(parts) > 1 else ""
                                status["admin_status"] = parts[2] if len(parts) > 2 else "unknown"
                                status["vlan"] = parts[3] if len(parts) > 3 else ""
                            except IndexError:
                                logger.warning(f"Could not parse port status line: {line}")
                        break

                return status

        except CiscoSSHError:
            raise
        except Exception as e:
            logger.error(f"Error getting status for port {port_number}: {e}")
            raise CiscoSSHError(f"Failed to get port status: {e}") from e

    def discover_ports(self) -> list[dict[str, Any]]:
        """
        Discover available ports on the switch.

        Runs 'sh int description' and parses for ports that are:
        - Administratively down (admin down)
        - Have description 'Available'

        Returns:
            List of dicts with port_name, short_name, description, status.
        """
        try:
            with self._connect() as conn:
                output = conn.send_command("sh int description")
                return self._parse_interface_description(output)

        except CiscoSSHError:
            raise
        except Exception as e:
            logger.error(f"Error discovering ports on {self.switch.name}: {e}")
            raise CiscoSSHError(f"Failed to discover ports: {e}") from e

    def _parse_interface_description(self, output: str) -> list[dict[str, Any]]:
        """
        Parse 'sh int description' output for available ports.

        Args:
            output: Raw command output.

        Returns:
            List of available ports with their details.
        """
        available_ports = []
        lines = output.strip().split("\n")

        for line in lines:
            # Skip header line
            if line.startswith("Interface") or not line.strip():
                continue

            # Parse line: Interface, Status, Protocol, Description
            # Format: Gi1/0/7                        admin down     down     Available
            parts = line.split()
            if len(parts) < 3:
                continue

            interface = parts[0]

            # Skip non-physical interfaces (VLANs, etc.)
            if not interface.startswith("Gi") and not interface.startswith("Fa"):
                continue

            # Check for "admin down" status
            # Line format: Interface  admin  down  <protocol>  [description...]
            # parts[1]="admin", parts[2]="down", parts[3]=protocol, parts[4+]=description
            status_str = " ".join(parts[1:3]).lower()
            if "admin down" not in status_str:
                continue

            # Get description (everything after protocol column, index 4+)
            # parts[0]=interface, parts[1]="admin", parts[2]="down", parts[3]=protocol
            description = ""
            if len(parts) > 4:
                description = " ".join(parts[4:])

            # Only include ports with "Available" description
            if description.strip().lower() != "available":
                continue

            # Convert short name to full name
            port_name = self._expand_port_name(interface)

            available_ports.append(
                {
                    "port_name": port_name,
                    "short_name": interface,
                    "description": description.strip(),
                    "status": "available",
                }
            )

        logger.info(f"Discovered {len(available_ports)} available ports on {self.switch.name}")
        return available_ports

    def _expand_port_name(self, short_name: str) -> str:
        """Expand short interface name to full name."""
        if short_name.startswith("Gi"):
            return "GigabitEthernet" + short_name[2:]
        elif short_name.startswith("Fa"):
            return "FastEthernet" + short_name[2:]
        return short_name

    def verify_port_state(self, port_number: str) -> dict[str, Any]:
        """
        Verify current state of a port.

        Args:
            port_number: Interface name (e.g., "Gi1/0/7").

        Returns:
            Dict with is_admin_down, is_connected, description.
        """
        try:
            with self._connect() as conn:
                output = conn.send_command(f"sh int {port_number}")
                return self._parse_port_state(output)

        except CiscoSSHError:
            raise
        except Exception as e:
            logger.error(f"Error verifying port {port_number}: {e}")
            raise CiscoSSHError(f"Failed to verify port state: {e}") from e

    def _parse_port_state(self, output: str) -> dict[str, Any]:
        """
        Parse 'sh int <port>' output for state.

        Args:
            output: Raw command output.

        Returns:
            Dict with port state details.
        """
        lines = output.strip().split("\n")
        state = {
            "is_admin_down": False,
            "is_connected": False,
            "description": "",
            "raw_status": "",
        }

        for line in lines:
            line_lower = line.lower()

            # First line has status
            if "is administratively down" in line_lower:
                state["is_admin_down"] = True
                state["raw_status"] = "administratively down"
            elif "is up" in line_lower and "line protocol is up" in line_lower:
                state["is_connected"] = True
                state["raw_status"] = "up"
            elif "is down" in line_lower and "administratively" not in line_lower:
                state["raw_status"] = "down"

            # Description line
            if line.strip().startswith("Description:"):
                state["description"] = line.split(":", 1)[1].strip()

        return state

    def configure_port_assign(self, port_number: str, simulator_name: str, vlan: int) -> bool:
        """
        Configure port for simulator assignment.

        The port remains disabled (shutdown) after assignment.
        User must explicitly enable the port when needed.

        Args:
            port_number: Interface name (e.g., "Gi1/0/7").
            simulator_name: Name to use in description.
            vlan: VLAN ID to assign.

        Returns:
            True if successful.
        """
        commands = [
            f"interface {port_number}",
            f"description SIMPORT:{simulator_name}",
            "switchport",
            "switchport mode access",
            f"switchport access vlan {vlan}",
            # Port stays shutdown - user enables explicitly when needed
        ]

        try:
            with self._connect() as conn:
                logger.info(f"Configuring port {port_number} for {simulator_name} on VLAN {vlan}")
                output = conn.send_config_set(commands)
                logger.debug(f"Config output: {output}")

                # Write config
                conn.send_command("wr mem")
                logger.info(f"Port {port_number} configured and saved")
                return True

        except CiscoSSHError:
            raise
        except Exception as e:
            logger.error(f"Error configuring port {port_number}: {e}")
            raise CiscoSSHError(f"Failed to configure port: {e}") from e

    def configure_port_release(self, port_number: str, vlan: int) -> bool:
        """
        Release port back to Available state.

        Args:
            port_number: Interface name (e.g., "Gi1/0/7").
            vlan: Current VLAN to remove.

        Returns:
            True if successful.
        """
        commands = [
            f"interface {port_number}",
            "description Available",
            f"no switchport access vlan {vlan}",
            "shutdown",
        ]

        try:
            with self._connect() as conn:
                logger.info(f"Releasing port {port_number} back to Available")
                output = conn.send_config_set(commands)
                logger.debug(f"Config output: {output}")

                # Write config
                conn.send_command("wr mem")
                logger.info(f"Port {port_number} released and saved")
                return True

        except CiscoSSHError:
            raise
        except Exception as e:
            logger.error(f"Error releasing port {port_number}: {e}")
            raise CiscoSSHError(f"Failed to release port: {e}") from e

    # =========================================================================
    # Async Wrappers
    # =========================================================================
    # These methods run the synchronous SSH operations in a thread pool
    # to avoid blocking the async event loop.

    async def enable_port_async(self, port_number: str, vlan: int) -> bool:
        """
        Async wrapper for enable_port.

        Runs the SSH operation in a thread pool to avoid blocking.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_ssh_executor, self.enable_port, port_number, vlan)

    async def disable_port_async(self, port_number: str) -> bool:
        """
        Async wrapper for disable_port.

        Runs the SSH operation in a thread pool to avoid blocking.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_ssh_executor, self.disable_port, port_number)

    async def test_connection_async(self) -> dict[str, Any]:
        """
        Async wrapper for test_connection.

        Runs the SSH operation in a thread pool to avoid blocking.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_ssh_executor, self.test_connection)

    async def get_port_status_async(self, port_number: str) -> dict[str, Any]:
        """
        Async wrapper for get_port_status.

        Runs the SSH operation in a thread pool to avoid blocking.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_ssh_executor, self.get_port_status, port_number)

    async def discover_ports_async(self) -> list[dict[str, Any]]:
        """Async wrapper for discover_ports."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_ssh_executor, self.discover_ports)

    async def verify_port_state_async(self, port_number: str) -> dict[str, Any]:
        """Async wrapper for verify_port_state."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_ssh_executor, self.verify_port_state, port_number)

    async def configure_port_assign_async(
        self, port_number: str, simulator_name: str, vlan: int
    ) -> bool:
        """Async wrapper for configure_port_assign."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _ssh_executor, self.configure_port_assign, port_number, simulator_name, vlan
        )

    async def configure_port_release_async(self, port_number: str, vlan: int) -> bool:
        """Async wrapper for configure_port_release."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _ssh_executor, self.configure_port_release, port_number, vlan
        )
