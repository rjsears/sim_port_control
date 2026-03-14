"""
Tests for API endpoints.
"""

import pytest

from app.models.simulator import Simulator
from app.models.user import User
from app.services.auth import AuthService


@pytest.fixture
async def admin_user(db_session):
    """Create an admin user for testing."""
    user = User(
        username="testadmin",
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
        username="testsimtech",
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
        name="Test Simulator CJ3",
        short_name="CJ3",
        icon_path="/icons/cj3_wht.png",
    )
    db_session.add(simulator)
    await db_session.commit()
    await db_session.refresh(simulator)
    return simulator


@pytest.mark.asyncio
class TestUserEndpoints:
    """Tests for user management endpoints."""

    async def test_list_users_requires_admin(self, client, simtech_token):
        """Non-admin users should not access user list."""
        response = await client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {simtech_token}"},
        )
        assert response.status_code == 403

    async def test_list_users_as_admin(self, client, admin_token, admin_user):
        """Admin should be able to list users."""
        response = await client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        # API returns a list directly
        assert isinstance(data, list)
        assert len(data) >= 1  # At least the admin user

    async def test_create_user_as_admin(self, client, admin_token):
        """Admin should be able to create users."""
        response = await client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "newuser",
                "password": "newpass123",
                "role": "simtech",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["role"] == "simtech"
        assert "password" not in data  # Password should not be returned


@pytest.mark.asyncio
class TestSimulatorEndpoints:
    """Tests for simulator endpoints."""

    async def test_list_simulators_requires_auth(self, client):
        """Simulator list should require authentication."""
        response = await client.get("/api/simulators")
        assert response.status_code == 401

    async def test_list_simulators_authenticated(self, client, simtech_token, test_simulator):
        """Authenticated users should see simulators."""
        response = await client.get(
            "/api/simulators",
            headers={"Authorization": f"Bearer {simtech_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "simulators" in data

    async def test_create_simulator_requires_admin(self, client, simtech_token):
        """Only admins should create simulators."""
        response = await client.post(
            "/api/simulators",
            headers={"Authorization": f"Bearer {simtech_token}"},
            json={
                "name": "New Simulator",
                "short_name": "NEW",
            },
        )
        assert response.status_code == 403

    async def test_create_simulator_as_admin(self, client, admin_token):
        """Admin should be able to create simulators."""
        response = await client.post(
            "/api/simulators",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Challenger 350",
                "short_name": "CL350",
                "icon_path": "/icons/cl350_wht.png",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Challenger 350"
        assert data["short_name"] == "CL350"


@pytest.mark.asyncio
class TestAuthorizationFlow:
    """Tests for authentication flow."""

    async def test_full_login_flow(self, client, admin_user):
        """Test complete login and authenticated request flow."""
        # Login
        login_response = await client.post(
            "/api/auth/login",
            data={
                "username": "testadmin",
                "password": "adminpass123",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Use token for authenticated request
        me_response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.status_code == 200
        user_data = me_response.json()
        assert user_data["username"] == "testadmin"
        assert user_data["role"] == "admin"
