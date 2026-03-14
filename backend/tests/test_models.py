"""
Tests for model properties and methods.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.models.port_assignment import PortAssignment
from app.models.simulator import Simulator
from app.models.switch import Switch
from app.models.user import User
from app.services.auth import AuthService
from app.services.encryption import EncryptionService


@pytest.fixture
async def test_simulator(db_session):
    """Create a test simulator."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    simulator = Simulator(
        name="Model Test Simulator",
        short_name="MTS",
        icon_path="/icons/mts.png",
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


@pytest.fixture
async def test_switch(db_session):
    """Create a test switch."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    encryption = EncryptionService()
    switch = Switch(
        name="Model Test Switch",
        ip_address="10.0.0.1",
        username="admin",
        password_encrypted=encryption.encrypt("testpass"),
        device_type="cisco_ios",
    )
    db_session.add(switch)
    await db_session.commit()

    # Reload with relationships eagerly loaded
    result = await db_session.execute(
        select(Switch).where(Switch.id == switch.id).options(selectinload(Switch.port_assignments))
    )
    return result.scalar_one()


@pytest.fixture
async def test_user(db_session):
    """Create a test user."""
    user = User(
        username="modeluser",
        password_hash=AuthService.get_password_hash("testpass123"),
        role="simtech",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
class TestSimulatorModel:
    """Tests for Simulator model properties."""

    async def test_has_active_ports_empty(self, test_simulator):
        """Simulator with no ports should return False."""
        assert test_simulator.has_active_ports is False

    async def test_active_port_count_empty(self, test_simulator):
        """Simulator with no ports should have count of 0."""
        assert test_simulator.active_port_count == 0

    async def test_port_count_empty(self, test_simulator):
        """Simulator with no ports should have count of 0."""
        assert len(test_simulator.port_assignments) == 0

    async def test_simulator_timestamps(self, test_simulator):
        """Simulator should have auto-generated timestamps."""
        assert test_simulator.created_at is not None

    async def test_simulator_fields(self, test_simulator):
        """Simulator fields should be set correctly."""
        assert test_simulator.name == "Model Test Simulator"
        assert test_simulator.short_name == "MTS"
        assert test_simulator.icon_path == "/icons/mts.png"


@pytest.mark.asyncio
class TestSwitchModel:
    """Tests for Switch model properties."""

    async def test_switch_port_count_empty(self, test_switch):
        """Switch with no ports should have count of 0."""
        assert test_switch.port_count == 0

    async def test_switch_timestamps(self, test_switch):
        """Switch should have auto-generated timestamps."""
        assert test_switch.created_at is not None
        assert test_switch.updated_at is not None

    async def test_switch_fields(self, test_switch):
        """Switch fields should be set correctly."""
        assert test_switch.name == "Model Test Switch"
        assert test_switch.ip_address == "10.0.0.1"
        assert test_switch.username == "admin"
        assert test_switch.device_type == "cisco_ios"


@pytest.mark.asyncio
class TestPortAssignmentModel:
    """Tests for PortAssignment model properties."""

    async def test_port_assignment_creation(self, db_session, test_simulator, test_switch):
        """Port assignment should be created with correct defaults."""
        port = PortAssignment(
            simulator_id=test_simulator.id,
            switch_id=test_switch.id,
            port_number="Gi0/1",
        )
        db_session.add(port)
        await db_session.commit()
        await db_session.refresh(port)

        assert port.vlan == 30  # Default
        assert port.timeout_hours == 4  # Default
        assert port.status == "disabled"  # Default

    async def test_is_enabled_disabled(self, db_session, test_simulator, test_switch):
        """is_enabled should return False when status is disabled."""
        port = PortAssignment(
            simulator_id=test_simulator.id,
            switch_id=test_switch.id,
            port_number="Gi0/2",
            status="disabled",
        )
        db_session.add(port)
        await db_session.commit()

        assert port.is_enabled is False

    async def test_is_enabled_enabled(self, db_session, test_simulator, test_switch):
        """is_enabled should return True when status is enabled."""
        port = PortAssignment(
            simulator_id=test_simulator.id,
            switch_id=test_switch.id,
            port_number="Gi0/3",
            status="enabled",
        )
        db_session.add(port)
        await db_session.commit()

        assert port.is_enabled is True

    async def test_seconds_remaining_disabled(self, db_session, test_simulator, test_switch):
        """seconds_remaining should be None when disabled."""
        port = PortAssignment(
            simulator_id=test_simulator.id,
            switch_id=test_switch.id,
            port_number="Gi0/4",
            status="disabled",
        )
        db_session.add(port)
        await db_session.commit()

        assert port.seconds_remaining is None

    async def test_seconds_remaining_no_auto_disable(self, db_session, test_simulator, test_switch):
        """seconds_remaining should be None when no auto_disable_at set."""
        port = PortAssignment(
            simulator_id=test_simulator.id,
            switch_id=test_switch.id,
            port_number="Gi0/5",
            status="enabled",
            auto_disable_at=None,
        )
        db_session.add(port)
        await db_session.commit()

        assert port.seconds_remaining is None

    async def test_seconds_remaining_future(self, db_session, test_simulator, test_switch):
        """seconds_remaining should return positive value for future time."""
        future_time = datetime.now(UTC) + timedelta(hours=2)
        port = PortAssignment(
            simulator_id=test_simulator.id,
            switch_id=test_switch.id,
            port_number="Gi0/6",
            status="enabled",
            auto_disable_at=future_time,
        )
        db_session.add(port)
        await db_session.commit()

        remaining = port.seconds_remaining
        assert remaining is not None
        assert remaining > 0
        # Should be approximately 2 hours (7200 seconds)
        assert 7000 < remaining < 7400

    async def test_seconds_remaining_past(self, db_session, test_simulator, test_switch):
        """seconds_remaining should return 0 for past time."""
        past_time = datetime.now(UTC) - timedelta(hours=1)
        port = PortAssignment(
            simulator_id=test_simulator.id,
            switch_id=test_switch.id,
            port_number="Gi0/7",
            status="enabled",
            auto_disable_at=past_time,
        )
        db_session.add(port)
        await db_session.commit()

        assert port.seconds_remaining == 0


@pytest.mark.asyncio
class TestUserModel:
    """Tests for User model properties."""

    async def test_user_timestamps(self, test_user):
        """User should have auto-generated timestamps."""
        assert test_user.created_at is not None

    async def test_user_fields(self, test_user):
        """User fields should be set correctly."""
        assert test_user.username == "modeluser"
        assert test_user.role == "simtech"
        assert test_user.password_hash is not None
        assert test_user.password_hash != "testpass123"  # Should be hashed

    async def test_user_password_verification(self, test_user):
        """Password should be verifiable."""
        assert AuthService.verify_password("testpass123", test_user.password_hash)
        assert not AuthService.verify_password("wrongpass", test_user.password_hash)
