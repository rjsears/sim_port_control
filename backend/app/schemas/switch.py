# =============================================================================
# Switch Schemas
# =============================================================================
"""
Schemas for switch management endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class SwitchBase(BaseModel):
    """Base switch schema."""

    name: str = Field(..., min_length=1, max_length=100)
    ip_address: str = Field(..., min_length=7, max_length=45)
    username: str = Field(..., min_length=1, max_length=50)
    device_type: str = Field(default="cisco_ios", max_length=50)


class SwitchCreate(SwitchBase):
    """Schema for creating a new switch."""

    password: str = Field(..., min_length=1)


class SwitchUpdate(BaseModel):
    """Schema for updating an existing switch."""

    name: str | None = Field(None, min_length=1, max_length=100)
    ip_address: str | None = Field(None, min_length=7, max_length=45)
    username: str | None = Field(None, min_length=1, max_length=50)
    password: str | None = None
    device_type: str | None = Field(None, max_length=50)


class SwitchOut(BaseModel):
    """Schema for switch responses (excludes password)."""

    id: int
    name: str
    ip_address: str
    username: str
    device_type: str
    port_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SwitchTestResult(BaseModel):
    """Result of testing switch connectivity."""

    success: bool
    message: str
    switch_info: dict | None = None


class SwitchListOut(BaseModel):
    """Schema for list of switches."""

    switches: list[SwitchOut]
    total: int
