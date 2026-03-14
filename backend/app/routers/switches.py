# =============================================================================
# Switches Router
# =============================================================================
"""
Switch management endpoints (admin only).
"""

import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.dependencies import AdminUser, DbSession
from app.models.switch import Switch
from app.schemas.switch import (
    SwitchCreate,
    SwitchListOut,
    SwitchOut,
    SwitchTestResult,
    SwitchUpdate,
)
from app.services.cisco_ssh import CiscoSSHError, CiscoSSHService
from app.services.encryption import get_encryption_service
from app.services.port_discovery import PortDiscoveryService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/switches", tags=["Switches"])


@router.get("", response_model=SwitchListOut)
async def list_switches(db: DbSession, admin: AdminUser) -> SwitchListOut:
    """List all switches (admin only)."""
    result = await db.execute(select(Switch).options(selectinload(Switch.port_assignments)))
    switches = result.scalars().all()

    return SwitchListOut(
        switches=[SwitchOut.model_validate(s) for s in switches],
        total=len(switches),
    )


@router.get("/{switch_id}", response_model=SwitchOut)
async def get_switch(switch_id: int, db: DbSession, admin: AdminUser) -> SwitchOut:
    """Get a specific switch by ID (admin only)."""
    result = await db.execute(
        select(Switch).where(Switch.id == switch_id).options(selectinload(Switch.port_assignments))
    )
    switch = result.scalar_one_or_none()
    if not switch:
        raise HTTPException(status_code=404, detail="Switch not found")
    return SwitchOut.model_validate(switch)


@router.post("", response_model=SwitchOut, status_code=status.HTTP_201_CREATED)
async def create_switch(data: SwitchCreate, db: DbSession, admin: AdminUser) -> SwitchOut:
    """Create a new switch (admin only)."""
    encryption = get_encryption_service()

    switch = Switch(
        name=data.name,
        ip_address=data.ip_address,
        username=data.username,
        password_encrypted=encryption.encrypt(data.password),
        device_type=data.device_type,
    )
    db.add(switch)
    await db.commit()

    logger.info(f"Created switch '{switch.name}' ({switch.ip_address})")

    # Auto-scan for available ports
    try:
        discovery_service = PortDiscoveryService(db)
        scan_result = await discovery_service.scan_switch(switch.id)
        logger.info(f"Auto-scan result: {scan_result['message']}")
    except Exception as e:
        logger.warning(f"Auto-scan failed for new switch: {e}")

    # Reload with relationships for serialization
    result = await db.execute(
        select(Switch).where(Switch.id == switch.id).options(selectinload(Switch.port_assignments))
    )
    switch = result.scalar_one()

    return SwitchOut.model_validate(switch)


@router.put("/{switch_id}", response_model=SwitchOut)
async def update_switch(
    switch_id: int, data: SwitchUpdate, db: DbSession, admin: AdminUser
) -> SwitchOut:
    """Update an existing switch (admin only)."""
    result = await db.execute(
        select(Switch).where(Switch.id == switch_id).options(selectinload(Switch.port_assignments))
    )
    switch = result.scalar_one_or_none()
    if not switch:
        raise HTTPException(status_code=404, detail="Switch not found")

    encryption = get_encryption_service()

    # Update fields
    if data.name is not None:
        switch.name = data.name
    if data.ip_address is not None:
        switch.ip_address = data.ip_address
    if data.username is not None:
        switch.username = data.username
    if data.password is not None:
        switch.password_encrypted = encryption.encrypt(data.password)
    if data.device_type is not None:
        switch.device_type = data.device_type

    await db.commit()

    # Reload with relationships for serialization
    result = await db.execute(
        select(Switch).where(Switch.id == switch_id).options(selectinload(Switch.port_assignments))
    )
    switch = result.scalar_one()

    logger.info(f"Updated switch '{switch.name}'")
    return SwitchOut.model_validate(switch)


@router.delete("/{switch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_switch(switch_id: int, db: DbSession, admin: AdminUser) -> None:
    """Delete a switch (admin only)."""
    result = await db.execute(select(Switch).where(Switch.id == switch_id))
    switch = result.scalar_one_or_none()
    if not switch:
        raise HTTPException(status_code=404, detail="Switch not found")

    await db.delete(switch)
    await db.commit()
    logger.info(f"Deleted switch '{switch.name}'")


@router.post("/{switch_id}/test", response_model=SwitchTestResult)
async def test_switch_connection(
    switch_id: int, db: DbSession, admin: AdminUser
) -> SwitchTestResult:
    """Test SSH connectivity to a switch (admin only)."""
    result = await db.execute(select(Switch).where(Switch.id == switch_id))
    switch = result.scalar_one_or_none()
    if not switch:
        raise HTTPException(status_code=404, detail="Switch not found")

    try:
        ssh_service = CiscoSSHService(switch)
        info = await ssh_service.test_connection_async()
        return SwitchTestResult(
            success=True,
            message=f"Successfully connected to {switch.name}",
            switch_info=info,
        )
    except CiscoSSHError as e:
        return SwitchTestResult(
            success=False,
            message=str(e),
            switch_info=None,
        )
