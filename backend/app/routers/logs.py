# =============================================================================
# Activity Logs Router
# =============================================================================
"""
Activity log endpoints (admin only).
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Query
from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from app.dependencies import AdminUser, DbSession
from app.models.activity_log import ActivityLog
from app.models.port_assignment import PortAssignment
from app.schemas.activity_log import ActivityLogListOut, ActivityLogOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/logs", tags=["Activity Logs"])


@router.get("", response_model=ActivityLogListOut)
async def list_activity_logs(
    db: DbSession,
    admin: AdminUser,
    simulator_id: int | None = Query(None, description="Filter by simulator"),
    user_id: int | None = Query(None, description="Filter by user"),
    action: str | None = Query(None, description="Filter by action (enable/disable/auto_disable)"),
    start_date: datetime | None = Query(None, description="Filter from date"),
    end_date: datetime | None = Query(None, description="Filter to date"),
    limit: int = Query(50, ge=1, le=500, description="Number of records"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> ActivityLogListOut:
    """
    List activity logs with optional filtering (admin only).

    Returns paginated list of port control events.
    """
    # Build query
    query = select(ActivityLog).options(
        selectinload(ActivityLog.user),
        selectinload(ActivityLog.simulator),
        selectinload(ActivityLog.port_assignment).selectinload(PortAssignment.switch),
    )

    # Apply filters
    filters = []
    if simulator_id is not None:
        filters.append(ActivityLog.simulator_id == simulator_id)
    if user_id is not None:
        filters.append(ActivityLog.user_id == user_id)
    if action is not None:
        filters.append(ActivityLog.action == action)
    if start_date is not None:
        filters.append(ActivityLog.timestamp >= start_date)
    if end_date is not None:
        filters.append(ActivityLog.timestamp <= end_date)

    if filters:
        query = query.where(and_(*filters))

    # Get total count
    count_result = await db.execute(
        select(ActivityLog.id).where(and_(*filters)) if filters else select(ActivityLog.id)
    )
    total = len(count_result.scalars().all())

    # Apply pagination and ordering
    query = query.order_by(ActivityLog.timestamp.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    # Convert to response schema
    log_items = []
    for log in logs:
        log_items.append(
            ActivityLogOut(
                id=log.id,
                timestamp=log.timestamp,
                username=log.username,
                simulator_name=log.simulator_name,
                port_number=log.port_assignment.port_number if log.port_assignment else None,
                switch_name=log.port_assignment.switch.name if log.port_assignment else None,
                action=log.action,
                vlan=log.vlan,
                timeout_hours=log.timeout_hours,
                details=log.details,
            )
        )

    return ActivityLogListOut(
        logs=log_items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.delete("")
async def clear_activity_logs(
    db: DbSession,
    admin: AdminUser,
) -> dict:
    """
    Clear all activity logs (admin only).

    Returns count of deleted logs.
    """
    # Get count before deletion
    count_result = await db.execute(select(ActivityLog.id))
    count = len(count_result.scalars().all())

    # Delete all logs
    await db.execute(ActivityLog.__table__.delete())
    await db.commit()

    logger.info(f"Admin {admin.username} cleared {count} activity logs")

    return {"deleted": count, "message": f"Cleared {count} activity logs"}
