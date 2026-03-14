# =============================================================================
# Port Schemas
# =============================================================================
"""
Schemas for port assignment and control endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class PortAssignmentBase(BaseModel):
    """Base port assignment schema."""

    simulator_id: int
    switch_id: int
    port_number: str = Field(..., min_length=1, max_length=20)
    vlan: int = Field(default=30, ge=1, le=4094)
    timeout_hours: int = Field(default=4, ge=1, le=168)  # Max 1 week


class PortAssignmentCreate(PortAssignmentBase):
    """Schema for creating a new port assignment."""

    pass


class PortAssignmentUpdate(BaseModel):
    """Schema for updating an existing port assignment."""

    vlan: int | None = Field(None, ge=1, le=4094)
    timeout_hours: int | None = Field(None, ge=1, le=168)


class PortAssignmentOut(BaseModel):
    """Schema for port assignment responses."""

    id: int
    simulator_id: int
    simulator_name: str
    switch_id: int
    switch_name: str
    port_number: str
    vlan: int
    timeout_hours: int
    status: str
    enabled_at: datetime | None
    auto_disable_at: datetime | None
    enabled_by_username: str | None
    seconds_remaining: int | None
    created_at: datetime
    # Force-enabled fields
    force_enabled: bool = False
    force_enabled_by_username: str | None = None
    force_enabled_at: datetime | None = None
    force_enabled_reason: str | None = None

    class Config:
        from_attributes = True


class PortEnableRequest(BaseModel):
    """Request to enable a port."""

    timeout_hours: float | None = Field(None, ge=0.01, le=168)  # Min ~36 seconds for testing
    vlan: int | None = Field(None, ge=1, le=4094)


class PortStatusOut(BaseModel):
    """Detailed port status response."""

    id: int
    simulator_name: str
    switch_name: str
    port_number: str
    vlan: int
    status: str
    enabled_at: datetime | None
    auto_disable_at: datetime | None
    enabled_by: str | None
    seconds_remaining: int | None


class PortActionResult(BaseModel):
    """Result of a port enable/disable action."""

    success: bool
    message: str
    port_id: int
    status: str
    auto_disable_at: datetime | None = None


class PortAssignmentListOut(BaseModel):
    """Schema for list of port assignments."""

    port_assignments: list[PortAssignmentOut]
    total: int


class ForceEnableRequest(BaseModel):
    """Request to force-enable a port (maintenance mode)."""

    reason: str = Field(..., min_length=1, max_length=255)


class ForceEnableResponse(BaseModel):
    """Response from force-enable operation."""

    success: bool
    message: str
    port_id: int
    force_enabled: bool
    force_enabled_reason: str | None = None
