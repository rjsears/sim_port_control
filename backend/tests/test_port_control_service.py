"""
Tests for port control service with mocked SSH.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.port_assignment import PortAssignment
from app.models.simulator import Simulator
from app.models.switch import Switch
from app.models.user import User
from app.services.auth import AuthService
from app.services.cisco_ssh import CiscoSSHError
from app.services.encryption import EncryptionService
from app.services.port_control import PortControlError, PortControlService


@pytest.fixture
async def admin_user(db_session):
    """Create an admin user for testing."""
    user = User(
        username="pcadmin",
        password_hash=AuthService.get_password_hash("adminpass123"),
        role="admin",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def simtech_user(db_session, test_simulator):
    """Create a simtech user with simulator assignment."""
    from app.models.user import UserSimulatorAssignment

    user = User(
        username="pcsimtech",
        password_hash=AuthService.get_password_hash("simtechpass123"),
        role="simtech",
    )
    db_session.add(user)
    await db_session.flush()

    # Assign simulator to user
    assignment = UserSimulatorAssignment(user_id=user.id, simulator_id=test_simulator.id)
    db_session.add(assignment)

    await db_session.commit()

    # Reload with relationships
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    result = await db_session.execute(
        select(User).where(User.id == user.id).options(selectinload(User.simulator_assignments))
    )
    return result.scalar_one()


@pytest.fixture
async def test_simulator(db_session):
    """Create a test simulator."""
    simulator = Simulator(
        name="PC Test Simulator",
        short_name="PCTS",
        icon_path="/icons/pcts.png",
    )
    db_session.add(simulator)
    await db_session.commit()
    await db_session.refresh(simulator)
    return simulator


@pytest.fixture
async def test_switch(db_session):
    """Create a test switch."""
    encryption = EncryptionService()
    switch = Switch(
        name="PC Test Switch",
        ip_address="192.168.1.100",
        username="admin",
        password_encrypted=encryption.encrypt("switchpassword"),
        device_type="cisco_ios",
    )
    db_session.add(switch)
    await db_session.commit()
    await db_session.refresh(switch)
    return switch


@pytest.fixture
async def test_port(db_session, test_simulator, test_switch):
    """Create a test port assignment."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    port = PortAssignment(
        simulator_id=test_simulator.id,
        switch_id=test_switch.id,
        port_number="Gi0/10",
        vlan=30,
        timeout_hours=4,
        status="disabled",
    )
    db_session.add(port)
    await db_session.commit()

    # Reload with relationships
    result = await db_session.execute(
        select(PortAssignment)
        .where(PortAssignment.id == port.id)
        .options(
            selectinload(PortAssignment.switch),
            selectinload(PortAssignment.simulator),
            selectinload(PortAssignment.enabled_by),
        )
    )
    return result.scalar_one()


@pytest.fixture
async def enabled_port(db_session, test_simulator, test_switch, admin_user):
    """Create an enabled port assignment."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    now = datetime.now(UTC)
    port = PortAssignment(
        simulator_id=test_simulator.id,
        switch_id=test_switch.id,
        port_number="Gi0/11",
        vlan=30,
        timeout_hours=4,
        status="enabled",
        enabled_at=now,
        auto_disable_at=now + timedelta(hours=4),
        enabled_by_user_id=admin_user.id,
    )
    db_session.add(port)
    await db_session.commit()

    # Reload with relationships
    result = await db_session.execute(
        select(PortAssignment)
        .where(PortAssignment.id == port.id)
        .options(
            selectinload(PortAssignment.switch),
            selectinload(PortAssignment.simulator),
            selectinload(PortAssignment.enabled_by),
        )
    )
    return result.scalar_one()


@pytest.mark.asyncio
class TestPortControlService:
    """Tests for PortControlService."""

    async def test_get_port_assignment(self, db_session, test_port):
        """Should retrieve port assignment by ID."""
        service = PortControlService(db_session)
        port = await service.get_port_assignment(test_port.id)

        assert port is not None
        assert port.id == test_port.id
        assert port.port_number == "Gi0/10"

    async def test_get_port_assignment_not_found(self, db_session):
        """Should return None for non-existent port."""
        service = PortControlService(db_session)
        port = await service.get_port_assignment(99999)

        assert port is None

    async def test_check_user_access_admin(self, db_session, admin_user, test_port):
        """Admin should have access to all ports."""
        service = PortControlService(db_session)
        has_access = await service.check_user_access(admin_user, test_port)

        assert has_access is True

    async def test_check_user_access_simtech_assigned(self, db_session, simtech_user, test_port):
        """SimTech should have access to assigned simulator ports."""
        service = PortControlService(db_session)
        has_access = await service.check_user_access(simtech_user, test_port)

        assert has_access is True

    async def test_check_user_access_simtech_not_assigned(self, db_session, test_port, test_switch):
        """SimTech should not have access to unassigned simulator ports."""
        # Create a different simulator
        other_sim = Simulator(name="Other Sim", short_name="OTHER")
        db_session.add(other_sim)
        await db_session.commit()

        # Create unassigned simtech
        unassigned_user = User(
            username="unassigned",
            password_hash=AuthService.get_password_hash("pass123"),
            role="simtech",
        )
        db_session.add(unassigned_user)
        await db_session.commit()

        # Reload with relationships
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        result = await db_session.execute(
            select(User)
            .where(User.id == unassigned_user.id)
            .options(selectinload(User.simulator_assignments))
        )
        unassigned_user = result.scalar_one()

        service = PortControlService(db_session)
        has_access = await service.check_user_access(unassigned_user, test_port)

        assert has_access is False

    @patch("app.services.port_control.CiscoSSHService")
    @patch("app.services.port_control.get_scheduler_service")
    async def test_enable_port_success(
        self, mock_scheduler, mock_ssh_class, db_session, test_port, admin_user
    ):
        """Should enable port successfully with mocked SSH."""
        # Setup mocks
        mock_ssh = MagicMock()
        mock_ssh.enable_port_async = AsyncMock()
        mock_ssh_class.return_value = mock_ssh

        mock_sched = MagicMock()
        mock_sched.schedule_port_disable = MagicMock()
        mock_scheduler.return_value = mock_sched

        service = PortControlService(db_session)
        result = await service.enable_port(test_port, admin_user)

        assert result.status == "enabled"
        assert result.enabled_at is not None
        assert result.auto_disable_at is not None
        assert result.enabled_by_user_id == admin_user.id
        mock_ssh.enable_port_async.assert_called_once_with("Gi0/10", 30)
        mock_sched.schedule_port_disable.assert_called_once()

    @patch("app.services.port_control.CiscoSSHService")
    @patch("app.services.port_control.get_scheduler_service")
    async def test_enable_port_with_overrides(
        self, mock_scheduler, mock_ssh_class, db_session, test_port, admin_user
    ):
        """Should enable port with timeout and VLAN overrides."""
        mock_ssh = MagicMock()
        mock_ssh.enable_port_async = AsyncMock()
        mock_ssh_class.return_value = mock_ssh

        mock_sched = MagicMock()
        mock_sched.schedule_port_disable = MagicMock()
        mock_scheduler.return_value = mock_sched

        service = PortControlService(db_session)
        result = await service.enable_port(test_port, admin_user, timeout_hours=8, vlan=50)

        assert result.vlan == 50
        mock_ssh.enable_port_async.assert_called_once_with("Gi0/10", 50)

    @patch("app.services.port_control.CiscoSSHService")
    @patch("app.services.port_control.get_scheduler_service")
    async def test_enable_port_ssh_failure(
        self, mock_scheduler, mock_ssh_class, db_session, test_port, admin_user
    ):
        """Should raise error when SSH fails."""
        mock_ssh = MagicMock()
        mock_ssh.enable_port_async = AsyncMock(side_effect=CiscoSSHError("Connection failed"))
        mock_ssh_class.return_value = mock_ssh

        mock_scheduler.return_value = MagicMock()

        service = PortControlService(db_session)

        with pytest.raises(PortControlError) as exc_info:
            await service.enable_port(test_port, admin_user)

        assert "Failed to enable port" in str(exc_info.value)

    @patch("app.services.port_control.CiscoSSHService")
    @patch("app.services.port_control.get_scheduler_service")
    async def test_disable_port_success(
        self, mock_scheduler, mock_ssh_class, db_session, enabled_port, admin_user
    ):
        """Should disable port successfully with mocked SSH."""
        mock_ssh = MagicMock()
        mock_ssh.disable_port_async = AsyncMock()
        mock_ssh_class.return_value = mock_ssh

        mock_sched = MagicMock()
        mock_sched.cancel_port_disable = MagicMock()
        mock_scheduler.return_value = mock_sched

        service = PortControlService(db_session)
        result = await service.disable_port(enabled_port, admin_user)

        assert result.status == "disabled"
        assert result.enabled_at is None
        assert result.auto_disable_at is None
        assert result.enabled_by_user_id is None
        mock_ssh.disable_port_async.assert_called_once_with("Gi0/11")
        mock_sched.cancel_port_disable.assert_called_once()

    @patch("app.services.port_control.CiscoSSHService")
    @patch("app.services.port_control.get_scheduler_service")
    async def test_disable_port_auto(
        self, mock_scheduler, mock_ssh_class, db_session, enabled_port
    ):
        """Should disable port automatically (no user)."""
        mock_ssh = MagicMock()
        mock_ssh.disable_port_async = AsyncMock()
        mock_ssh_class.return_value = mock_ssh

        mock_sched = MagicMock()
        mock_sched.cancel_port_disable = MagicMock()
        mock_scheduler.return_value = mock_sched

        service = PortControlService(db_session)
        result = await service.disable_port(enabled_port, user=None, is_auto=True)

        assert result.status == "disabled"

    @patch("app.services.port_control.CiscoSSHService")
    @patch("app.services.port_control.get_scheduler_service")
    async def test_disable_port_ssh_failure(
        self, mock_scheduler, mock_ssh_class, db_session, enabled_port, admin_user
    ):
        """Should raise error when SSH disable fails."""
        mock_ssh = MagicMock()
        mock_ssh.disable_port_async = AsyncMock(side_effect=CiscoSSHError("Connection failed"))
        mock_ssh_class.return_value = mock_ssh

        mock_scheduler.return_value = MagicMock()

        service = PortControlService(db_session)

        with pytest.raises(PortControlError) as exc_info:
            await service.disable_port(enabled_port, admin_user)

        assert "Failed to disable port" in str(exc_info.value)
