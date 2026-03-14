"""
Tests for activity logs endpoints.
"""

import pytest

from app.models.activity_log import ActivityLog
from app.models.simulator import Simulator
from app.models.user import User
from app.services.auth import AuthService


@pytest.fixture
async def admin_user(db_session):
    """Create an admin user for testing."""
    user = User(
        username="logsadmin",
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
        username="logssimtech",
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
        name="Log Test Simulator",
        short_name="LTS",
        icon_path="/icons/lts.png",
    )
    db_session.add(simulator)
    await db_session.commit()
    await db_session.refresh(simulator)
    return simulator


@pytest.fixture
async def test_activity_log(db_session, admin_user, test_simulator):
    """Create a test activity log."""
    log = ActivityLog(
        user_id=admin_user.id,
        simulator_id=test_simulator.id,
        action="enable",
        vlan=30,
        timeout_hours=4,
        details={"note": "Test log entry"},
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)
    return log


@pytest.mark.asyncio
class TestActivityLogsEndpoints:
    """Tests for activity logs endpoints."""

    async def test_list_logs_requires_admin(self, client, simtech_token):
        """Non-admin users should not access activity logs."""
        response = await client.get(
            "/api/logs",
            headers={"Authorization": f"Bearer {simtech_token}"},
        )
        assert response.status_code == 403

    async def test_list_logs_requires_auth(self, client):
        """Unauthenticated users should not access activity logs."""
        response = await client.get("/api/logs")
        assert response.status_code == 401

    async def test_list_logs_as_admin(self, client, admin_token, test_activity_log):
        """Admin should be able to list activity logs."""
        response = await client.get(
            "/api/logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

    async def test_list_logs_pagination(self, client, admin_token, test_activity_log):
        """Should support pagination parameters."""
        response = await client.get(
            "/api/logs?limit=10&offset=0",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0

    async def test_list_logs_filter_by_action(self, client, admin_token, test_activity_log):
        """Should filter logs by action."""
        response = await client.get(
            "/api/logs?action=enable",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        # All returned logs should have action=enable
        for log in data["logs"]:
            assert log["action"] == "enable"

    async def test_list_logs_filter_by_simulator(
        self, client, admin_token, test_activity_log, test_simulator
    ):
        """Should filter logs by simulator."""
        response = await client.get(
            f"/api/logs?simulator_id={test_simulator.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        # Should have at least our test log
        assert data["total"] >= 1

    async def test_list_logs_filter_by_user(
        self, client, admin_token, test_activity_log, admin_user
    ):
        """Should filter logs by user."""
        response = await client.get(
            f"/api/logs?user_id={admin_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        # Should have at least our test log
        assert data["total"] >= 1

    async def test_list_logs_limit_validation(self, client, admin_token):
        """Should validate limit parameter bounds."""
        # Limit too high
        response = await client.get(
            "/api/logs?limit=1000",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 422  # Validation error

        # Limit too low
        response = await client.get(
            "/api/logs?limit=0",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestActivityLogModel:
    """Tests for ActivityLog model."""

    async def test_activity_log_creation(self, test_activity_log):
        """Activity log should be created with correct values."""
        assert test_activity_log.action == "enable"
        assert test_activity_log.vlan == 30
        assert test_activity_log.timeout_hours == 4
        assert test_activity_log.details == {"note": "Test log entry"}

    async def test_activity_log_timestamp_auto(self, test_activity_log):
        """Activity log should have auto-generated timestamp."""
        assert test_activity_log.timestamp is not None


@pytest.mark.asyncio
class TestActivityLogsDateFiltering:
    """Tests for activity log date filtering."""

    async def test_filter_by_date_range(self, client, admin_token, test_activity_log):
        """Should filter logs by date range."""
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        start = (now - timedelta(days=1)).isoformat()
        end = (now + timedelta(days=1)).isoformat()

        response = await client.get(
            f"/api/logs?start_date={start}&end_date={end}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_filter_no_results(self, client, admin_token):
        """Should return empty when no logs match filter."""
        response = await client.get(
            "/api/logs?action=nonexistent_action",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    async def test_pagination_offset(self, client, admin_token, test_activity_log):
        """Should respect pagination offset."""
        response = await client.get(
            "/api/logs?limit=10&offset=1000",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 0  # No logs at this offset
