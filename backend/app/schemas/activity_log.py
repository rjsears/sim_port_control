# =============================================================================
# Activity Log Schemas
# =============================================================================
"""
Schemas for activity log endpoints.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ActivityLogOut(BaseModel):
    """Schema for activity log responses."""

    id: int
    timestamp: datetime
    username: str
    simulator_name: str | None
    port_number: str | None
    switch_name: str | None
    action: str
    vlan: int | None
    timeout_hours: int | None
    details: dict[str, Any] | None

    class Config:
        from_attributes = True


class ActivityLogListOut(BaseModel):
    """Schema for paginated list of activity logs."""

    logs: list[ActivityLogOut]
    total: int
    limit: int
    offset: int


class ActivityLogFilter(BaseModel):
    """Filter parameters for activity logs."""

    simulator_id: int | None = None
    user_id: int | None = None
    action: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
