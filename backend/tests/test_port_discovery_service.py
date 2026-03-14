"""Tests for PortDiscoveryService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.discovered_port import DiscoveredPort
from app.models.port_assignment import PortAssignment
from app.models.simulator import Simulator
from app.models.switch import Switch
from app.services.cisco_ssh import CiscoSSHError
from app.services.port_discovery import PortDiscoveryService


@pytest.fixture
async def test_switch(db_session):
    """Create a test switch."""
    switch = Switch(
        name="TestSwitch",
        ip_address="192.168.1.1",
        username="admin",
        password_encrypted="encrypted",
    )
    db_session.add(switch)
    await db_session.commit()
    await db_session.refresh(switch)
    return switch


@pytest.fixture
async def test_simulator(db_session):
    """Create a test simulator."""
    simulator = Simulator(
        name="Test Simulator",
        short_name="TST",
        icon_path="/icons/tst.png",
    )
    db_session.add(simulator)
    await db_session.commit()
    await db_session.refresh(simulator)
    return simulator


@pytest.fixture
async def available_port(db_session, test_switch):
    """Create an available discovered port."""
    port = DiscoveredPort(
        switch_id=test_switch.id,
        port_name="GigabitEthernet1/0/7",
        short_name="Gi1/0/7",
        status="available",
        description="Available",
        discovered_at=datetime.now(UTC),
    )
    db_session.add(port)
    await db_session.commit()

    result = await db_session.execute(
        select(DiscoveredPort)
        .where(DiscoveredPort.id == port.id)
        .options(selectinload(DiscoveredPort.switch))
    )
    return result.scalar_one()


@pytest.fixture
async def assigned_port_with_assignment(db_session, test_switch, test_simulator):
    """Create an assigned discovered port with port assignment."""
    port = DiscoveredPort(
        switch_id=test_switch.id,
        port_name="GigabitEthernet1/0/8",
        short_name="Gi1/0/8",
        status="assigned",
        description="SIMPORT:TST",
        discovered_at=datetime.now(UTC),
    )
    db_session.add(port)
    await db_session.flush()

    assignment = PortAssignment(
        simulator_id=test_simulator.id,
        switch_id=test_switch.id,
        port_number="Gi1/0/8",
        vlan=30,
        timeout_hours=4,
        status="enabled",
        discovered_port_id=port.id,
    )
    db_session.add(assignment)
    await db_session.commit()

    result = await db_session.execute(
        select(DiscoveredPort)
        .where(DiscoveredPort.id == port.id)
        .options(
            selectinload(DiscoveredPort.switch),
            selectinload(DiscoveredPort.port_assignment).selectinload(PortAssignment.simulator),
        )
    )
    return result.scalar_one()


@pytest.mark.asyncio
class TestScanSwitch:
    """Tests for switch scanning."""

    async def test_scan_creates_discovered_ports(self, db_session, test_switch):
        """Should create DiscoveredPort records for available ports."""
        mock_ports = [
            {
                "port_name": "GigabitEthernet1/0/7",
                "short_name": "Gi1/0/7",
                "description": "Available",
                "status": "available",
            },
            {
                "port_name": "GigabitEthernet1/0/8",
                "short_name": "Gi1/0/8",
                "description": "Available",
                "status": "available",
            },
        ]

        with patch("app.services.port_discovery.CiscoSSHService") as mock_ssh:
            mock_instance = MagicMock()
            mock_instance.discover_ports_async = AsyncMock(return_value=mock_ports)
            mock_ssh.return_value = mock_instance

            service = PortDiscoveryService(db_session)
            result = await service.scan_switch(test_switch.id)

        assert result["success"] is True
        assert result["ports_found"] == 2
        assert result["new_ports"] == 2

    async def test_scan_switch_not_found(self, db_session):
        """Should return failure for non-existent switch."""
        service = PortDiscoveryService(db_session)
        result = await service.scan_switch(99999)

        assert result["success"] is False
        assert "not found" in result["message"]

    async def test_scan_ssh_error(self, db_session, test_switch):
        """Should handle SSH errors gracefully."""
        with patch("app.services.port_discovery.CiscoSSHService") as mock_ssh:
            mock_instance = MagicMock()
            mock_instance.discover_ports_async = AsyncMock(
                side_effect=CiscoSSHError("Connection refused")
            )
            mock_ssh.return_value = mock_instance

            service = PortDiscoveryService(db_session)
            result = await service.scan_switch(test_switch.id)

        assert result["success"] is False
        assert "Connection refused" in result["message"]

    async def test_scan_updates_existing_ports(self, db_session, test_switch, available_port):
        """Should update existing ports during scan."""
        mock_ports = [
            {
                "port_name": "GigabitEthernet1/0/7",
                "short_name": "Gi1/0/7",
                "description": "Updated Description",
                "status": "available",
            },
        ]

        with patch("app.services.port_discovery.CiscoSSHService") as mock_ssh:
            mock_instance = MagicMock()
            mock_instance.discover_ports_async = AsyncMock(return_value=mock_ports)
            mock_ssh.return_value = mock_instance

            service = PortDiscoveryService(db_session)
            result = await service.scan_switch(test_switch.id)

        assert result["success"] is True
        assert result["new_ports"] == 0  # Existing port updated, not new

    async def test_scan_marks_missing_ports_as_error(self, db_session, test_switch, available_port):
        """Should mark ports not found in scan as error."""
        mock_ports = []  # No ports returned

        with patch("app.services.port_discovery.CiscoSSHService") as mock_ssh:
            mock_instance = MagicMock()
            mock_instance.discover_ports_async = AsyncMock(return_value=mock_ports)
            mock_ssh.return_value = mock_instance

            service = PortDiscoveryService(db_session)
            result = await service.scan_switch(test_switch.id)

        assert result["success"] is True
        assert result["removed_ports"] == 1


@pytest.mark.asyncio
class TestGetDiscoveredPorts:
    """Tests for getting discovered ports."""

    async def test_get_all_ports(self, db_session, available_port):
        """Should return all discovered ports."""
        service = PortDiscoveryService(db_session)
        ports = await service.get_discovered_ports()

        assert len(ports) >= 1

    async def test_get_ports_by_switch(self, db_session, test_switch, available_port):
        """Should filter ports by switch."""
        service = PortDiscoveryService(db_session)
        ports = await service.get_discovered_ports(switch_id=test_switch.id)

        assert len(ports) >= 1
        for port in ports:
            assert port.switch_id == test_switch.id

    async def test_get_ports_by_status(self, db_session, available_port):
        """Should filter ports by status."""
        service = PortDiscoveryService(db_session)
        ports = await service.get_discovered_ports(status="available")

        for port in ports:
            assert port.status == "available"


@pytest.mark.asyncio
class TestAssignPort:
    """Tests for port assignment."""

    async def test_assign_port_success(self, db_session, available_port, test_simulator):
        """Should assign port successfully."""
        with patch("app.services.port_discovery.CiscoSSHService") as mock_ssh:
            mock_instance = MagicMock()
            mock_instance.configure_port_assign_async = AsyncMock()
            mock_instance.verify_port_state_async = AsyncMock(
                return_value={
                    "is_admin_down": False,
                    "description": "SIMPORT:TST",
                    "is_connected": False,
                }
            )
            mock_ssh.return_value = mock_instance

            service = PortDiscoveryService(db_session)
            result = await service.assign_port(
                discovered_port_id=available_port.id,
                simulator_id=test_simulator.id,
                vlan=30,
                timeout_hours=4,
                user_id=1,
            )

        assert result["success"] is True
        assert result["port_id"] is not None

    async def test_assign_port_not_found(self, db_session, test_simulator):
        """Should fail if port not found."""
        service = PortDiscoveryService(db_session)
        result = await service.assign_port(
            discovered_port_id=99999,
            simulator_id=test_simulator.id,
            vlan=30,
            timeout_hours=4,
            user_id=1,
        )

        assert result["success"] is False
        assert "not found" in result["message"]

    async def test_assign_port_not_available(
        self, db_session, assigned_port_with_assignment, test_simulator
    ):
        """Should fail if port is not available."""
        service = PortDiscoveryService(db_session)
        result = await service.assign_port(
            discovered_port_id=assigned_port_with_assignment.id,
            simulator_id=test_simulator.id,
            vlan=30,
            timeout_hours=4,
            user_id=1,
        )

        assert result["success"] is False
        assert "not available" in result["message"]

    async def test_assign_port_simulator_not_found(self, db_session, available_port):
        """Should fail if simulator not found."""
        service = PortDiscoveryService(db_session)
        result = await service.assign_port(
            discovered_port_id=available_port.id,
            simulator_id=99999,
            vlan=30,
            timeout_hours=4,
            user_id=1,
        )

        assert result["success"] is False
        assert "Simulator not found" in result["message"]

    async def test_assign_port_ssh_error(self, db_session, available_port, test_simulator):
        """Should handle SSH errors during assignment."""
        with patch("app.services.port_discovery.CiscoSSHService") as mock_ssh:
            mock_instance = MagicMock()
            mock_instance.configure_port_assign_async = AsyncMock(
                side_effect=CiscoSSHError("Connection failed")
            )
            mock_ssh.return_value = mock_instance

            service = PortDiscoveryService(db_session)
            result = await service.assign_port(
                discovered_port_id=available_port.id,
                simulator_id=test_simulator.id,
                vlan=30,
                timeout_hours=4,
                user_id=1,
            )

        assert result["success"] is False
        assert "SSH error" in result["message"]

    async def test_assign_port_succeeds_when_admin_down(
        self, db_session, available_port, test_simulator
    ):
        """Port should remain admin down after assignment - user enables explicitly."""
        with patch("app.services.port_discovery.CiscoSSHService") as mock_ssh:
            mock_instance = MagicMock()
            mock_instance.configure_port_assign_async = AsyncMock()
            mock_instance.verify_port_state_async = AsyncMock(
                return_value={
                    "is_admin_down": True,  # Expected - port stays down until user enables
                    "description": "SIMPORT:TST",
                    "is_connected": False,
                }
            )
            mock_ssh.return_value = mock_instance

            service = PortDiscoveryService(db_session)
            result = await service.assign_port(
                discovered_port_id=available_port.id,
                simulator_id=test_simulator.id,
                vlan=30,
                timeout_hours=4,
                user_id=1,
            )

        assert result["success"] is True

    async def test_assign_port_verification_ssh_error(
        self, db_session, available_port, test_simulator
    ):
        """Should handle verification SSH errors."""
        with patch("app.services.port_discovery.CiscoSSHService") as mock_ssh:
            mock_instance = MagicMock()
            mock_instance.configure_port_assign_async = AsyncMock()
            mock_instance.verify_port_state_async = AsyncMock(
                side_effect=CiscoSSHError("Verification failed")
            )
            mock_ssh.return_value = mock_instance

            service = PortDiscoveryService(db_session)
            result = await service.assign_port(
                discovered_port_id=available_port.id,
                simulator_id=test_simulator.id,
                vlan=30,
                timeout_hours=4,
                user_id=1,
            )

        assert result["success"] is False
        assert "Verification failed" in result["message"]


@pytest.mark.asyncio
class TestReleasePort:
    """Tests for port release."""

    async def test_release_port_success(self, db_session, assigned_port_with_assignment):
        """Should release port successfully."""
        assignment_id = assigned_port_with_assignment.port_assignment.id

        with patch("app.services.port_discovery.CiscoSSHService") as mock_ssh:
            mock_instance = MagicMock()
            mock_instance.configure_port_release_async = AsyncMock()
            mock_instance.verify_port_state_async = AsyncMock(
                return_value={
                    "is_admin_down": True,
                    "description": "Available",
                    "is_connected": False,
                }
            )
            mock_ssh.return_value = mock_instance

            service = PortDiscoveryService(db_session)
            result = await service.release_port(assignment_id, user_id=1)

        assert result["success"] is True

    async def test_release_port_not_found(self, db_session):
        """Should fail if assignment not found."""
        service = PortDiscoveryService(db_session)
        result = await service.release_port(99999, user_id=1)

        assert result["success"] is False
        assert "not found" in result["message"]

    async def test_release_port_ssh_error(self, db_session, assigned_port_with_assignment):
        """Should handle SSH errors during release."""
        assignment_id = assigned_port_with_assignment.port_assignment.id

        with patch("app.services.port_discovery.CiscoSSHService") as mock_ssh:
            mock_instance = MagicMock()
            mock_instance.configure_port_release_async = AsyncMock(
                side_effect=CiscoSSHError("Connection failed")
            )
            mock_ssh.return_value = mock_instance

            service = PortDiscoveryService(db_session)
            result = await service.release_port(assignment_id, user_id=1)

        assert result["success"] is False
        assert "SSH error" in result["message"]

    async def test_release_port_verification_fails_not_down(
        self, db_session, assigned_port_with_assignment
    ):
        """Should fail if port not admin down after release."""
        assignment_id = assigned_port_with_assignment.port_assignment.id

        with patch("app.services.port_discovery.CiscoSSHService") as mock_ssh:
            mock_instance = MagicMock()
            mock_instance.configure_port_release_async = AsyncMock()
            mock_instance.verify_port_state_async = AsyncMock(
                return_value={
                    "is_admin_down": False,  # Not down - failure
                    "description": "Available",
                    "is_connected": False,
                }
            )
            mock_ssh.return_value = mock_instance

            service = PortDiscoveryService(db_session)
            result = await service.release_port(assignment_id, user_id=1)

        assert result["success"] is False
        assert "not disabled" in result["message"]

    async def test_release_port_verification_ssh_error(
        self, db_session, assigned_port_with_assignment
    ):
        """Should handle verification SSH errors."""
        assignment_id = assigned_port_with_assignment.port_assignment.id

        with patch("app.services.port_discovery.CiscoSSHService") as mock_ssh:
            mock_instance = MagicMock()
            mock_instance.configure_port_release_async = AsyncMock()
            mock_instance.verify_port_state_async = AsyncMock(
                side_effect=CiscoSSHError("Verification failed")
            )
            mock_ssh.return_value = mock_instance

            service = PortDiscoveryService(db_session)
            result = await service.release_port(assignment_id, user_id=1)

        assert result["success"] is False
        assert "Verification failed" in result["message"]


@pytest.mark.asyncio
class TestGetSwitch:
    """Tests for getting switch."""

    async def test_get_switch_found(self, db_session, test_switch):
        """Should return switch with discovered ports."""
        service = PortDiscoveryService(db_session)
        switch = await service.get_switch(test_switch.id)

        assert switch is not None
        assert switch.id == test_switch.id

    async def test_get_switch_not_found(self, db_session):
        """Should return None for non-existent switch."""
        service = PortDiscoveryService(db_session)
        switch = await service.get_switch(99999)

        assert switch is None
