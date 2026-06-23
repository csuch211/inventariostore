"""Tests for JWT authentication."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta

from services.auth import AuthService
from config.settings import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
)


@pytest.fixture
def auth_service(ctrl):
    """Create an AuthService with DB access."""
    return AuthService(db=ctrl.db)


class TestPasswordHashing:
    def test_hash_password_returns_salt_hash_format(self):
        hashed = AuthService.hash_password("TestPass123")
        assert ":" in hashed
        assert len(hashed.split(":")) == 2

    def test_verify_password_new_format(self):
        hashed = AuthService.hash_password("TestPass123")
        assert AuthService.verify_password(hashed, "TestPass123") is True
        assert AuthService.verify_password(hashed, "WrongPass") is False

    def test_verify_empty_password(self):
        assert AuthService.verify_password("", "password") is False
        assert AuthService.verify_password("hash", "") is False

    def test_legacy_password_verification(self):
        # Test legacy format (no colon = legacy salt)
        from services.auth import _hash_with_salt, _LEGACY_SALT

        legacy_hash = _hash_with_salt("Admin123", _LEGACY_SALT)
        assert AuthService.verify_password(legacy_hash, "Admin123") is True


class TestJWTAccessTokens:
    def test_create_access_token_returns_string(self, auth_service):
        token = auth_service.create_access_token(
            username="admin",
            rol="admin",
            permissions=["productos.leer", "dashboard.ver"],
        )
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_access_token_valid(self, auth_service):
        token = auth_service.create_access_token(
            username="admin",
            rol="admin",
            permissions=["productos.leer"],
        )
        payload = auth_service.verify_access_token(token)
        assert payload is not None
        assert payload["sub"] == "admin"
        assert payload["rol"] == "admin"
        assert "productos.leer" in payload["permissions"]
        assert payload["type"] == "access"

    def test_verify_access_token_expired(self, auth_service):
        # Create a token with expired time
        import jwt

        now = datetime.utcnow()
        payload = {
            "sub": "admin",
            "rol": "admin",
            "permissions": [],
            "iat": now - timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES + 1),
            "exp": now - timedelta(minutes=1),
            "type": "access",
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        result = auth_service.verify_access_token(token)
        assert result is None

    def test_verify_access_token_wrong_type(self, auth_service):
        # Create a refresh token and try to verify as access
        import jwt

        now = datetime.utcnow()
        payload = {
            "sub": "admin",
            "jti": "test123",
            "iat": now,
            "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            "type": "refresh",
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        result = auth_service.verify_access_token(token)
        assert result is None

    def test_verify_access_token_invalid_signature(self, auth_service):
        import jwt

        now = datetime.utcnow()
        payload = {
            "sub": "admin",
            "rol": "admin",
            "permissions": [],
            "iat": now,
            "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            "type": "access",
        }
        # Sign with wrong key
        token = jwt.encode(payload, "wrong-secret", algorithm=JWT_ALGORITHM)
        result = auth_service.verify_access_token(token)
        assert result is None


class TestJWTRefreshTokens:
    def test_create_refresh_token_returns_string(self, auth_service):
        token = auth_service.create_refresh_token(username="admin", user_id=1)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_refresh_token_valid(self, auth_service):
        token = auth_service.create_refresh_token(username="admin", user_id=1)
        payload = auth_service.verify_refresh_token(token)
        assert payload is not None
        assert payload["sub"] == "admin"
        assert payload["type"] == "refresh"
        assert "jti" in payload

    def test_revoke_refresh_token(self, auth_service):
        token = auth_service.create_refresh_token(username="admin", user_id=1)
        payload = auth_service.verify_refresh_token(token)
        assert payload is not None

        # Revoke
        success = auth_service.revoke_refresh_token(payload["jti"])
        assert success is True

        # Verify revoked
        result = auth_service.verify_refresh_token(token)
        assert result is None

    def test_verify_refresh_token_expired(self, auth_service):
        import jwt

        now = datetime.utcnow()
        payload = {
            "sub": "admin",
            "jti": "expired-token",
            "iat": now - timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS + 1),
            "exp": now - timedelta(days=1),
            "type": "refresh",
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        result = auth_service.verify_refresh_token(token)
        assert result is None


class TestAuthIntegration:
    @pytest.mark.asyncio
    async def test_authenticate_returns_tokens(self, ctrl):
        """Test full authentication flow returns JWT tokens."""
        result = await ctrl.login("admin", "Admin123")
        assert result.get("success") or "token" in str(result)

    @pytest.mark.asyncio
    async def test_login_sets_permissions(self, ctrl):
        """Verify login sets permissions correctly."""
        await ctrl.login("admin", "Admin123")
        assert ctrl.current_user == "admin"
        assert len(ctrl.current_user_permissions) > 0


class TestUserRegistration:
    def test_register_valid_user(self, ctrl):
        """Test registering a new valid user."""
        from api.rest import register, RegisterRequest
        import asyncio

        req = RegisterRequest(
            username="newuser123",
            password="SecurePass1",
            nombre="Test User",
        )
        result = asyncio.run(register(req))
        assert result["username"] == "newuser123"
        assert result["id"] is not None

    def test_register_duplicate_username(self, ctrl):
        """Test registering with existing username fails."""
        from api.rest import register, RegisterRequest
        from fastapi import HTTPException
        import asyncio

        # First registration
        req = RegisterRequest(
            username="duplicate_user",
            password="SecurePass1",
            nombre="First User",
        )
        asyncio.run(register(req))

        # Second registration should fail
        req2 = RegisterRequest(
            username="duplicate_user",
            password="SecurePass2",
            nombre="Second User",
        )
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(register(req2))
        assert exc_info.value.status_code == 409

    def test_register_weak_password(self, ctrl):
        """Test registration with weak password fails (Pydantic validation)."""
        from pydantic import ValidationError
        from api.rest import RegisterRequest

        # Password too short (min 8 chars)
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="weakpassuser",
                password="weak",
                nombre="Weak User",
            )

    def test_register_invalid_username(self, ctrl):
        """Test registration with invalid username fails (Pydantic validation)."""
        from pydantic import ValidationError
        from api.rest import RegisterRequest

        # Username with invalid characters
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="invalid user!",
                password="SecurePass1",
                nombre="Invalid User",
            )
