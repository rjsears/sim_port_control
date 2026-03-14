# =============================================================================
# Authentication Service
# =============================================================================
"""
Authentication service for JWT token management and password hashing.
"""

import logging
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.user import User, UserSimulatorAssignment
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)
settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication operations."""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate bcrypt hash for a password."""
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
        """
        Create a JWT access token.

        Args:
            data: Payload data to encode in the token.
            expires_delta: Optional custom expiration time.

        Returns:
            Encoded JWT token string.
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> TokenData | None:
        """
        Decode and validate a JWT token.

        Args:
            token: JWT token string.

        Returns:
            TokenData if valid, None otherwise.
        """
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            username: str | None = payload.get("sub")
            user_id: int | None = payload.get("user_id")
            role: str | None = payload.get("role")
            if username is None:
                return None
            return TokenData(username=username, user_id=user_id, role=role)
        except JWTError:
            return None

    @staticmethod
    async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
        """
        Authenticate a user by username and password.

        Args:
            db: Database session.
            username: Username to authenticate.
            password: Password to verify.

        Returns:
            User object if authentication succeeds, None otherwise.
        """
        result = await db.execute(
            select(User)
            .where(User.username == username)
            .options(selectinload(User.simulator_assignments))
        )
        user = result.scalar_one_or_none()
        if not user:
            logger.warning(f"Authentication failed: user '{username}' not found")
            return None
        if not AuthService.verify_password(password, user.password_hash):
            logger.warning(f"Authentication failed: invalid password for user '{username}'")
            return None
        logger.info(f"User '{username}' authenticated successfully")
        return user

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
        """Get a user by ID."""
        result = await db.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.simulator_assignments).selectinload(
                    UserSimulatorAssignment.simulator
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
        """Get a user by username."""
        result = await db.execute(
            select(User)
            .where(User.username == username)
            .options(
                selectinload(User.simulator_assignments).selectinload(
                    UserSimulatorAssignment.simulator
                )
            )
        )
        return result.scalar_one_or_none()
