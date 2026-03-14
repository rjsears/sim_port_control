# =============================================================================
# Pydantic Schemas
# =============================================================================
"""
Request/Response schemas for API validation.
"""

from app.schemas.activity_log import ActivityLogListOut, ActivityLogOut
from app.schemas.auth import LoginRequest, Token, TokenData
from app.schemas.port import (
    PortAssignmentCreate,
    PortAssignmentOut,
    PortAssignmentUpdate,
    PortEnableRequest,
    PortStatusOut,
)
from app.schemas.simulator import SimulatorCreate, SimulatorOut, SimulatorUpdate
from app.schemas.switch import SwitchCreate, SwitchOut, SwitchTestResult, SwitchUpdate
from app.schemas.user import UserCreate, UserOut, UserUpdate

__all__ = [
    "ActivityLogListOut",
    "ActivityLogOut",
    "LoginRequest",
    "PortAssignmentCreate",
    "PortAssignmentOut",
    "PortAssignmentUpdate",
    "PortEnableRequest",
    "PortStatusOut",
    "SimulatorCreate",
    "SimulatorOut",
    "SimulatorUpdate",
    "SwitchCreate",
    "SwitchOut",
    "SwitchTestResult",
    "SwitchUpdate",
    "Token",
    "TokenData",
    "UserCreate",
    "UserOut",
    "UserUpdate",
]
