# =============================================================================
# User Schemas
# =============================================================================
"""
Schemas for user management endpoints.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Base user schema with common fields."""

    username: str = Field(..., min_length=3, max_length=50)
    role: Literal["admin", "simtech"] = "simtech"


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=8, max_length=100)
    assigned_simulator_ids: list[int] = Field(default_factory=list)


class UserUpdate(BaseModel):
    """Schema for updating an existing user."""

    username: str | None = Field(None, min_length=3, max_length=50)
    password: str | None = Field(None, min_length=8, max_length=100)
    role: Literal["admin", "simtech"] | None = None
    assigned_simulator_ids: list[int] | None = None


class SimulatorBasic(BaseModel):
    """Basic simulator info for user response."""

    id: int
    name: str
    short_name: str

    class Config:
        from_attributes = True


class UserOut(BaseModel):
    """Schema for user responses."""

    id: int
    username: str
    role: str
    created_at: datetime
    updated_at: datetime
    assigned_simulators: list[SimulatorBasic] = Field(default_factory=list)

    class Config:
        from_attributes = True
