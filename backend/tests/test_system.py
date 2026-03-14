"""
Tests for system status and management endpoints.
"""

import pytest

from app.models.user import User
from app.services.auth import AuthService


@pytest.fixture
async def admin_user(db_session):
    """Create an admin user for testing."""
    user = User(
        username="systemadmin",
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
        username="systemsimtech",
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


@pytest.mark.asyncio
class TestHealthEndpoint:
    """Tests for health check endpoint."""

    async def test_health_check_no_auth(self, client):
        """Health check should not require authentication."""
        response = await client.get("/api/system/health")
        assert response.status_code == 200

    async def test_health_check_returns_status(self, client):
        """Health check should return status info."""
        response = await client.get("/api/system/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data


@pytest.mark.asyncio
class TestSystemInfoEndpoint:
    """Tests for system info endpoint."""

    async def test_system_info_requires_admin(self, client, simtech_token):
        """Non-admin users should not access system info."""
        response = await client.get(
            "/api/system/info",
            headers={"Authorization": f"Bearer {simtech_token}"},
        )
        assert response.status_code == 403

    async def test_system_info_requires_auth(self, client):
        """Unauthenticated users should not access system info."""
        response = await client.get("/api/system/info")
        assert response.status_code == 401

    async def test_system_info_as_admin(self, client, admin_token):
        """Admin should be able to get system info."""
        response = await client.get(
            "/api/system/info",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "environment" in data
        assert "database" in data
        assert "scheduler" in data

    async def test_system_info_database_counts(self, client, admin_token, admin_user):
        """System info should include database counts."""
        response = await client.get(
            "/api/system/info",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        data = response.json()
        db_info = data["database"]
        assert "status" in db_info
        assert db_info["status"] == "connected"
        assert "users" in db_info
        assert db_info["users"] >= 1  # At least the admin user

    async def test_system_info_scheduler_status(self, client, admin_token):
        """System info should include scheduler status."""
        response = await client.get(
            "/api/system/info",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        data = response.json()
        scheduler_info = data["scheduler"]
        assert "status" in scheduler_info
        assert "pending_jobs" in scheduler_info
        assert "jobs" in scheduler_info


@pytest.mark.asyncio
class TestSSLEndpoints:
    """Tests for SSL certificate endpoints."""

    async def test_ssl_info_requires_admin(self, client, simtech_token):
        """Non-admin users should not access SSL info."""
        response = await client.get(
            "/api/system/ssl",
            headers={"Authorization": f"Bearer {simtech_token}"},
        )
        assert response.status_code == 403

    async def test_ssl_info_requires_auth(self, client):
        """Unauthenticated users should not access SSL info."""
        response = await client.get("/api/system/ssl")
        assert response.status_code == 401

    async def test_ssl_info_as_admin(self, client, admin_token):
        """Admin should be able to get SSL info."""
        response = await client.get(
            "/api/system/ssl",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # Might return 200 with "not configured" or certificate info
        assert response.status_code == 200
        data = response.json()
        assert "configured" in data
        assert "certificates" in data

    async def test_ssl_renew_requires_admin(self, client, simtech_token):
        """Non-admin users should not renew SSL."""
        response = await client.post(
            "/api/system/ssl/renew",
            headers={"Authorization": f"Bearer {simtech_token}"},
        )
        assert response.status_code == 403

    async def test_ssl_renew_requires_auth(self, client):
        """Unauthenticated users should not renew SSL."""
        response = await client.post("/api/system/ssl/renew")
        assert response.status_code == 401
