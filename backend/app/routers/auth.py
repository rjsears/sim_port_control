# =============================================================================
# Authentication Router
# =============================================================================
"""
Authentication endpoints for login/logout.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.config import get_settings
from app.dependencies import CurrentUser, DbSession
from app.schemas.auth import ChangePasswordRequest, ChangePasswordResponse, Token, UserBasic
from app.services.auth import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post("/login", response_model=Token)
async def login(
    db: DbSession,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    """
    Authenticate user and return JWT token.

    Accepts OAuth2 password form (username + password).
    """
    user = await AuthService.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = AuthService.create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "role": user.role,
        }
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserBasic(
            id=user.id,
            username=user.username,
            role=user.role,
        ),
    )


@router.post("/logout")
async def logout(current_user: CurrentUser) -> dict:
    """
    Logout current user.

    Note: With JWT, logout is handled client-side by discarding the token.
    This endpoint is provided for API completeness.
    """
    logger.info(f"User '{current_user.username}' logged out")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserBasic)
async def get_current_user_info(current_user: CurrentUser) -> UserBasic:
    """Get current authenticated user info."""
    return UserBasic(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
    )


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    db: DbSession,
    current_user: CurrentUser,
    request: ChangePasswordRequest,
) -> ChangePasswordResponse:
    """
    Change the current user's password.

    Requires the current password for verification.
    """
    # Verify current password
    if not AuthService.verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    current_user.password_hash = AuthService.get_password_hash(request.new_password)
    await db.commit()

    logger.info(f"User '{current_user.username}' changed their password")

    return ChangePasswordResponse(
        success=True,
        message="Password changed successfully",
    )
