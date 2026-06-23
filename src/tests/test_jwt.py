"""Tests for JWT authentication."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime, timedelta, timezone

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

        now = datetime.now(timezone.utc)
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

        now = datetime.now(timezone.utc)
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

        now = datetime.now(timezone.utc)
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

        now = datetime.now(timezone.utc)
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
            email="test@example.com",
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
            email="first@example.com",
        )
        asyncio.run(register(req))

        # Second registration should fail
        req2 = RegisterRequest(
            username="duplicate_user",
            password="SecurePass2",
            nombre="Second User",
            email="second@example.com",
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
                email="weak@example.com",
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
                email="invalid@example.com",
            )


class TestPasswordReset:
    def test_forgot_password_returns_success(self, ctrl):
        """Test forgot-password always returns success (prevents enumeration)."""
        from api.rest import forgot_password, ForgotPasswordRequest
        import asyncio

        req = ForgotPasswordRequest(username="admin")
        result = asyncio.run(forgot_password(req))
        assert "message" in result

    def test_forgot_password_nonexistent_user(self, ctrl):
        """Test forgot-password for nonexistent user still returns success."""
        from api.rest import forgot_password, ForgotPasswordRequest
        import asyncio

        req = ForgotPasswordRequest(username="nonexistent_user_xyz")
        result = asyncio.run(forgot_password(req))
        assert "message" in result

    def test_create_and_verify_reset_token(self, ctrl):
        """Test creating and verifying a password reset token."""
        from services.auth import AuthService

        auth_svc = AuthService(db=ctrl.db)

        # Create token
        token = auth_svc.create_password_reset_token("admin")
        assert token is not None
        assert len(token) > 0

        # Verify token
        token_info = auth_svc.verify_password_reset_token(token)
        assert token_info is not None
        assert token_info["username"] == "admin"

    def test_reset_password_valid_token(self, ctrl):
        """Test resetting password with valid token."""
        from services.auth import AuthService

        auth_svc = AuthService(db=ctrl.db)

        # Create token
        token = auth_svc.create_password_reset_token("admin")
        assert token is not None

        # Reset password
        success = auth_svc.reset_password(token, "NewSecurePass1")
        assert success is True

        # Verify old password no longer works
        user = ctrl.db.obtener_usuario_por_username_full("admin")
        assert AuthService.verify_password(user["password_hash"], "Admin123") is False

        # Verify new password works
        assert AuthService.verify_password(user["password_hash"], "NewSecurePass1") is True

    def test_reset_password_invalid_token(self, ctrl):
        """Test resetting password with invalid token fails."""
        from services.auth import AuthService

        auth_svc = AuthService(db=ctrl.db)
        success = auth_svc.reset_password("invalid_token_123", "NewSecurePass1")
        assert success is False

    def test_reset_password_token_cannot_be_reused(self, ctrl):
        """Test that a reset token cannot be used twice."""
        from services.auth import AuthService

        auth_svc = AuthService(db=ctrl.db)

        # Create and use token
        token = auth_svc.create_password_reset_token("admin")
        success = auth_svc.reset_password(token, "NewSecurePass1")
        assert success is True

        # Try to reuse token
        success2 = auth_svc.reset_password(token, "AnotherPass1")
        assert success2 is False

    def test_reset_password_invalidates_old_tokens(self, ctrl):
        """Test that creating a new reset token invalidates old ones."""
        from services.auth import AuthService

        auth_svc = AuthService(db=ctrl.db)

        # Create first token
        token1 = auth_svc.create_password_reset_token("admin")
        assert token1 is not None

        # Create second token (should invalidate first)
        token2 = auth_svc.create_password_reset_token("admin")
        assert token2 is not None

        # First token should no longer work
        token_info = auth_svc.verify_password_reset_token(token1)
        assert token_info is None

        # Second token should work
        token_info2 = auth_svc.verify_password_reset_token(token2)
        assert token_info2 is not None


class TestEmailVerification:
    def test_create_and_verify_email_token(self, ctrl):
        """Test creating and verifying an email verification token."""
        from services.auth import AuthService

        auth_svc = AuthService(db=ctrl.db)

        # Get admin user ID
        user = ctrl.db.obtener_usuario_por_username_full("admin")
        assert user is not None

        # Create token
        token = auth_svc.create_email_verification_token(user["id"])
        assert token is not None
        assert len(token) > 0

        # Verify token
        token_info = auth_svc.verify_email_token(token)
        assert token_info is not None
        assert token_info["username"] == "admin"

    def test_confirm_email_activates_account(self, ctrl):
        """Test that confirming email activates the user account."""
        from services.auth import AuthService

        auth_svc = AuthService(db=ctrl.db)

        # Create a user that is inactive
        password_hash = AuthService.hash_password("TestPass1")
        user_id = ctrl.db.crear_usuario(
            username="inactive_user",
            password_hash=password_hash,
            nombre="Inactive User",
            rol="viewer",
        )
        # Deactivate
        with ctrl.db._get_connection() as conn:
            conn.execute("UPDATE usuarios SET activo = 0 WHERE id = ?", (user_id,))
            conn.commit()

        # Verify user is inactive
        assert auth_svc.is_email_verified(user_id) is False

        # Create verification token
        token = auth_svc.create_email_verification_token(user_id)
        assert token is not None

        # Confirm email
        success = auth_svc.confirm_email(token)
        assert success is True

        # Verify user is now active
        assert auth_svc.is_email_verified(user_id) is True

    def test_confirm_email_invalid_token(self, ctrl):
        """Test confirming email with invalid token fails."""
        from services.auth import AuthService

        auth_svc = AuthService(db=ctrl.db)
        success = auth_svc.confirm_email("invalid_token_123")
        assert success is False

    def test_confirm_email_already_verified(self, ctrl):
        """Test confirming email for already verified user is idempotent."""
        from services.auth import AuthService

        auth_svc = AuthService(db=ctrl.db)

        # Get admin user (already active)
        user = ctrl.db.obtener_usuario_por_username_full("admin")
        assert user is not None

        # Create token
        token = auth_svc.create_email_verification_token(user["id"])
        assert token is not None

        # Confirm email (should succeed even though already active)
        success = auth_svc.confirm_email(token)
        assert success is True

    def test_email_token_cannot_be_reused(self, ctrl):
        """Test that an email verification token cannot be used twice."""
        from services.auth import AuthService

        auth_svc = AuthService(db=ctrl.db)

        # Create a user that is inactive
        password_hash = AuthService.hash_password("TestPass1")
        user_id = ctrl.db.crear_usuario(
            username="reuse_user",
            password_hash=password_hash,
            nombre="Reuse User",
            rol="viewer",
        )
        with ctrl.db._get_connection() as conn:
            conn.execute("UPDATE usuarios SET activo = 0 WHERE id = ?", (user_id,))
            conn.commit()

        # Create and use token
        token = auth_svc.create_email_verification_token(user_id)
        success = auth_svc.confirm_email(token)
        assert success is True

        # Try to reuse token
        success2 = auth_svc.confirm_email(token)
        assert success2 is False

    def test_resend_verification_endpoint(self, ctrl):
        """Test resend verification endpoint returns success."""
        from api.rest import resend_verification, ForgotPasswordRequest
        import asyncio

        req = ForgotPasswordRequest(username="admin")
        result = asyncio.run(resend_verification(req))
        assert "message" in result


class TestSMTPConfig:
    def test_get_smtp_config(self, ctrl):
        """Test getting SMTP configuration."""
        from api.rest import get_smtp_config_endpoint
        import asyncio

        result = asyncio.run(get_smtp_config_endpoint(user="admin"))
        assert "host" in result
        assert "port" in result
        assert "enabled" in result

    def test_save_smtp_config(self, ctrl):
        """Test saving SMTP configuration."""
        from api.rest import save_smtp_config, SMTPConfigIn
        import asyncio

        req = SMTPConfigIn(
            host="smtp.gmail.com",
            port=587,
            user="test@gmail.com",
            password="testpass",
            from_email="test@gmail.com",
            enabled=True,
        )
        result = asyncio.run(save_smtp_config(req, user="admin"))
        assert "message" in result

        # Verify config was saved
        from api.rest import get_smtp_config_endpoint
        config = asyncio.run(get_smtp_config_endpoint(user="admin"))
        assert config["host"] == "smtp.gmail.com"
        assert config["enabled"] is True
