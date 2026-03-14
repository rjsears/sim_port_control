# =============================================================================
# Scheduler Service
# =============================================================================
"""
APScheduler-based service for automatic port timeout handling.
"""

import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import async_session_maker
from app.models.port_assignment import PortAssignment

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing scheduled port timeout jobs."""

    def __init__(self) -> None:
        """Initialize scheduler service."""
        self._scheduler: AsyncIOScheduler = AsyncIOScheduler()

    @property
    def scheduler(self) -> AsyncIOScheduler:
        """Get the scheduler instance."""
        return self._scheduler

    def start(self) -> None:
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler shutdown")

    def schedule_port_disable(self, port_assignment_id: int, disable_at: datetime) -> str:
        """
        Schedule automatic port disable.

        Args:
            port_assignment_id: ID of the port assignment to disable.
            disable_at: When to disable the port.

        Returns:
            Job ID for the scheduled job.
        """
        job_id = f"auto_disable_port_{port_assignment_id}"

        # Remove existing job if any
        self.cancel_port_disable(port_assignment_id)

        # Schedule new job
        self.scheduler.add_job(
            self._auto_disable_port,
            trigger=DateTrigger(run_date=disable_at),
            id=job_id,
            args=[port_assignment_id],
            replace_existing=True,
            misfire_grace_time=60,  # Allow 60 seconds grace period
        )

        logger.info(f"Scheduled auto-disable for port {port_assignment_id} at {disable_at}")
        return job_id

    def cancel_port_disable(self, port_assignment_id: int) -> bool:
        """
        Cancel a scheduled port disable job.

        Args:
            port_assignment_id: ID of the port assignment.

        Returns:
            True if job was cancelled, False if no job existed.
        """
        job_id = f"auto_disable_port_{port_assignment_id}"
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Cancelled auto-disable job for port {port_assignment_id}")
            return True
        except Exception:
            return False

    def get_scheduled_jobs(self) -> list[dict]:
        """Get list of all scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "next_run_time": job.next_run_time,
                    "name": job.name,
                }
            )
        return jobs

    async def _auto_disable_port(self, port_assignment_id: int) -> None:
        """
        Internal method to auto-disable a port.

        Args:
            port_assignment_id: ID of the port assignment to disable.
        """
        logger.info(f"Auto-disable triggered for port assignment {port_assignment_id}")

        async with async_session_maker() as db:
            try:
                # Get the port assignment with relationships
                result = await db.execute(
                    select(PortAssignment)
                    .where(PortAssignment.id == port_assignment_id)
                    .options(
                        selectinload(PortAssignment.switch),
                        selectinload(PortAssignment.simulator),
                    )
                )
                port = result.scalar_one_or_none()

                if not port:
                    logger.warning(
                        f"Port assignment {port_assignment_id} not found for auto-disable"
                    )
                    return

                if port.status != "enabled":
                    logger.info(f"Port {port_assignment_id} already disabled, skipping")
                    return

                # Skip force-enabled ports (maintenance mode)
                if port.force_enabled:
                    logger.info(
                        f"Port {port_assignment_id} is force-enabled (maintenance mode), "
                        f"skipping auto-disable. Reason: {port.force_enabled_reason}"
                    )
                    return

                # Import here to avoid circular imports
                from app.services.port_control import PortControlService

                # Disable the port
                service = PortControlService(db)
                await service.disable_port(port, is_auto=True)

                logger.info(f"Auto-disabled port {port.port_number} on {port.switch.name}")

            except Exception as e:
                logger.error(f"Error in auto-disable for port {port_assignment_id}: {e}")
                await db.rollback()

    async def restore_scheduled_jobs(self) -> None:
        """
        Restore scheduled jobs from database for any enabled ports.

        This should be called on application startup to reschedule
        auto-disable jobs that were lost during a restart.
        """
        logger.info("Restoring scheduled jobs from database...")
        restored_count = 0

        async with async_session_maker() as db:
            try:
                result = await db.execute(
                    select(PortAssignment).where(PortAssignment.status == "enabled")
                )
                enabled_ports = result.scalars().all()

                for port in enabled_ports:
                    if port.auto_disable_at:
                        now = datetime.now(UTC)
                        if port.auto_disable_at > now:
                            # Schedule future auto-disable
                            self.schedule_port_disable(port.id, port.auto_disable_at)
                            restored_count += 1
                            logger.debug(
                                f"Restored auto-disable job for port {port.id} "
                                f"at {port.auto_disable_at}"
                            )
                        else:
                            # Port should have been disabled already - trigger immediately
                            logger.warning(
                                f"Port {port.id} missed auto-disable at {port.auto_disable_at}, "
                                "triggering now"
                            )
                            # Schedule for 5 seconds from now to allow startup to complete
                            self.schedule_port_disable(port.id, now + timedelta(seconds=5))
                            restored_count += 1

                logger.info(f"Restored {restored_count} scheduled auto-disable jobs")

            except Exception as e:
                logger.error(f"Error restoring scheduled jobs: {e}")


# Singleton instance
_scheduler_service: SchedulerService | None = None


def get_scheduler_service() -> SchedulerService:
    """Get singleton scheduler service instance."""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service
