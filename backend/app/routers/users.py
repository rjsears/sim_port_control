# =============================================================================
# Users Router
# =============================================================================
"""
User management endpoints (admin only).
"""

import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.dependencies import AdminUser, DbSession
from app.models.user import User, UserSimulatorAssignment
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services.auth import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=list[UserOut])
async def list_users(db: DbSession, admin: AdminUser) -> list[UserOut]:
    """List all users (admin only)."""
    result = await db.execute(
        select(User).options(
            selectinload(User.simulator_assignments).selectinload(UserSimulatorAssignment.simulator)
        )
    )
    users = result.scalars().all()
    return [UserOut.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: int, db: DbSession, admin: AdminUser) -> UserOut:
    """Get a specific user by ID (admin only)."""
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.simulator_assignments).selectinload(UserSimulatorAssignment.simulator)
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(user)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, db: DbSession, admin: AdminUser) -> UserOut:
    """Create a new user (admin only)."""
    # Check if username exists
    existing = await AuthService.get_user_by_username(db, data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # Create user
    user = User(
        username=data.username,
        password_hash=AuthService.get_password_hash(data.password),
        role=data.role,
    )
    db.add(user)
    await db.flush()  # Get the user ID

    # Add simulator assignments
    for sim_id in data.assigned_simulator_ids:
        assignment = UserSimulatorAssignment(user_id=user.id, simulator_id=sim_id)
        db.add(assignment)

    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(User)
        .where(User.id == user.id)
        .options(
            selectinload(User.simulator_assignments).selectinload(UserSimulatorAssignment.simulator)
        )
    )
    user = result.scalar_one()

    logger.info(f"Created user '{user.username}' with role '{user.role}'")
    return UserOut.model_validate(user)


@router.put("/{user_id}", response_model=UserOut)
async def update_user(user_id: int, data: UserUpdate, db: DbSession, admin: AdminUser) -> UserOut:
    """Update an existing user (admin only)."""
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.simulator_assignments))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update fields
    if data.username is not None:
        # Check if new username is taken
        existing = await AuthService.get_user_by_username(db, data.username)
        if existing and existing.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )
        user.username = data.username

    if data.password is not None:
        user.password_hash = AuthService.get_password_hash(data.password)

    if data.role is not None:
        user.role = data.role

    # Update simulator assignments if provided
    if data.assigned_simulator_ids is not None:
        # Remove existing assignments
        await db.execute(
            delete(UserSimulatorAssignment).where(UserSimulatorAssignment.user_id == user_id)
        )
        # Add new assignments
        for sim_id in data.assigned_simulator_ids:
            assignment = UserSimulatorAssignment(user_id=user.id, simulator_id=sim_id)
            db.add(assignment)

    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(User)
        .where(User.id == user.id)
        .options(
            selectinload(User.simulator_assignments).selectinload(UserSimulatorAssignment.simulator)
        )
    )
    user = result.scalar_one()

    logger.info(f"Updated user '{user.username}'")
    return UserOut.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: DbSession, admin: AdminUser) -> None:
    """Delete a user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent deleting yourself
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    await db.delete(user)
    await db.commit()
    logger.info(f"Deleted user '{user.username}'")
