"""
Tests for simulator endpoints.
"""

import pytest

from app.models.simulator import Simulator
from app.models.user import User
from app.services.auth import AuthService


@pytest.fixture
async def admin_user(db_session):
    """Create an admin user for testing."""
    user = User(
        username="simadmin",
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
        username="simsimtech",
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
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    simulator = Simulator(
        name="Test Learjet 45",
        short_name="LJ45",
        icon_path="/icons/lj45_wht.png",
    )
    db_session.add(simulator)
    await db_session.commit()

    # Reload with relationships eagerly loaded
    result = await db_session.execute(
        select(Simulator)
        .where(Simulator.id == simulator.id)
        .options(selectinload(Simulator.port_assignments))
    )
    return result.scalar_one()


@pytest.mark.asyncio
class TestSimulatorEndpoints:
    """Tests for simulator CRUD endpoints."""

    async def test_list_simulators_requires_auth(self, client):
        """Simulator list should require authentication."""
        response = await client.get("/api/simulators")
        assert response.status_code == 401

    async def test_list_simulators_as_simtech(self, client, simtech_token, test_simulator):
        """Simtech users should see simulators."""
        response = await client.get(
            "/api/simulators",
            headers={"Authorization": f"Bearer {simtech_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "simulators" in data

    async def test_list_simulators_as_admin(self, client, admin_token, test_simulator):
        """Admin users should see simulators."""
        response = await client.get(
            "/api/simulators",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "simulators" in data
        assert len(data["simulators"]) >= 1

    async def test_get_simulator_by_id(self, client, admin_token, test_simulator):
        """Should get simulator by ID."""
        response = await client.get(
            f"/api/simulators/{test_simulator.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Learjet 45"
        assert data["short_name"] == "LJ45"

    async def test_get_simulator_not_found(self, client, admin_token):
        """Should return 404 for non-existent simulator."""
        response = await client.get(
            "/api/simulators/99999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    async def test_create_simulator_as_admin(self, client, admin_token):
        """Admin should be able to create simulators."""
        response = await client.post(
            "/api/simulators",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "New Simulator",
                "short_name": "NEW",
                "icon_path": "/icons/new_wht.png",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Simulator"
        assert data["short_name"] == "NEW"

    async def test_create_simulator_minimal(self, client, admin_token):
        """Should create simulator with minimal fields."""
        response = await client.post(
            "/api/simulators",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Minimal Sim",
                "short_name": "MIN",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Sim"

    async def test_create_simulator_requires_admin(self, client, simtech_token):
        """Only admins should create simulators."""
        response = await client.post(
            "/api/simulators",
            headers={"Authorization": f"Bearer {simtech_token}"},
            json={
                "name": "Unauthorized Sim",
                "short_name": "UNAUTH",
            },
        )
        assert response.status_code == 403

    async def test_update_simulator(self, client, admin_token, test_simulator):
        """Admin should be able to update simulators."""
        response = await client.put(
            f"/api/simulators/{test_simulator.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Updated Learjet 45",
                "short_name": "LJ45X",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Learjet 45"
        assert data["short_name"] == "LJ45X"

    async def test_update_simulator_partial(self, client, admin_token, test_simulator):
        """Should allow partial updates."""
        original_short_name = test_simulator.short_name
        response = await client.put(
            f"/api/simulators/{test_simulator.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Only Name Changed",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Only Name Changed"
        assert data["short_name"] == original_short_name

    async def test_update_simulator_not_found(self, client, admin_token):
        """Should return 404 for non-existent simulator."""
        response = await client.put(
            "/api/simulators/99999",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Ghost Sim"},
        )
        assert response.status_code == 404

    async def test_delete_simulator(self, client, admin_token, test_simulator):
        """Admin should be able to delete simulators."""
        response = await client.delete(
            f"/api/simulators/{test_simulator.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 204

        # Verify it's deleted
        response = await client.get(
            f"/api/simulators/{test_simulator.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    async def test_delete_simulator_not_found(self, client, admin_token):
        """Should return 404 for non-existent simulator."""
        response = await client.delete(
            "/api/simulators/99999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    async def test_delete_simulator_requires_admin(self, client, simtech_token, test_simulator):
        """Only admins should delete simulators."""
        response = await client.delete(
            f"/api/simulators/{test_simulator.id}",
            headers={"Authorization": f"Bearer {simtech_token}"},
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestSimulatorModel:
    """Tests for Simulator model."""

    async def test_simulator_repr(self, test_simulator):
        """Simulator repr should include key info."""
        repr_str = repr(test_simulator)
        assert "Simulator" in repr_str
        assert "LJ45" in repr_str

    async def test_simulator_port_count_empty(self, test_simulator):
        """Simulator with no ports should have count of 0."""
        assert len(test_simulator.port_assignments) == 0
        assert test_simulator.active_port_count == 0


@pytest.mark.asyncio
class TestSimulatorAccessControl:
    """Tests for simulator access control."""

    async def test_update_simulator_requires_admin(self, client, simtech_token, test_simulator):
        """Non-admins should not update simulators."""
        response = await client.put(
            f"/api/simulators/{test_simulator.id}",
            headers={"Authorization": f"Bearer {simtech_token}"},
            json={"name": "Unauthorized Update"},
        )
        assert response.status_code == 403

    async def test_create_simulator_requires_admin(self, client, simtech_token):
        """Non-admins should not create simulators."""
        response = await client.post(
            "/api/simulators",
            headers={"Authorization": f"Bearer {simtech_token}"},
            json={
                "name": "Unauthorized Sim",
                "short_name": "UNAUTH",
            },
        )
        assert response.status_code == 403

    async def test_update_simulator_icon_path(self, client, admin_token, test_simulator):
        """Should update simulator icon path."""
        response = await client.put(
            f"/api/simulators/{test_simulator.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "icon_path": "/icons/new_icon.png",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["icon_path"] == "/icons/new_icon.png"
