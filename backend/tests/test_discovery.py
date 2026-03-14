"""
Tests for port discovery endpoints.
"""

from unittest.mock import patch

import pytest

from app.models.discovered_port import DiscoveredPort
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
        username="discoveryadmin",
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
        username="discoverysimtech",
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
async def test_switch(db_session):
    """Create a test switch."""
    encryption = EncryptionService()
    switch = Switch(
        name="Discovery Test Switch",
        ip_address="192.168.1.200",
        username="admin",
        password_encrypted=encryption.encrypt("switchpassword"),
        device_type="cisco_ios",
    )
    db_session.add(switch)
    await db_session.commit()
    await db_session.refresh(switch)
    return switch


@pytest.fixture
async def test_simulator(db_session):
    """Create a test simulator."""
    simulator = Simulator(
        name="Discovery Test Simulator",
        short_name="DTS",
        icon_path="/icons/dts.png",
    )
    db_session.add(simulator)
    await db_session.commit()
    await db_session.refresh(simulator)
    return simulator


@pytest.fixture
async def discovered_port(db_session, test_switch):
    """Create a discovered port."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    port = DiscoveredPort(
        switch_id=test_switch.id,
        port_name="GigabitEthernet0/15",
        short_name="Gi0/15",
        status="available",
        description="Available port for simulators",
    )
    db_session.add(port)
    await db_session.commit()

    # Reload with relationships
    result = await db_session.execute(
        select(DiscoveredPort)
        .where(DiscoveredPort.id == port.id)
        .options(
            selectinload(DiscoveredPort.switch),
            selectinload(DiscoveredPort.port_assignment),
        )
    )
    return result.scalar_one()


@pytest.fixture
async def assigned_port(db_session, test_switch, test_simulator):
    """Create a discovered port that is assigned."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    port = DiscoveredPort(
        switch_id=test_switch.id,
        port_name="GigabitEthernet0/16",
        short_name="Gi0/16",
        status="assigned",
        description="Assigned port",
    )
    db_session.add(port)
    await db_session.flush()

    # Create the assignment
    assignment = PortAssignment(
        simulator_id=test_simulator.id,
        switch_id=test_switch.id,
        port_number="Gi0/16",
        vlan=30,
        timeout_hours=4,
        status="disabled",
        discovered_port_id=port.id,
    )
    db_session.add(assignment)
    await db_session.commit()

    # Reload with relationships
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
class TestDiscoveryEndpoints:
    """Tests for discovery API endpoints."""

    async def test_scan_switch_requires_admin(self, client, simtech_token, test_switch):
        """Non-admin users should not scan switches."""
        response = await client.post(
            f"/api/discovery/switches/{test_switch.id}/scan",
            headers={"Authorization": f"Bearer {simtech_token}"},
        )
        assert response.status_code == 403

    async def test_scan_switch_requires_auth(self, client, test_switch):
        """Unauthenticated users should not scan switches."""
        response = await client.post(f"/api/discovery/switches/{test_switch.id}/scan")
        assert response.status_code == 401

    @patch("app.services.port_discovery.PortDiscoveryService.scan_switch")
    async def test_scan_switch_as_admin(self, mock_scan, client, admin_token, test_switch):
        """Admin should be able to scan switches."""
        mock_scan.return_value = {
            "success": True,
            "message": "Scan completed",
            "ports_found": 24,
            "new_ports": 5,
            "removed_ports": 0,
        }

        response = await client.post(
            f"/api/discovery/switches/{test_switch.id}/scan",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["ports_found"] == 24
        assert data["new_ports"] == 5

    async def test_list_switch_ports_requires_admin(self, client, simtech_token, test_switch):
        """Non-admin users should not list switch ports."""
        response = await client.get(
            f"/api/discovery/switches/{test_switch.id}/ports",
            headers={"Authorization": f"Bearer {simtech_token}"},
        )
        assert response.status_code == 403

    async def test_list_switch_ports_as_admin(
        self, client, admin_token, test_switch, discovered_port
    ):
        """Admin should be able to list switch ports."""
        response = await client.get(
            f"/api/discovery/switches/{test_switch.id}/ports",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "ports" in data
        assert "total" in data
        assert "available_count" in data
        assert "assigned_count" in data

    async def test_list_all_ports_requires_admin(self, client, simtech_token):
        """Non-admin users should not list all ports."""
        response = await client.get(
            "/api/discovery/ports",
            headers={"Authorization": f"Bearer {simtech_token}"},
        )
        assert response.status_code == 403

    async def test_list_all_ports_as_admin(self, client, admin_token, discovered_port):
        """Admin should be able to list all ports."""
        response = await client.get(
            "/api/discovery/ports",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "ports" in data
        assert data["total"] >= 1

    async def test_list_ports_filter_by_status(self, client, admin_token, discovered_port):
        """Should filter ports by status."""
        response = await client.get(
            "/api/discovery/ports?status=available",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        for port in data["ports"]:
            assert port["status"] == "available"

    async def test_assign_port_requires_admin(
        self, client, simtech_token, discovered_port, test_simulator
    ):
        """Non-admin users should not assign ports."""
        response = await client.post(
            "/api/discovery/ports/assign",
            headers={"Authorization": f"Bearer {simtech_token}"},
            json={
                "discovered_port_id": discovered_port.id,
                "simulator_id": test_simulator.id,
                "vlan": 30,
                "timeout_hours": 4,
            },
        )
        assert response.status_code == 403

    @patch("app.services.port_discovery.PortDiscoveryService.assign_port")
    async def test_assign_port_as_admin(
        self, mock_assign, client, admin_token, discovered_port, test_simulator
    ):
        """Admin should be able to assign ports."""
        mock_assign.return_value = {
            "success": True,
            "message": "Port assigned successfully",
            "port_id": 1,
        }

        response = await client.post(
            "/api/discovery/ports/assign",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "discovered_port_id": discovered_port.id,
                "simulator_id": test_simulator.id,
                "vlan": 30,
                "timeout_hours": 4,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_release_port_requires_admin(self, client, simtech_token, assigned_port):
        """Non-admin users should not release ports."""
        response = await client.delete(
            f"/api/discovery/ports/assignments/{assigned_port.port_assignment.id}",
            headers={"Authorization": f"Bearer {simtech_token}"},
        )
        assert response.status_code == 403

    @patch("app.services.port_discovery.PortDiscoveryService.release_port")
    async def test_release_port_as_admin(self, mock_release, client, admin_token, assigned_port):
        """Admin should be able to release ports."""
        mock_release.return_value = {
            "success": True,
            "message": "Port released successfully",
        }

        response = await client.delete(
            f"/api/discovery/ports/assignments/{assigned_port.port_assignment.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_refresh_port_requires_admin(self, client, simtech_token, discovered_port):
        """Non-admin users should not refresh port status."""
        response = await client.post(
            f"/api/discovery/ports/{discovered_port.id}/refresh",
            headers={"Authorization": f"Bearer {simtech_token}"},
        )
        assert response.status_code == 403

    async def test_refresh_port_as_admin(self, client, admin_token, discovered_port):
        """Admin should be able to refresh port status."""
        response = await client.post(
            f"/api/discovery/ports/{discovered_port.id}/refresh",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["port_name"] == "GigabitEthernet0/15"

    async def test_refresh_port_not_found(self, client, admin_token):
        """Should return 404 for non-existent port."""
        response = await client.post(
            "/api/discovery/ports/99999/refresh",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404
