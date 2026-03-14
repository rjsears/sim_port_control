# =============================================================================
# Simulator Schemas
# =============================================================================
"""
Schemas for simulator management endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class SimulatorBase(BaseModel):
    """Base simulator schema."""

    name: str = Field(..., min_length=1, max_length=100)
    short_name: str = Field(..., min_length=1, max_length=20)
    icon_path: str | None = None


class SimulatorCreate(SimulatorBase):
    """Schema for creating a new simulator."""

    pass


class SimulatorUpdate(BaseModel):
    """Schema for updating an existing simulator."""

    name: str | None = Field(None, min_length=1, max_length=100)
    short_name: str | None = Field(None, min_length=1, max_length=20)
    icon_path: str | None = None


class PortBasic(BaseModel):
    """Basic port info for simulator response."""

    id: int
    port_number: str
    switch_name: str
    vlan: int
    timeout_hours: int
    status: str
    enabled_at: datetime | None
    auto_disable_at: datetime | None
    seconds_remaining: int | None
    # Force-enabled fields
    force_enabled: bool = False
    force_enabled_by_username: str | None = None
    force_enabled_at: datetime | None = None
    force_enabled_reason: str | None = None

    class Config:
        from_attributes = True


class SimulatorOut(BaseModel):
    """Schema for simulator responses."""

    id: int
    name: str
    short_name: str
    icon_path: str | None
    created_at: datetime
    port_assignments: list[PortBasic] = Field(default_factory=list)
    has_active_ports: bool = False
    active_port_count: int = 0

    class Config:
        from_attributes = True


class SimulatorListOut(BaseModel):
    """Schema for list of simulators."""

    simulators: list[SimulatorOut]
    total: int
