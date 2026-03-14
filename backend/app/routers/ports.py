# =============================================================================
# Ports Router
# =============================================================================
"""
Port assignment and control endpoints.
"""

import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.dependencies import AdminUser, CurrentUser, DbSession
from app.models.port_assignment import PortAssignment
from app.schemas.port import (
    ForceEnableRequest,
    ForceEnableResponse,
    PortActionResult,
    PortAssignmentCreate,
    PortAssignmentListOut,
    PortAssignmentOut,
    PortAssignmentUpdate,
    PortEnableRequest,
    PortStatusOut,
)
from app.services.port_control import PortControlError, PortControlService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ports", tags=["Ports"])


def _port_to_out(port: PortAssignment) -> PortAssignmentOut:
    """Convert PortAssignment model to schema."""
    return PortAssignmentOut(
        id=port.id,
        simulator_id=port.simulator_id,
        simulator_name=port.simulator.name,
        switch_id=port.switch_id,
        switch_name=port.switch.name,
        port_number=port.port_number,
        vlan=port.vlan,
        timeout_hours=port.timeout_hours,
        status=port.status,
        enabled_at=port.enabled_at,
        auto_disable_at=port.auto_disable_at,
        enabled_by_username=port.enabled_by.username if port.enabled_by else None,
        seconds_remaining=port.seconds_remaining,
        created_at=port.created_at,
        force_enabled=port.force_enabled,
        force_enabled_by_username=port.force_enabled_by.username if port.force_enabled_by else None,
        force_enabled_at=port.force_enabled_at,
        force_enabled_reason=port.force_enabled_reason,
    )


# =============================================================================
# Port Assignment CRUD (Admin only)
# =============================================================================


@router.get("/assignments", response_model=PortAssignmentListOut)
async def list_port_assignments(db: DbSession, admin: AdminUser) -> PortAssignmentListOut:
    """List all port assignments (admin only)."""
    result = await db.execute(
        select(PortAssignment).options(
            selectinload(PortAssignment.switch),
            selectinload(PortAssignment.simulator),
            selectinload(PortAssignment.enabled_by),
            selectinload(PortAssignment.force_enabled_by),
        )
    )
    ports = result.scalars().all()

    return PortAssignmentListOut(
        port_assignments=[_port_to_out(p) for p in ports],
        total=len(ports),
    )


@router.post("/assignments", response_model=PortAssignmentOut, status_code=status.HTTP_201_CREATED)
async def create_port_assignment(
    data: PortAssignmentCreate, db: DbSession, admin: AdminUser
) -> PortAssignmentOut:
    """Create a new port assignment (admin only)."""
    # Check for duplicate switch/port combination
    result = await db.execute(
        select(PortAssignment).where(
            PortAssignment.switch_id == data.switch_id,
            PortAssignment.port_number == data.port_number,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Port already assigned on this switch",
        )

    port = PortAssignment(
        simulator_id=data.simulator_id,
        switch_id=data.switch_id,
        port_number=data.port_number,
        vlan=data.vlan,
        timeout_hours=data.timeout_hours,
    )
    db.add(port)
    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(PortAssignment)
        .where(PortAssignment.id == port.id)
        .options(
            selectinload(PortAssignment.switch),
            selectinload(PortAssignment.simulator),
        )
    )
    port = result.scalar_one()

    logger.info(f"Created port assignment: {port.switch.name}:{port.port_number}")
    return _port_to_out(port)


@router.put("/assignments/{assignment_id}", response_model=PortAssignmentOut)
async def update_port_assignment(
    assignment_id: int, data: PortAssignmentUpdate, db: DbSession, admin: AdminUser
) -> PortAssignmentOut:
    """Update a port assignment (admin only)."""
    result = await db.execute(
        select(PortAssignment)
        .where(PortAssignment.id == assignment_id)
        .options(
            selectinload(PortAssignment.switch),
            selectinload(PortAssignment.simulator),
            selectinload(PortAssignment.enabled_by),
        )
    )
    port = result.scalar_one_or_none()
    if not port:
        raise HTTPException(status_code=404, detail="Port assignment not found")

    if data.vlan is not None:
        port.vlan = data.vlan
    if data.timeout_hours is not None:
        port.timeout_hours = data.timeout_hours

    await db.commit()
    await db.refresh(port)

    logger.info(f"Updated port assignment: {port.switch.name}:{port.port_number}")
    return _port_to_out(port)


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_port_assignment(assignment_id: int, db: DbSession, admin: AdminUser) -> None:
    """Delete a port assignment (admin only)."""
    result = await db.execute(select(PortAssignment).where(PortAssignment.id == assignment_id))
    port = result.scalar_one_or_none()
    if not port:
        raise HTTPException(status_code=404, detail="Port assignment not found")

    await db.delete(port)
    await db.commit()
    logger.info(f"Deleted port assignment {assignment_id}")


# =============================================================================
# Port Control (Enable/Disable)
# =============================================================================


@router.get("/{port_id}", response_model=PortStatusOut)
async def get_port_status(port_id: int, db: DbSession, current_user: CurrentUser) -> PortStatusOut:
    """Get current status of a port."""
    service = PortControlService(db)
    port = await service.get_port_assignment(port_id)
    if not port:
        raise HTTPException(status_code=404, detail="Port not found")

    # Check access
    if not await service.check_user_access(current_user, port):
        raise HTTPException(status_code=403, detail="Not authorized for this port")

    return PortStatusOut(
        id=port.id,
        simulator_name=port.simulator.name,
        switch_name=port.switch.name,
        port_number=port.port_number,
        vlan=port.vlan,
        status=port.status,
        enabled_at=port.enabled_at,
        auto_disable_at=port.auto_disable_at,
        enabled_by=port.enabled_by.username if port.enabled_by else None,
        seconds_remaining=port.seconds_remaining,
    )


@router.post("/{port_id}/enable", response_model=PortActionResult)
async def enable_port(
    port_id: int,
    db: DbSession,
    current_user: CurrentUser,
    request: PortEnableRequest | None = None,
) -> PortActionResult:
    """
    Enable a switch port.

    Optionally override timeout and VLAN from port assignment defaults.
    """
    service = PortControlService(db)
    port = await service.get_port_assignment(port_id)
    if not port:
        raise HTTPException(status_code=404, detail="Port not found")

    # Check access
    if not await service.check_user_access(current_user, port):
        raise HTTPException(status_code=403, detail="Not authorized for this port")

    # Check if already enabled
    if port.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Port is already enabled",
        )

    try:
        timeout_hours = request.timeout_hours if request else None
        vlan = request.vlan if request else None
        port = await service.enable_port(port, current_user, timeout_hours, vlan)

        return PortActionResult(
            success=True,
            message=f"Port {port.port_number} enabled for {port.simulator.name}",
            port_id=port.id,
            status=port.status,
            auto_disable_at=port.auto_disable_at,
        )
    except PortControlError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/{port_id}/disable", response_model=PortActionResult)
async def disable_port(port_id: int, db: DbSession, current_user: CurrentUser) -> PortActionResult:
    """Disable a switch port."""
    service = PortControlService(db)
    port = await service.get_port_assignment(port_id)
    if not port:
        raise HTTPException(status_code=404, detail="Port not found")

    # Check access
    if not await service.check_user_access(current_user, port):
        raise HTTPException(status_code=403, detail="Not authorized for this port")

    # Check if already disabled
    if not port.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Port is already disabled",
        )

    try:
        port = await service.disable_port(port, current_user)

        return PortActionResult(
            success=True,
            message=f"Port {port.port_number} disabled for {port.simulator.name}",
            port_id=port.id,
            status=port.status,
        )
    except PortControlError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# =============================================================================
# Force Enable (Admin only - Maintenance Mode)
# =============================================================================


@router.post("/{port_id}/force-enable", response_model=ForceEnableResponse)
async def force_enable_port(
    port_id: int,
    request: ForceEnableRequest,
    db: DbSession,
    admin: AdminUser,
) -> ForceEnableResponse:
    """
    Force-enable a port (maintenance mode).

    This bypasses the auto-disable timer. Admin only.
    Requires a reason for audit purposes.
    """
    service = PortControlService(db)
    port = await service.get_port_assignment(port_id)
    if not port:
        raise HTTPException(status_code=404, detail="Port not found")

    port = await service.set_force_enabled(port, admin, enabled=True, reason=request.reason)

    return ForceEnableResponse(
        success=True,
        message=f"Port {port.port_number} is now force-enabled (maintenance mode)",
        port_id=port.id,
        force_enabled=port.force_enabled,
        force_enabled_reason=port.force_enabled_reason,
    )


@router.post("/{port_id}/force-disable", response_model=ForceEnableResponse)
async def force_disable_port(
    port_id: int,
    db: DbSession,
    admin: AdminUser,
) -> ForceEnableResponse:
    """
    Clear force-enabled (maintenance mode) from a port.

    This re-enables the auto-disable timer if the port is still enabled.
    Admin only.
    """
    service = PortControlService(db)
    port = await service.get_port_assignment(port_id)
    if not port:
        raise HTTPException(status_code=404, detail="Port not found")

    if not port.force_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Port is not force-enabled",
        )

    port = await service.set_force_enabled(port, admin, enabled=False)

    return ForceEnableResponse(
        success=True,
        message=f"Port {port.port_number} is no longer force-enabled",
        port_id=port.id,
        force_enabled=port.force_enabled,
    )
