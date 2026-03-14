"""
Tests for authentication endpoints and services.
"""

import pytest

from app.services.auth import AuthService


class TestPasswordHashing:
    """Tests for password hashing functionality."""

    def test_password_hash_generates_different_hashes(self):
        """Same password should generate different hashes (due to salt)."""
        password = "testpassword123"
        hash1 = AuthService.get_password_hash(password)
        hash2 = AuthService.get_password_hash(password)
        assert hash1 != hash2

    def test_password_verification_correct(self):
        """Correct password should verify successfully."""
        password = "testpassword123"
        hashed = AuthService.get_password_hash(password)
        assert AuthService.verify_password(password, hashed) is True

    def test_password_verification_incorrect(self):
        """Incorrect password should fail verification."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = AuthService.get_password_hash(password)
        assert AuthService.verify_password(wrong_password, hashed) is False


class TestJWTTokens:
    """Tests for JWT token creation and validation."""

    def test_create_access_token(self):
        """Access token should be created successfully."""
        data = {"sub": "testuser", "user_id": 1, "role": "admin"}
        token = AuthService.create_access_token(data)
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_token(self):
        """Valid token should decode successfully."""
        data = {"sub": "testuser", "user_id": 1, "role": "admin"}
        token = AuthService.create_access_token(data)
        decoded = AuthService.decode_token(token)
        assert decoded is not None
        assert decoded.username == "testuser"
        assert decoded.user_id == 1
        assert decoded.role == "admin"

    def test_decode_invalid_token(self):
        """Invalid token should return None."""
        invalid_token = "invalid.token.here"
        decoded = AuthService.decode_token(invalid_token)
        assert decoded is None

    def test_decode_malformed_token(self):
        """Malformed token should return None."""
        malformed_token = "not-a-jwt-at-all"
        decoded = AuthService.decode_token(malformed_token)
        assert decoded is None


@pytest.fixture
async def test_user(db_session):
    """Create a test user for authentication."""
    from app.models.user import User

    user = User(
        username="authuser",
        password_hash=AuthService.get_password_hash("correctpassword"),
        role="simtech",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session):
    """Create an admin user for testing."""
    from app.models.user import User

    user = User(
        username="authadmin",
        password_hash=AuthService.get_password_hash("adminpass123"),
        role="admin",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
class TestAuthEndpoints:
    """Tests for authentication API endpoints."""

    async def test_login_without_credentials(self, client):
        """Login without credentials should fail."""
        response = await client.post("/api/auth/login")
        assert response.status_code == 422  # Validation error

    async def test_login_with_invalid_credentials(self, client):
        """Login with invalid credentials should fail."""
        response = await client.post(
            "/api/auth/login",
            data={"username": "nonexistent", "password": "wrong"},
        )
        assert response.status_code == 401

    async def test_protected_endpoint_without_token(self, client):
        """Protected endpoints should require authentication."""
        response = await client.get("/api/auth/me")
        assert response.status_code == 401

    async def test_protected_endpoint_with_invalid_token(self, client):
        """Protected endpoints should reject invalid tokens."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    async def test_login_success(self, client, test_user):
        """Should login with correct credentials."""
        response = await client.post(
            "/api/auth/login",
            data={
                "username": "authuser",
                "password": "correctpassword",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client, test_user):
        """Should reject incorrect password."""
        response = await client.post(
            "/api/auth/login",
            data={
                "username": "authuser",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    async def test_login_returns_user_info(self, client, test_user):
        """Login response should include user information."""
        response = await client.post(
            "/api/auth/login",
            data={
                "username": "authuser",
                "password": "correctpassword",
            },
        )
        data = response.json()
        assert "user" in data
        assert data["user"]["username"] == "authuser"
        assert data["user"]["role"] == "simtech"

    async def test_get_me_authenticated(self, client, test_user):
        """Should return current user info when authenticated."""
        # First login
        login_response = await client.post(
            "/api/auth/login",
            data={
                "username": "authuser",
                "password": "correctpassword",
            },
        )
        token = login_response.json()["access_token"]

        # Get current user
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "authuser"
        assert data["role"] == "simtech"
        assert "password" not in data


@pytest.mark.asyncio
class TestAuthServiceDatabase:
    """Tests for AuthService database operations."""

    async def test_get_user_by_username(self, db_session, test_user):
        """Should find user by username."""
        user = await AuthService.get_user_by_username(db_session, "authuser")
        assert user is not None
        assert user.username == "authuser"

    async def test_get_user_by_username_not_found(self, db_session):
        """Should return None for non-existent user."""
        user = await AuthService.get_user_by_username(db_session, "nonexistent")
        assert user is None

    async def test_authenticate_user_success(self, db_session, test_user):
        """Should authenticate user with correct credentials."""
        user = await AuthService.authenticate_user(db_session, "authuser", "correctpassword")
        assert user is not None
        assert user.username == "authuser"

    async def test_authenticate_user_wrong_password(self, db_session, test_user):
        """Should return None for wrong password."""
        user = await AuthService.authenticate_user(db_session, "authuser", "wrongpassword")
        assert user is None

    async def test_authenticate_user_not_found(self, db_session):
        """Should return None for non-existent user."""
        user = await AuthService.authenticate_user(db_session, "nonexistent", "anypassword")
        assert user is None
