"""
Tests for port assignment and control endpoints.
"""

import pytest

from app.models.port_assignment import PortAssignment
from app.models.simulator import Simulator
from app.models.switch import Switch
from app.models.user import User
from app.services.auth import AuthService
from app.services.encryption import EncryptionService


@pytest.fixture
async def admin_user(db_session):
    """Create an admin user for testing."""
    user = User(
        username="portadmin",
        password_hash=AuthService.get_password_hash("adminpass123"),
        role="admin",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def simtech_user(db_session):
    """Create a simtech user for testing."""
    user = User(
        username="portsimtech",
        password_hash=AuthService.get_password_hash("simtechpass123"),
        role="simtech",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user):
    """Get JWT token for admin user."""
    return AuthService.create_access_token(
        {
            "sub": admin_user.username,
            "user_id": admin_user.id,
            "role": admin_user.role,
        }
    )


@pytest.fixture
def simtech_token(simtech_user):
    """Get JWT token for simtech user."""
    return AuthService.create_access_token(
        {
            "sub": simtech_user.username,
            "user_id": simtech_user.id,
            "role": simtech_user.role,
        }
    )


@pytest.fixture
async def test_simulator(db_session):
    """Create a test simulator."""
    simulator = Simulator(
        name="Port Test Simulator",
        short_name="PTS",
        icon_path="/icons/pts.png",
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
        name="Port Test Switch",
        ip_address="192.168.1.1",
        username="admin",
        password_encrypted=encryption.encrypt("switchpassword"),
        device_type="cisco_ios",
    )
    db_session.add(switch)
    await db_session.commit()
    await db_session.refresh(switch)
    return switch


@pytest.fixture
async def test_port_assignment(db_session, test_simulator, test_switch):
    """Create a test port assignment."""
    port = PortAssignment(
        simulator_id=test_simulator.id,
        switch_id=test_switch.id,
        port_number="Gi0/1",
        vlan=30,
        timeout_hours=4,
        status="disabled",
    )
    db_session.add(port)
    await db_session.commit()
    await db_session.refresh(port)
    return port


@pytest.mark.asyncio
class TestPortAssignmentEndpoints:
    """Tests for port assignment CRUD endpoints."""

    async def test_list_port_assignments_requires_admin(self, client, simtech_token):
        """Non-admin users should not access port assignments list."""
        response = await client.get(
            "/api/ports/assignments",
            headers={"Authorization": f"Bearer {simtech_token}"},
        )
        assert response.status_code == 403

    async def test_list_port_assignments_as_admin(self, client, admin_token, test_port_assignment):
        """Admin should be able to list port assignments."""
        response = await client.get(
            "/api/ports/assignments",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "port_assignments" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_create_port_assignment(self, client, admin_token, test_simulator, test_switch):
        """Admin should be able to create port assignments."""
        response = await client.post(
            "/api/ports/assignments",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "simulator_id": test_simulator.id,
                "switch_id": test_switch.id,
                "port_number": "Gi0/5",
                "vlan": 40,
                "timeout_hours": 8,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["port_number"] == "Gi0/5"
        assert data["vlan"] == 40
        assert data["timeout_hours"] == 8

    async def test_create_duplicate_port_assignment_fails(
        self, client, admin_token, test_port_assignment, test_simulator
    ):
        """Should not allow duplicate switch/port combinations."""
        response = await client.post(
            "/api/ports/assignments",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "simulator_id": test_simulator.id,
                "switch_id": test_port_assignment.switch_id,
                "port_number": test_port_assignment.port_number,  # Same port
                "vlan": 50,
                "timeout_hours": 2,
            },
        )
        assert response.status_code == 400
        assert "already assigned" in response.json()["detail"].lower()

    async def test_update_port_assignment(self, client, admin_token, test_port_assignment):
        """Admin should be able to update port assignments."""
        response = await client.put(
            f"/api/ports/assignments/{test_port_assignment.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "vlan": 100,
                "timeout_hours": 12,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["vlan"] == 100
        assert data["timeout_hours"] == 12

    async def test_update_port_assignment_not_found(self, client, admin_token):
        """Should return 404 for non-existent port assignment."""
        response = await client.put(
            "/api/ports/assignments/99999",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"vlan": 50},
        )
        assert response.status_code == 404

    async def test_delete_port_assignment(self, client, admin_token, test_port_assignment):
        """Admin should be able to delete port assignments."""
        response = await client.delete(
            f"/api/ports/assignments/{test_port_assignment.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 204

    async def test_delete_port_assignment_not_found(self, client, admin_token):
        """Should return 404 for non-existent port assignment."""
        response = await client.delete(
            "/api/ports/assignments/99999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404


@pytest.mark.asyncio
class TestPortStatusEndpoints:
    """Tests for port status endpoints."""

    async def test_get_port_status_requires_auth(self, client, test_port_assignment):
        """Port status should require authentication."""
        response = await client.get(f"/api/ports/{test_port_assignment.id}")
        assert response.status_code == 401

    async def test_get_port_status_authenticated(self, client, admin_token, test_port_assignment):
        """Authenticated users should see port status."""
        response = await client.get(
            f"/api/ports/{test_port_assignment.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["port_number"] == "Gi0/1"
        assert data["status"] == "disabled"

    async def test_get_port_status_not_found(self, client, admin_token):
        """Should return 404 for non-existent port."""
        response = await client.get(
            "/api/ports/99999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404


@pytest.fixture
async def enabled_port_assignment(db_session, test_simulator, test_switch, admin_user):
    """Create an enabled port assignment."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    now = datetime.now(UTC)
    port = PortAssignment(
        simulator_id=test_simulator.id,
        switch_id=test_switch.id,
        port_number="Gi0/2",
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
class TestPortEnableDisable:
    """Tests for port enable/disable endpoints."""

    async def test_enable_port_not_found(self, client, admin_token):
        """Should return 404 for non-existent port."""
        response = await client.post(
            "/api/ports/99999/enable",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    async def test_disable_port_not_found(self, client, admin_token):
        """Should return 404 for non-existent port."""
        response = await client.post(
            "/api/ports/99999/disable",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    async def test_disable_already_disabled_port(self, client, admin_token, test_port_assignment):
        """Should error when disabling already disabled port."""
        response = await client.post(
            f"/api/ports/{test_port_assignment.id}/disable",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400
        assert "already disabled" in response.json()["detail"].lower()

    async def test_enable_already_enabled_port(self, client, admin_token, enabled_port_assignment):
        """Should error when enabling already enabled port."""
        response = await client.post(
            f"/api/ports/{enabled_port_assignment.id}/enable",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400
        assert "already enabled" in response.json()["detail"].lower()

    async def test_enable_port_requires_auth(self, client, test_port_assignment):
        """Enable port should require authentication."""
        response = await client.post(f"/api/ports/{test_port_assignment.id}/enable")
        assert response.status_code == 401

    async def test_disable_port_requires_auth(self, client, enabled_port_assignment):
        """Disable port should require authentication."""
        response = await client.post(f"/api/ports/{enabled_port_assignment.id}/disable")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestPortAccessControl:
    """Tests for port access control."""

    async def test_simtech_cannot_access_unassigned_port(
        self, client, simtech_token, test_port_assignment
    ):
        """SimTech should not access ports for unassigned simulators."""
        response = await client.get(
            f"/api/ports/{test_port_assignment.id}",
            headers={"Authorization": f"Bearer {simtech_token}"},
        )
        assert response.status_code == 403

    async def test_admin_can_access_any_port(self, client, admin_token, test_port_assignment):
        """Admin should access any port."""
        response = await client.get(
            f"/api/ports/{test_port_assignment.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200


@pytest.mark.asyncio
class TestPortAssignmentModel:
    """Tests for PortAssignment model properties."""

    async def test_is_enabled_when_disabled(self, test_port_assignment):
        """is_enabled should return False when status is disabled."""
        assert test_port_assignment.is_enabled is False

    async def test_seconds_remaining_when_disabled(self, test_port_assignment):
        """seconds_remaining should return None when disabled."""
        assert test_port_assignment.seconds_remaining is None

    async def test_port_repr(self, test_port_assignment):
        """Port repr should include key info."""
        repr_str = repr(test_port_assignment)
        assert "PortAssignment" in repr_str
        assert "Gi0/1" in repr_str
        assert "disabled" in repr_str


@pytest.mark.asyncio
class TestPortEnableDisableWithMockedSSH:
    """Tests for port enable/disable with mocked SSH."""

    async def test_enable_port_success(self, client, admin_token, test_port_assignment):
        """Should enable port with mocked SSH."""
        from unittest.mock import AsyncMock, MagicMock, patch

        with (
            patch("app.services.port_control.CiscoSSHService") as mock_ssh_class,
            patch("app.services.port_control.get_scheduler_service") as mock_sched_fn,
        ):
            mock_ssh = MagicMock()
            mock_ssh.enable_port_async = AsyncMock()
            mock_ssh_class.return_value = mock_ssh

            mock_sched = MagicMock()
            mock_sched.schedule_port_disable = MagicMock()
            mock_sched_fn.return_value = mock_sched

            response = await client.post(
                f"/api/ports/{test_port_assignment.id}/enable",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "enabled"

    async def test_enable_port_with_overrides(self, client, admin_token, test_port_assignment):
        """Should enable port with timeout and VLAN overrides."""
        from unittest.mock import AsyncMock, MagicMock, patch

        with (
            patch("app.services.port_control.CiscoSSHService") as mock_ssh_class,
            patch("app.services.port_control.get_scheduler_service") as mock_sched_fn,
        ):
            mock_ssh = MagicMock()
            mock_ssh.enable_port_async = AsyncMock()
            mock_ssh_class.return_value = mock_ssh

            mock_sched = MagicMock()
            mock_sched.schedule_port_disable = MagicMock()
            mock_sched_fn.return_value = mock_sched

            response = await client.post(
                f"/api/ports/{test_port_assignment.id}/enable",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"timeout_hours": 8, "vlan": 50},
            )
            assert response.status_code == 200

    async def test_disable_port_success(self, client, admin_token, enabled_port_assignment):
        """Should disable port with mocked SSH."""
        from unittest.mock import AsyncMock, MagicMock, patch

        with (
            patch("app.services.port_control.CiscoSSHService") as mock_ssh_class,
            patch("app.services.port_control.get_scheduler_service") as mock_sched_fn,
        ):
            mock_ssh = MagicMock()
            mock_ssh.disable_port_async = AsyncMock()
            mock_ssh_class.return_value = mock_ssh

            mock_sched = MagicMock()
            mock_sched.cancel_port_disable = MagicMock()
            mock_sched_fn.return_value = mock_sched

            response = await client.post(
                f"/api/ports/{enabled_port_assignment.id}/disable",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "disabled"

    async def test_enable_port_ssh_failure(self, client, admin_token, test_port_assignment):
        """Should return 500 when SSH fails."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.services.cisco_ssh import CiscoSSHError

        with (
            patch("app.services.port_control.CiscoSSHService") as mock_ssh_class,
            patch("app.services.port_control.get_scheduler_service") as mock_sched_fn,
        ):
            mock_ssh = MagicMock()
            mock_ssh.enable_port_async = AsyncMock(side_effect=CiscoSSHError("Connection failed"))
            mock_ssh_class.return_value = mock_ssh
            mock_sched_fn.return_value = MagicMock()

            response = await client.post(
                f"/api/ports/{test_port_assignment.id}/enable",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert response.status_code == 500
            assert "failed" in response.json()["detail"].lower()
