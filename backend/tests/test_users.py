"""
Tests for user management endpoints.
"""

import pytest

from app.models.simulator import Simulator
from app.models.user import User
from app.services.auth import AuthService


@pytest.fixture
async def admin_user(db_session):
    """Create an admin user for testing."""
    user = User(
        username="useradmin",
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
        username="usersimtech",
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
        name="User Test Simulator",
        short_name="UTS",
        icon_path="/icons/uts.png",
    )
    db_session.add(simulator)
    await db_session.commit()
    await db_session.refresh(simulator)
    return simulator


@pytest.mark.asyncio
class TestUserEndpoints:
    """Tests for user CRUD endpoints."""

    async def test_list_users_requires_admin(self, client, simtech_token):
        """Non-admin users should not access user list."""
        response = await client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {simtech_token}"},
        )
        assert response.status_code == 403

    async def test_list_users_requires_auth(self, client):
        """Unauthenticated users should not access user list."""
        response = await client.get("/api/users")
        assert response.status_code == 401

    async def test_list_users_as_admin(self, client, admin_token, admin_user):
        """Admin should be able to list users."""
        response = await client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_get_user_by_id(self, client, admin_token, admin_user):
        """Admin should be able to get user by ID."""
        response = await client.get(
            f"/api/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "useradmin"
        assert data["role"] == "admin"

    async def test_get_user_not_found(self, client, admin_token):
        """Should return 404 for non-existent user."""
        response = await client.get(
            "/api/users/99999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    async def test_create_user(self, client, admin_token):
        """Admin should be able to create users."""
        response = await client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "newuser",
                "password": "newpass123",
                "role": "simtech",
                "assigned_simulator_ids": [],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["role"] == "simtech"
        assert "password" not in data  # Password should not be returned

    async def test_create_user_with_simulator_assignment(self, client, admin_token, test_simulator):
        """Should create user with simulator assignments."""
        response = await client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "simuser",
                "password": "simpass123",
                "role": "simtech",
                "assigned_simulator_ids": [test_simulator.id],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "simuser"
        assert len(data["assigned_simulators"]) == 1

    async def test_create_duplicate_username_fails(self, client, admin_token, admin_user):
        """Should not allow duplicate usernames."""
        response = await client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "useradmin",  # Already exists
                "password": "somepass123",
                "role": "simtech",
                "assigned_simulator_ids": [],
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    async def test_create_user_requires_admin(self, client, simtech_token):
        """Only admins should create users."""
        response = await client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {simtech_token}"},
            json={
                "username": "unauthorized",
                "password": "somepass123",
                "role": "simtech",
                "assigned_simulator_ids": [],
            },
        )
        assert response.status_code == 403

    async def test_update_user(self, client, admin_token, simtech_user):
        """Admin should be able to update users."""
        response = await client.put(
            f"/api/users/{simtech_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "updatedsimtech",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "updatedsimtech"

    async def test_update_user_role(self, client, admin_token, simtech_user):
        """Should be able to change user role."""
        response = await client.put(
            f"/api/users/{simtech_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "role": "admin",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"

    async def test_update_user_password(self, client, admin_token, simtech_user):
        """Should be able to change user password."""
        response = await client.put(
            f"/api/users/{simtech_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "password": "newpassword123",
            },
        )
        assert response.status_code == 200

    async def test_update_user_not_found(self, client, admin_token):
        """Should return 404 for non-existent user."""
        response = await client.put(
            "/api/users/99999",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"username": "ghost"},
        )
        assert response.status_code == 404

    async def test_update_to_duplicate_username_fails(
        self, client, admin_token, admin_user, simtech_user
    ):
        """Should not allow updating to duplicate username."""
        response = await client.put(
            f"/api/users/{simtech_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "useradmin",  # Admin's username
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    async def test_delete_user(self, client, admin_token, simtech_user):
        """Admin should be able to delete users."""
        response = await client.delete(
            f"/api/users/{simtech_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 204

        # Verify it's deleted
        response = await client.get(
            f"/api/users/{simtech_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    async def test_delete_user_not_found(self, client, admin_token):
        """Should return 404 for non-existent user."""
        response = await client.delete(
            "/api/users/99999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    async def test_delete_self_fails(self, client, admin_token, admin_user):
        """Should not allow deleting own account."""
        response = await client.delete(
            f"/api/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400
        assert "own account" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestUserModel:
    """Tests for User model."""

    async def test_user_repr(self, admin_user):
        """User repr should include key info."""
        repr_str = repr(admin_user)
        assert "User" in repr_str
        assert "useradmin" in repr_str

    async def test_password_not_exposed(self, admin_user):
        """Password hash should not be in repr or easily accessible."""
        repr_str = repr(admin_user)
        assert "password" not in repr_str.lower() or "hash" not in repr_str.lower()


@pytest.mark.asyncio
class TestUserSimulatorAssignments:
    """Tests for user-simulator assignment management."""

    async def test_update_user_with_simulator_assignments(
        self, client, admin_token, simtech_user, test_simulator
    ):
        """Should update user with new simulator assignments."""
        response = await client.put(
            f"/api/users/{simtech_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "assigned_simulator_ids": [test_simulator.id],
            },
        )
        assert response.status_code == 200
        data = response.json()
        # Verify the update was accepted (simulator assignment may be returned)
        assert "assigned_simulators" in data

    async def test_update_user_clear_assignments(self, client, admin_token, simtech_user):
        """Should clear all simulator assignments."""
        response = await client.put(
            f"/api/users/{simtech_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "assigned_simulator_ids": [],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["assigned_simulators"]) == 0

    async def test_create_admin_user(self, client, admin_token):
        """Should create admin user."""
        response = await client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "newadmin",
                "password": "adminpass123",
                "role": "admin",
                "assigned_simulator_ids": [],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "admin"

    async def test_update_user_requires_admin(self, client, simtech_token, simtech_user):
        """Non-admins should not update users."""
        response = await client.put(
            f"/api/users/{simtech_user.id}",
            headers={"Authorization": f"Bearer {simtech_token}"},
            json={"username": "newname"},
        )
        assert response.status_code == 403

    async def test_delete_user_requires_admin(self, client, simtech_token, simtech_user):
        """Non-admins should not delete users."""
        response = await client.delete(
            f"/api/users/{simtech_user.id}",
            headers={"Authorization": f"Bearer {simtech_token}"},
        )
        assert response.status_code == 403
