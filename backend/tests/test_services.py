"""
Tests for service layer components.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.services.encryption import EncryptionService
from app.services.scheduler import SchedulerService


class TestEncryptionService:
    """Tests for encryption service."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypted data should decrypt to original."""
        service = EncryptionService()
        plaintext = "my-secret-password-123"

        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypted_differs_from_plaintext(self):
        """Encrypted data should differ from plaintext."""
        service = EncryptionService()
        plaintext = "my-secret-password-123"

        encrypted = service.encrypt(plaintext)

        assert encrypted != plaintext

    def test_different_encryptions_produce_different_ciphertext(self):
        """Same plaintext should produce different ciphertext each time (due to IV)."""
        service = EncryptionService()
        plaintext = "my-secret-password-123"

        encrypted1 = service.encrypt(plaintext)
        encrypted2 = service.encrypt(plaintext)

        assert encrypted1 != encrypted2

    def test_generate_key(self):
        """Generated key should be valid Fernet key format."""
        key = EncryptionService.generate_key()

        assert key is not None
        assert isinstance(key, str)
        # Fernet keys are 44 characters base64
        assert len(key) == 44


@pytest.mark.asyncio
class TestSchedulerService:
    """Tests for scheduler service."""

    async def test_scheduler_starts_and_stops(self):
        """Scheduler should start and stop without errors."""
        service = SchedulerService()

        service.start()
        assert service.scheduler.running is True

        service.shutdown()
        # Give event loop time to process async shutdown
        await asyncio.sleep(0.01)
        assert service.scheduler.running is False

    async def test_schedule_port_disable(self):
        """Should schedule a job for port disable."""
        service = SchedulerService()
        service.start()

        try:
            future_time = datetime.now(UTC) + timedelta(hours=1)
            job_id = service.schedule_port_disable(port_assignment_id=1, disable_at=future_time)

            assert job_id == "auto_disable_port_1"

            # Verify job exists
            jobs = service.get_scheduled_jobs()
            job_ids = [j["id"] for j in jobs]
            assert "auto_disable_port_1" in job_ids
        finally:
            service.shutdown()

    async def test_cancel_port_disable(self):
        """Should cancel a scheduled job."""
        service = SchedulerService()
        service.start()

        try:
            future_time = datetime.now(UTC) + timedelta(hours=1)
            service.schedule_port_disable(port_assignment_id=1, disable_at=future_time)

            # Cancel the job
            result = service.cancel_port_disable(port_assignment_id=1)
            assert result is True

            # Verify job no longer exists
            jobs = service.get_scheduled_jobs()
            job_ids = [j["id"] for j in jobs]
            assert "auto_disable_port_1" not in job_ids
        finally:
            service.shutdown()

    async def test_cancel_nonexistent_job(self):
        """Canceling non-existent job should return False."""
        service = SchedulerService()
        service.start()

        try:
            result = service.cancel_port_disable(port_assignment_id=999)
            assert result is False
        finally:
            service.shutdown()

    async def test_reschedule_replaces_existing_job(self):
        """Rescheduling should replace existing job."""
        service = SchedulerService()
        service.start()

        try:
            time1 = datetime.now(UTC) + timedelta(hours=1)
            time2 = datetime.now(UTC) + timedelta(hours=2)

            service.schedule_port_disable(port_assignment_id=1, disable_at=time1)
            service.schedule_port_disable(port_assignment_id=1, disable_at=time2)

            # Should only have one job
            jobs = service.get_scheduled_jobs()
            matching_jobs = [j for j in jobs if j["id"] == "auto_disable_port_1"]
            assert len(matching_jobs) == 1
        finally:
            service.shutdown()

    async def test_get_scheduled_jobs_returns_job_info(self):
        """Should return detailed job information."""
        service = SchedulerService()
        service.start()

        try:
            future_time = datetime.now(UTC) + timedelta(hours=1)
            service.schedule_port_disable(port_assignment_id=42, disable_at=future_time)

            jobs = service.get_scheduled_jobs()
            job = next((j for j in jobs if j["id"] == "auto_disable_port_42"), None)

            assert job is not None
            assert "next_run_time" in job
            assert "name" in job
        finally:
            service.shutdown()

    async def test_scheduler_property(self):
        """Scheduler property should return the scheduler instance."""
        service = SchedulerService()
        assert service.scheduler is not None
        assert service.scheduler == service._scheduler


@pytest.mark.asyncio
class TestSchedulerRestoreJobs:
    """Tests for scheduler job restoration."""

    async def test_restore_scheduled_jobs(self, db_session):
        """Should restore jobs for enabled ports."""
        from unittest.mock import AsyncMock, patch

        from app.models.port_assignment import PortAssignment
        from app.models.simulator import Simulator
        from app.models.switch import Switch
        from app.services.encryption import EncryptionService

        # Create test data
        encryption = EncryptionService()
        switch = Switch(
            name="RestoreTest Switch",
            ip_address="192.168.1.100",
            username="admin",
            password_encrypted=encryption.encrypt("pass"),
        )
        db_session.add(switch)

        simulator = Simulator(
            name="RestoreTest Simulator",
            short_name="RTS",
        )
        db_session.add(simulator)
        await db_session.commit()
        await db_session.refresh(switch)
        await db_session.refresh(simulator)

        # Create enabled port with future auto-disable time
        future_time = datetime.now(UTC) + timedelta(hours=2)
        port = PortAssignment(
            simulator_id=simulator.id,
            switch_id=switch.id,
            port_number="Gi0/1",
            vlan=30,
            timeout_hours=4,
            status="enabled",
            enabled_at=datetime.now(UTC),
            auto_disable_at=future_time,
        )
        db_session.add(port)
        await db_session.commit()

        # Test restore
        service = SchedulerService()
        service.start()

        try:
            # Mock the session maker to return our session
            with patch("app.services.scheduler.async_session_maker") as mock_maker:
                mock_maker.return_value.__aenter__ = AsyncMock(return_value=db_session)
                mock_maker.return_value.__aexit__ = AsyncMock(return_value=None)

                await service.restore_scheduled_jobs()

            # Should have scheduled a job
            jobs = service.get_scheduled_jobs()
            job_ids = [j["id"] for j in jobs]
            assert f"auto_disable_port_{port.id}" in job_ids
        finally:
            service.shutdown()


@pytest.mark.asyncio
class TestSchedulerSingleton:
    """Tests for scheduler singleton."""

    async def test_get_scheduler_service_singleton(self):
        """Should return same instance."""
        from app.services.scheduler import get_scheduler_service

        service1 = get_scheduler_service()
        service2 = get_scheduler_service()

        assert service1 is service2
