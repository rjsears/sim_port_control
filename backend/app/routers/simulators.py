# =============================================================================
# Simulators Router
# =============================================================================
"""
Simulator management endpoints.
"""

import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.dependencies import AdminUser, CurrentUser, DbSession
from app.models.port_assignment import PortAssignment
from app.models.simulator import Simulator
from app.schemas.simulator import (
    PortBasic,
    SimulatorCreate,
    SimulatorListOut,
    SimulatorOut,
    SimulatorUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulators", tags=["Simulators"])


def _port_to_basic(port: PortAssignment) -> PortBasic:
    """Convert PortAssignment to PortBasic schema."""
    return PortBasic(
        id=port.id,
        port_number=port.port_number,
        switch_name=port.switch.name,
        vlan=port.vlan,
        timeout_hours=port.timeout_hours,
        status=port.status,
        enabled_at=port.enabled_at,
        auto_disable_at=port.auto_disable_at,
        seconds_remaining=port.seconds_remaining,
        force_enabled=port.force_enabled,
        force_enabled_by_username=port.force_enabled_by.username if port.force_enabled_by else None,
        force_enabled_at=port.force_enabled_at,
        force_enabled_reason=port.force_enabled_reason,
    )


def _simulator_to_out(sim: Simulator) -> SimulatorOut:
    """Convert Simulator model to SimulatorOut schema."""
    return SimulatorOut(
        id=sim.id,
        name=sim.name,
        short_name=sim.short_name,
        icon_path=sim.icon_path,
        created_at=sim.created_at,
        port_assignments=[_port_to_basic(p) for p in sim.port_assignments],
        has_active_ports=sim.has_active_ports,
        active_port_count=sim.active_port_count,
    )


@router.get("", response_model=SimulatorListOut)
async def list_simulators(db: DbSession, current_user: CurrentUser) -> SimulatorListOut:
    """
    List simulators.

    Admins see all simulators.
    SimTechs see only their assigned simulators.
    """
    query = select(Simulator).options(
        selectinload(Simulator.port_assignments).selectinload(PortAssignment.switch),
        selectinload(Simulator.port_assignments).selectinload(PortAssignment.force_enabled_by),
    )

    # Filter for non-admin users
    if not current_user.is_admin:
        assigned_ids = [sim.id for sim in current_user.assigned_simulators]
        query = query.where(Simulator.id.in_(assigned_ids))

    result = await db.execute(query.order_by(Simulator.name))
    simulators = result.scalars().all()

    return SimulatorListOut(
        simulators=[_simulator_to_out(s) for s in simulators],
        total=len(simulators),
    )


@router.get("/{simulator_id}", response_model=SimulatorOut)
async def get_simulator(
    simulator_id: int, db: DbSession, current_user: CurrentUser
) -> SimulatorOut:
    """Get a specific simulator by ID."""
    result = await db.execute(
        select(Simulator)
        .where(Simulator.id == simulator_id)
        .options(
            selectinload(Simulator.port_assignments).selectinload(PortAssignment.switch),
            selectinload(Simulator.port_assignments).selectinload(PortAssignment.force_enabled_by),
        )
    )
    simulator = result.scalar_one_or_none()
    if not simulator:
        raise HTTPException(status_code=404, detail="Simulator not found")

    # Check access for non-admin users
    if not current_user.is_admin:
        assigned_ids = [sim.id for sim in current_user.assigned_simulators]
        if simulator_id not in assigned_ids:
            raise HTTPException(status_code=403, detail="Not authorized for this simulator")

    return _simulator_to_out(simulator)


@router.post("", response_model=SimulatorOut, status_code=status.HTTP_201_CREATED)
async def create_simulator(data: SimulatorCreate, db: DbSession, admin: AdminUser) -> SimulatorOut:
    """Create a new simulator (admin only)."""
    simulator = Simulator(
        name=data.name,
        short_name=data.short_name,
        icon_path=data.icon_path,
    )
    db.add(simulator)
    await db.commit()

    # Reload with relationships to avoid lazy loading issues
    result = await db.execute(
        select(Simulator)
        .where(Simulator.id == simulator.id)
        .options(
            selectinload(Simulator.port_assignments).selectinload(PortAssignment.switch),
            selectinload(Simulator.port_assignments).selectinload(PortAssignment.force_enabled_by),
        )
    )
    simulator = result.scalar_one()

    logger.info(f"Created simulator '{simulator.name}'")
    return _simulator_to_out(simulator)


@router.put("/{simulator_id}", response_model=SimulatorOut)
async def update_simulator(
    simulator_id: int, data: SimulatorUpdate, db: DbSession, admin: AdminUser
) -> SimulatorOut:
    """Update an existing simulator (admin only)."""
    result = await db.execute(
        select(Simulator)
        .where(Simulator.id == simulator_id)
        .options(
            selectinload(Simulator.port_assignments).selectinload(PortAssignment.switch),
            selectinload(Simulator.port_assignments).selectinload(PortAssignment.force_enabled_by),
        )
    )
    simulator = result.scalar_one_or_none()
    if not simulator:
        raise HTTPException(status_code=404, detail="Simulator not found")

    # Update fields
    if data.name is not None:
        simulator.name = data.name
    if data.short_name is not None:
        simulator.short_name = data.short_name
    if data.icon_path is not None:
        simulator.icon_path = data.icon_path

    await db.commit()

    # Reload with relationships to avoid lazy loading issues
    result = await db.execute(
        select(Simulator)
        .where(Simulator.id == simulator_id)
        .options(
            selectinload(Simulator.port_assignments).selectinload(PortAssignment.switch),
            selectinload(Simulator.port_assignments).selectinload(PortAssignment.force_enabled_by),
        )
    )
    simulator = result.scalar_one()

    logger.info(f"Updated simulator '{simulator.name}'")
    return _simulator_to_out(simulator)


@router.delete("/{simulator_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_simulator(simulator_id: int, db: DbSession, admin: AdminUser) -> None:
    """Delete a simulator (admin only)."""
    result = await db.execute(select(Simulator).where(Simulator.id == simulator_id))
    simulator = result.scalar_one_or_none()
    if not simulator:
        raise HTTPException(status_code=404, detail="Simulator not found")

    await db.delete(simulator)
    await db.commit()
    logger.info(f"Deleted simulator '{simulator.name}'")
