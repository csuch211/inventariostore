"""Tests for AuthService: password hashing, sessions, JWT, password reset, email verification."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import jwt
import pytest

from services.auth import (
    AuthService,
    _hash_password_new,
    _hash_with_salt,
    _verify_legacy,
    _verify_new_format,
)
from utils.exceptions import AuthenticationException

# ============ Password Hashing (unit-level, no DB) ============


class TestPasswordHashing:
    def test_hash_password_new_returns_salt_hash_format(self):
        hashed = _hash_password_new("TestPass123")
        assert ":" in hashed
        salt, digest = hashed.split(":", 1)
        assert len(salt) == 32  # 16 bytes hex
        assert len(digest) == 64  # sha256 hex

    def test_hash_changes_with_salt(self):
        h1 = _hash_password_new("SamePassword")
        h2 = _hash_password_new("SamePassword")
        assert h1 != h2  # different salts

    def test_verify_new_format_valid(self):
        hashed = _hash_password_new("MyPassword")
        assert _verify_new_format(hashed, "MyPassword") is True

    def test_verify_new_format_invalid(self):
        hashed = _hash_password_new("MyPassword")
        assert _verify_new_format(hashed, "WrongPassword") is False

    def test_verify_new_format_malformed(self):
        assert _verify_new_format("no-colon", "any") is False

    def test_verify_legacy_valid(self):
        stored = _hash_with_salt("LegacyPass", "inventario2024")
        assert _verify_legacy(stored, "LegacyPass") is True

    def test_verify_legacy_invalid(self):
        stored = _hash_with_salt("LegacyPass", "inventario2024")
        assert _verify_legacy(stored, "Wrong") is False

    def test_hash_and_verify_static_methods(self):
        hashed = AuthService.hash_password("NewPass!")
        assert AuthService.verify_password(hashed, "NewPass!") is True
        assert AuthService.verify_password(hashed, "Wrong") is False
        assert AuthService.verify_password("", "anything") is False
        assert AuthService.verify_password("anything", "") is False


# ============ AuthService with mock DB ============


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.obtener_usuario_por_username_full.return_value = {
        "id": 1,
        "username": "testuser",
        "password_hash": _hash_password_new("ValidPass123"),
        "nombre": "Test User",
        "rol": "operador",
        "activo": 1,
    }
    db.obtener_permisos_de_usuario.return_value = ["productos.leer", "stock.leer"]
    db.obtener_roles_de_usuario.return_value = [{"nombre": "operador"}]

    def fake_get_connection():
        conn = MagicMock()
        conn.__enter__.return_value = conn

        def _execute_side_effect(sql, params=None):
            result = MagicMock()
            if "refresh_tokens" in sql:
                row = MagicMock()
                row.__getitem__.side_effect = lambda k: 0 if k == "revoked" else None
                result.fetchone.return_value = row
            elif "activo" in sql:
                row = MagicMock()
                row.__getitem__.return_value = 1
                result.fetchone.return_value = row
            else:
                result.fetchone.return_value = None
            return result

        conn.execute.side_effect = _execute_side_effect
        return conn

    db._get_connection = fake_get_connection
    return db


@pytest.fixture
def auth(mock_db):
    return AuthService(db=mock_db)


class TestAuthServiceAuthenticate:
    def test_authenticate_success(self, auth):
        result = auth.authenticate("testuser", "ValidPass123")
        assert result["username"] == "testuser"
        assert result["rol"] == "operador"
        assert "token" in result
        assert len(result["permissions"]) == 2

    def test_authenticate_empty_username(self, auth):
        with pytest.raises(AuthenticationException, match="Username and password required"):
            auth.authenticate("", "pass")

    def test_authenticate_empty_password(self, auth):
        with pytest.raises(AuthenticationException, match="Username and password required"):
            auth.authenticate("user", "")

    def test_authenticate_invalid_user(self, auth, mock_db):
        mock_db.obtener_usuario_por_username_full.return_value = None
        with pytest.raises(AuthenticationException, match="Invalid credentials"):
            auth.authenticate("unknown", "pass")

    def test_authenticate_wrong_password(self, auth):
        with pytest.raises(AuthenticationException, match="Invalid credentials"):
            auth.authenticate("testuser", "WrongPassword")


class TestAuthServiceSessions:
    def test_validate_session_valid(self, auth):
        result = auth.authenticate("testuser", "ValidPass123")
        assert auth.validate_session(result["token"]) is True

    def test_validate_session_invalid_token(self, auth):
        assert auth.validate_session("nonexistent_token") is False

    def test_logout_removes_session(self, auth):
        result = auth.authenticate("testuser", "ValidPass123")
        token = result["token"]
        auth.logout(token)
        assert auth.validate_session(token) is False

    def test_get_current_user(self, auth):
        result = auth.authenticate("testuser", "ValidPass123")
        assert auth.get_current_user(result["token"]) == "testuser"
        assert auth.get_current_user("badtoken") is None

    def test_get_session_permissions(self, auth):
        result = auth.authenticate("testuser", "ValidPass123")
        perms = auth.get_session_permissions(result["token"])
        assert "productos.leer" in perms

    def test_get_session_role(self, auth):
        result = auth.authenticate("testuser", "ValidPass123")
        assert auth.get_session_role(result["token"]) == "operador"

    def test_expired_session_cleaned(self, auth):
        result = auth.authenticate("testuser", "ValidPass123")
        token = result["token"]
        # Manually expire the session
        auth.sessions[token]["expires_at"] = datetime.now() - timedelta(seconds=1)
        assert auth.validate_session(token) is False

    def test_auto_renew_session(self, auth):
        result = auth.authenticate("testuser", "ValidPass123")
        token = result["token"]
        # Set expiration close to now (less than 5 min remaining)
        auth.sessions[token]["expires_at"] = datetime.now() + timedelta(seconds=60)
        assert auth.validate_session(token) is True


class TestAuthServiceJWT:
    def test_create_access_token_returns_jwt(self, auth):
        token = auth.create_access_token("testuser", "admin", ["all"])
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_verify_access_token_valid(self, auth):
        token = auth.create_access_token("testuser", "admin", ["all"])
        payload = auth.verify_access_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["rol"] == "admin"
        assert payload["type"] == "access"

    def test_verify_access_token_expired(self, auth):
        expired_payload = {
            "sub": "testuser",
            "rol": "admin",
            "permissions": [],
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "type": "access",
        }
        from config.settings import JWT_ALGORITHM, JWT_SECRET_KEY
        expired_token = jwt.encode(expired_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        assert auth.verify_access_token(expired_token) is None

    def test_verify_access_token_wrong_type(self, auth):
        refresh_token = auth.create_refresh_token("testuser", 1)
        assert auth.verify_access_token(refresh_token) is None

    def test_verify_access_token_invalid(self, auth):
        assert auth.verify_access_token("invalid.jwt.token") is None

    def test_create_and_verify_refresh_token(self, auth):
        token = auth.create_refresh_token("testuser", 1)
        payload = auth.verify_refresh_token(token)
        assert payload is not None
        assert payload["type"] == "refresh"
        assert payload["sub"] == "testuser"

    def test_revoke_refresh_token(self, auth, mock_db):
        # Mock DB: token exists and not revoked initially
        def fake_execute(sql, params=None):
            result = MagicMock()
            if "SELECT" in sql or "select" in sql:
                if "revoked" in sql or "revoked" in sql.lower():
                    row = MagicMock()
                    row.__getitem__.return_value = 0
                    result.fetchone.return_value = row
                else:
                    row = MagicMock()
                    row["cnt"] = 0
                    result.fetchone.return_value = row
            return result

        mock_db._get_connection = lambda: MagicMock(
            __enter__=lambda s: MagicMock(execute=fake_execute, commit=lambda: None),
            __exit__=lambda *a: None,
        )

        auth.create_refresh_token("testuser", 1)
        assert auth.revoke_refresh_token("some_jti") is True


class TestAuthServicePasswordReset:
    def test_create_password_reset_token(self, auth, mock_db):
        # Simulate user found
        mock_db.obtener_usuario_por_username_full.return_value = {
            "id": 1, "username": "testuser"
        }
        token = auth.create_password_reset_token("testuser")
        assert token is not None
        assert len(token) > 20

    def test_create_password_reset_token_user_not_found(self, auth, mock_db):
        mock_db.obtener_usuario_por_username_full.return_value = None
        token = auth.create_password_reset_token("unknown")
        assert token is None

    def test_verify_password_reset_token_invalid(self, auth):
        assert auth.verify_password_reset_token("invalid_token") is None

    def test_reset_password_invalid_token(self, auth):
        assert auth.reset_password("invalid_token", "NewPass123") is False


class TestAuthServiceEmailVerification:
    def test_create_email_verification_token(self, auth):
        token = auth.create_email_verification_token(1)
        assert token is not None
        assert len(token) > 20

    def test_verify_email_token_invalid(self, auth):
        assert auth.verify_email_token("bad_token") is None

    def test_is_email_verified(self, auth, mock_db):
        assert auth.is_email_verified(1) is True

    def test_confirm_email_invalid_token(self, auth):
        assert auth.confirm_email("bad_token") is False
