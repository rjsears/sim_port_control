"""
Port discovery API endpoints.
"""

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.dependencies import AdminUser, DbSession
from app.models.discovered_port import DiscoveredPort
from app.schemas.discovery import (
    DiscoveredPortListOut,
    DiscoveredPortOut,
    PortAssignRequest,
    PortAssignResult,
    PortReleaseResult,
    ScanResult,
)
from app.services.port_discovery import PortDiscoveryService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/discovery", tags=["Discovery"])


def _port_to_out(port: DiscoveredPort) -> DiscoveredPortOut:
    """Convert DiscoveredPort model to schema."""
    assigned_sim = None
    if port.port_assignment and port.port_assignment.simulator:
        assigned_sim = port.port_assignment.simulator.name

    return DiscoveredPortOut(
        id=port.id,
        switch_id=port.switch_id,
        switch_name=port.switch.name,
        port_name=port.port_name,
        short_name=port.short_name,
        status=port.status,
        description=port.description,
        discovered_at=port.discovered_at,
        last_verified_at=port.last_verified_at,
        error_message=port.error_message,
        assigned_simulator_name=assigned_sim,
    )


@router.post("/switches/{switch_id}/scan", response_model=ScanResult)
async def scan_switch(switch_id: int, db: DbSession, admin: AdminUser) -> ScanResult:
    """Scan a switch for available ports (admin only)."""
    service = PortDiscoveryService(db)
    result = await service.scan_switch(switch_id)

    return ScanResult(
        success=result["success"],
        message=result["message"],
        ports_found=result["ports_found"],
        new_ports=result["new_ports"],
        removed_ports=result["removed_ports"],
    )


@router.get("/switches/{switch_id}/ports", response_model=DiscoveredPortListOut)
async def list_switch_ports(
    switch_id: int, db: DbSession, admin: AdminUser
) -> DiscoveredPortListOut:
    """List discovered ports for a switch (admin only)."""
    service = PortDiscoveryService(db)
    ports = await service.get_discovered_ports(switch_id=switch_id)

    available = sum(1 for p in ports if p.status == "available")
    assigned = sum(1 for p in ports if p.status == "assigned")
    errors = sum(1 for p in ports if p.status == "error")

    return DiscoveredPortListOut(
        ports=[_port_to_out(p) for p in ports],
        total=len(ports),
        available_count=available,
        assigned_count=assigned,
        error_count=errors,
    )


@router.get("/ports", response_model=DiscoveredPortListOut)
async def list_all_discovered_ports(
    db: DbSession, admin: AdminUser, status: str | None = None
) -> DiscoveredPortListOut:
    """List all discovered ports (admin only)."""
    service = PortDiscoveryService(db)
    ports = await service.get_discovered_ports(status=status)

    available = sum(1 for p in ports if p.status == "available")
    assigned = sum(1 for p in ports if p.status == "assigned")
    errors = sum(1 for p in ports if p.status == "error")

    return DiscoveredPortListOut(
        ports=[_port_to_out(p) for p in ports],
        total=len(ports),
        available_count=available,
        assigned_count=assigned,
        error_count=errors,
    )


@router.post("/ports/assign", response_model=PortAssignResult)
async def assign_port(
    request: PortAssignRequest, db: DbSession, admin: AdminUser
) -> PortAssignResult:
    """Assign a discovered port to a simulator (admin only)."""
    service = PortDiscoveryService(db)
    result = await service.assign_port(
        discovered_port_id=request.discovered_port_id,
        simulator_id=request.simulator_id,
        vlan=request.vlan,
        timeout_hours=request.timeout_hours,
        user_id=admin.id,
    )

    return PortAssignResult(
        success=result["success"],
        message=result["message"],
        port_id=result.get("port_id"),
        error=result.get("error"),
    )


@router.delete("/ports/assignments/{assignment_id}", response_model=PortReleaseResult)
async def release_port(assignment_id: int, db: DbSession, admin: AdminUser) -> PortReleaseResult:
    """Release a port back to available (admin only)."""
    service = PortDiscoveryService(db)
    result = await service.release_port(assignment_id, admin.id)

    return PortReleaseResult(
        success=result["success"],
        message=result["message"],
        error=result.get("error"),
    )


@router.post("/ports/{port_id}/refresh", response_model=DiscoveredPortOut)
async def refresh_port_status(port_id: int, db: DbSession, admin: AdminUser) -> DiscoveredPortOut:
    """Refresh status of a single discovered port (admin only)."""
    result = await db.execute(
        select(DiscoveredPort)
        .where(DiscoveredPort.id == port_id)
        .options(
            selectinload(DiscoveredPort.switch),
            selectinload(DiscoveredPort.port_assignment),
        )
    )
    port = result.scalar_one_or_none()

    if not port:
        raise HTTPException(status_code=404, detail="Port not found")

    # TODO: Implement single port refresh with verification
    # For now, just return current state

    return _port_to_out(port)
