# =============================================================================
# Authentication Schemas
# =============================================================================
"""
Schemas for authentication endpoints.
"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request payload."""

    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserBasic"


class TokenData(BaseModel):
    """Decoded JWT token data."""

    username: str | None = None
    user_id: int | None = None
    role: str | None = None


class UserBasic(BaseModel):
    """Basic user info for token response."""

    id: int
    username: str
    role: str

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    """Change password request payload."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=100)


class ChangePasswordResponse(BaseModel):
    """Change password response."""

    success: bool
    message: str


# Update forward reference
Token.model_rebuild()
