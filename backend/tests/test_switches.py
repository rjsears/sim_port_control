"""
Tests for switch management endpoints.
"""

import pytest

from app.models.switch import Switch
from app.models.user import User
from app.services.auth import AuthService
from app.services.encryption import EncryptionService


@pytest.fixture
async def admin_user(db_session):
    """Create an admin user for testing."""
    user = User(
        username="switchadmin",
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
        username="switchsimtech",
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
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    encryption = EncryptionService()
    switch = Switch(
        name="Test Switch 1",
        ip_address="192.168.1.1",
        username="admin",
        password_encrypted=encryption.encrypt("switchpassword"),
        device_type="cisco_ios",
    )
    db_session.add(switch)
    await db_session.commit()

    # Reload with relationships eagerly loaded
    result = await db_session.execute(
        select(Switch).where(Switch.id == switch.id).options(selectinload(Switch.port_assignments))
    )
    return result.scalar_one()


@pytest.mark.asyncio
class TestSwitchEndpoints:
    """Tests for switch CRUD endpoints."""

    async def test_list_switches_requires_admin(self, client, simtech_token):
        """Non-admin users should not access switch list."""
        response = await client.get(
            "/api/switches",
            headers={"Authorization": f"Bearer {simtech_token}"},
        )
        assert response.status_code == 403

    async def test_list_switches_requires_auth(self, client):
        """Unauthenticated users should not access switch list."""
        response = await client.get("/api/switches")
        assert response.status_code == 401

    async def test_list_switches_as_admin(self, client, admin_token, test_switch):
        """Admin should be able to list switches."""
        response = await client.get(
            "/api/switches",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "switches" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_get_switch_by_id(self, client, admin_token, test_switch):
        """Admin should be able to get switch by ID."""
        response = await client.get(
            f"/api/switches/{test_switch.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Switch 1"
        assert data["ip_address"] == "192.168.1.1"

    async def test_get_switch_not_found(self, client, admin_token):
        """Should return 404 for non-existent switch."""
        response = await client.get(
            "/api/switches/99999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    async def test_create_switch_as_admin(self, client, admin_token):
        """Admin should be able to create switches."""
        response = await client.post(
            "/api/switches",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "New Switch",
                "ip_address": "192.168.1.100",
                "username": "admin",
                "password": "secretpass",
                "device_type": "cisco_ios",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Switch"
        assert data["ip_address"] == "192.168.1.100"
        assert "password" not in data  # Password should not be returned

    async def test_create_switch_requires_admin(self, client, simtech_token):
        """Only admins should create switches."""
        response = await client.post(
            "/api/switches",
            headers={"Authorization": f"Bearer {simtech_token}"},
            json={
                "name": "Unauthorized Switch",
                "ip_address": "192.168.1.200",
                "username": "admin",
                "password": "secretpass",
            },
        )
        assert response.status_code == 403

    async def test_update_switch(self, client, admin_token, test_switch):
        """Admin should be able to update switches."""
        response = await client.put(
            f"/api/switches/{test_switch.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Updated Switch Name",
                "ip_address": "192.168.1.50",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Switch Name"
        assert data["ip_address"] == "192.168.1.50"

    async def test_update_switch_partial(self, client, admin_token, test_switch):
        """Should allow partial updates."""
        original_ip = test_switch.ip_address
        response = await client.put(
            f"/api/switches/{test_switch.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Only Name Changed",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Only Name Changed"
        assert data["ip_address"] == original_ip

    async def test_update_switch_not_found(self, client, admin_token):
        """Should return 404 for updating non-existent switch."""
        response = await client.put(
            "/api/switches/99999",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Ghost Switch"},
        )
        assert response.status_code == 404

    async def test_delete_switch(self, client, admin_token, test_switch):
        """Admin should be able to delete switches."""
        response = await client.delete(
            f"/api/switches/{test_switch.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 204

        # Verify it's deleted
        response = await client.get(
            f"/api/switches/{test_switch.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    async def test_delete_switch_not_found(self, client, admin_token):
        """Should return 404 for deleting non-existent switch."""
        response = await client.delete(
            "/api/switches/99999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404


@pytest.mark.asyncio
class TestSwitchModel:
    """Tests for Switch model properties."""

    async def test_switch_port_count_empty(self, db_session):
        """Switch with no ports should have count of 0."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        encryption = EncryptionService()
        switch = Switch(
            name="Empty Switch",
            ip_address="192.168.1.10",
            username="admin",
            password_encrypted=encryption.encrypt("pass"),
            device_type="cisco_ios",
        )
        db_session.add(switch)
        await db_session.commit()

        # Reload with relationships eagerly loaded
        result = await db_session.execute(
            select(Switch)
            .where(Switch.id == switch.id)
            .options(selectinload(Switch.port_assignments))
        )
        switch = result.scalar_one()

        assert switch.port_count == 0

    async def test_switch_repr(self, test_switch):
        """Switch repr should include key info."""
        repr_str = repr(test_switch)
        assert "Switch" in repr_str
        assert "Test Switch 1" in repr_str
        assert "192.168.1.1" in repr_str


@pytest.mark.asyncio
class TestSwitchTestConnection:
    """Tests for switch test connection endpoint."""

    async def test_test_connection_requires_admin(self, client, simtech_token, test_switch):
        """Non-admin users should not test switch connections."""
        response = await client.post(
            f"/api/switches/{test_switch.id}/test",
            headers={"Authorization": f"Bearer {simtech_token}"},
        )
        assert response.status_code == 403

    async def test_test_connection_not_found(self, client, admin_token):
        """Should return 404 for non-existent switch."""
        response = await client.post(
            "/api/switches/99999/test",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    async def test_test_connection_success(self, client, admin_token, test_switch):
        """Should test connection with mocked SSH."""
        from unittest.mock import AsyncMock, MagicMock, patch

        with patch("app.routers.switches.CiscoSSHService") as mock_ssh_class:
            mock_ssh = MagicMock()
            mock_ssh.test_connection_async = AsyncMock(
                return_value={"connected": True, "hostname": "TestSwitch"}
            )
            mock_ssh_class.return_value = mock_ssh

            response = await client.post(
                f"/api/switches/{test_switch.id}/test",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "switch_info" in data

    async def test_test_connection_failure(self, client, admin_token, test_switch):
        """Should return failure when SSH fails."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.services.cisco_ssh import CiscoSSHError

        with patch("app.routers.switches.CiscoSSHService") as mock_ssh_class:
            mock_ssh = MagicMock()
            mock_ssh.test_connection_async = AsyncMock(
                side_effect=CiscoSSHError("Connection refused")
            )
            mock_ssh_class.return_value = mock_ssh

            response = await client.post(
                f"/api/switches/{test_switch.id}/test",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False


@pytest.mark.asyncio
class TestSwitchAutoScan:
    """Tests for switch auto-scan on create."""

    async def test_create_switch_with_auto_scan(self, client, admin_token):
        """Should auto-scan switch on creation (mocked)."""
        from unittest.mock import AsyncMock, MagicMock, patch

        with patch("app.routers.switches.PortDiscoveryService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.scan_switch = AsyncMock(
                return_value={
                    "success": True,
                    "message": "Found 24 ports",
                    "ports_found": 24,
                    "new_ports": 24,
                    "removed_ports": 0,
                }
            )
            mock_service_class.return_value = mock_service

            response = await client.post(
                "/api/switches",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "name": "New Auto-Scan Switch",
                    "ip_address": "192.168.1.200",
                    "username": "admin",
                    "password": "secretpass",
                    "device_type": "cisco_ios",
                },
            )
            assert response.status_code == 201
