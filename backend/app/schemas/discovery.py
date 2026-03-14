# backend/app/schemas/discovery.py
"""Schemas for port discovery endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class DiscoveredPortOut(BaseModel):
    """Schema for discovered port response."""

    id: int
    switch_id: int
    switch_name: str
    port_name: str
    short_name: str
    status: str
    description: str | None
    discovered_at: datetime
    last_verified_at: datetime | None
    error_message: str | None
    assigned_simulator_name: str | None = None

    class Config:
        from_attributes = True


class DiscoveredPortListOut(BaseModel):
    """Schema for list of discovered ports."""

    ports: list[DiscoveredPortOut]
    total: int
    available_count: int
    assigned_count: int
    error_count: int


class ScanResult(BaseModel):
    """Result of a port scan operation."""

    success: bool
    message: str
    ports_found: int
    new_ports: int
    removed_ports: int


class PortAssignRequest(BaseModel):
    """Request to assign a discovered port to a simulator."""

    discovered_port_id: int
    simulator_id: int
    vlan: int = Field(default=30, ge=1, le=4094)
    timeout_hours: int = Field(default=4, ge=1, le=24)


class PortAssignResult(BaseModel):
    """Result of a port assignment."""

    success: bool
    message: str
    port_id: int | None = None
    error: str | None = None


class PortReleaseResult(BaseModel):
    """Result of releasing a port."""

    success: bool
    message: str
    error: str | None = None
