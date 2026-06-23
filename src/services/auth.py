"""
Authentication service for user management

Hybrid password hashing:
- New users: PBKDF2 with a random per-user salt. Stored as "salt:hash".
- Legacy compatibility: AuthService.verify_password transparently falls
  back to the historical hardcoded salt when stored hashes don't carry one.

Authenticate() returns session info enriched with the user's role and
resolved permission list (RBAC), sourced from the SQLite database via
DatabaseManager when available.

JWT support:
- create_access_token() / create_refresh_token() for API auth
- verify_access_token() / verify_refresh_token() for token validation
- Revoke refresh token on logout
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

import jwt

from config.settings import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SESSION_TIMEOUT_MINUTES,
)
from utils.exceptions import AuthenticationException
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Legacy hardcoded salt, kept only for backward compatibility with the
# passwords hashed before this refactor (e.g. admin/Admin123).
_LEGACY_SALT = "inventario2024"
_PBKDF2_ITERATIONS = 100_000
_HASH_ALGO = "sha256"


def _hash_with_salt(password: str, salt: str) -> str:
    """Run PBKDF2-HMAC with the given salt. Returns hex digest."""
    return hashlib.pbkdf2_hmac(
        _HASH_ALGO,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ITERATIONS,
    ).hex()


def _hash_password_new(password: str) -> str:
    """Hash a password with a fresh random salt. Returns 'salt:hash'."""
    salt = secrets.token_hex(16)
    digest = _hash_with_salt(password, salt)
    return f"{salt}:{digest}"


def _verify_new_format(stored: str, password: str) -> bool:
    """Verify a 'salt:hash' style stored value."""
    try:
        salt, digest = stored.split(":", 1)
    except ValueError:
        return False
    candidate = _hash_with_salt(password, salt)
    return hmac.compare_digest(digest, candidate)


def _verify_legacy(stored: str, password: str) -> bool:
    """Verify against the legacy hardcoded salt. Returns True on match."""
    candidate = _hash_with_salt(password, _LEGACY_SALT)
    return hmac.compare_digest(stored, candidate)


class AuthService:
    """Authentication and session management"""

    def __init__(self, db=None):
        self.sessions: dict[str, dict] = {}
        self._db = db

    @staticmethod
    def hash_password(password: str) -> str:
        """Public helper: hash a brand-new password with a random salt."""
        return _hash_password_new(password)

    @staticmethod
    def verify_password(stored: str, password: str) -> bool:
        """Verify a stored hash against a plaintext password.

        Supports both formats:
        - New: "salt:hash" (random salt per user)
        - Legacy: hex hash with the historical hardcoded salt
        """
        if not stored or not password:
            return False
        if ":" in stored:
            return _verify_new_format(stored, password)
        return _verify_legacy(stored, password)

    def authenticate(self, username: str, password: str) -> dict:
        """Authenticate user and create session.

        Returns:
            Dict with token, username, expires_in, rol (str), permissions (list).
            Raises AuthenticationException on failure.
        """
        if not username or not password:
            logger.warning("Authentication attempt with empty credentials")
            raise AuthenticationException("Username and password required")

        user = self._db.obtener_usuario_por_username_full(username) if self._db else None
        if not user:
            logger.warning(f"Authentication failed: user {username} not found")
            raise AuthenticationException("Invalid credentials")

        stored_hash = user["password_hash"]
        if not self.verify_password(stored_hash, password):
            logger.warning(f"Authentication failed: wrong password for {username}")
            raise AuthenticationException("Invalid credentials")

        rol, permissions = self._resolve_role_and_permissions(username)

        # Create session
        session_token = hashlib.sha256(
            f"{username}{datetime.now().isoformat()}{secrets.token_hex(8)}".encode()
        ).hexdigest()

        session_data = {
            "username": username,
            "rol": rol,
            "permissions": permissions,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(minutes=SESSION_TIMEOUT_MINUTES),
            "last_activity": datetime.now(),
        }

        self.sessions[session_token] = session_data
        logger.info(f"User {username} authenticated as '{rol}' with {len(permissions)} permissions")

        return {
            "token": session_token,
            "username": username,
            "rol": rol,
            "permissions": permissions,
            "expires_in": SESSION_TIMEOUT_MINUTES,
        }

    def _resolve_role_and_permissions(self, username: str):
        """Return (rol_name, permissions_list) for a username from the DB."""
        try:
            user_row = self._db.obtener_usuario_por_username_full(username)
            if not user_row:
                raise AuthenticationException("Invalid credentials")
            perms = self._db.obtener_permisos_de_usuario(user_row["id"])
            roles = self._db.obtener_roles_de_usuario(user_row["id"])
            rol_name = roles[0]["nombre"] if roles else (user_row.get("rol") or "operador").lower()
            return rol_name, perms
        except AuthenticationException:
            raise
        except Exception as e:
            logger.warning(f"RBAC resolution failed for {username}: {e}")
            raise AuthenticationException("Invalid credentials")

    def validate_session(self, token: str) -> bool:
        """Validate if session is active"""
        if token not in self.sessions:
            return False

        session = self.sessions[token]
        if datetime.now() > session["expires_at"]:
            del self.sessions[token]
            return False

        session["last_activity"] = datetime.now()
        return True

    def logout(self, token: str):
        """End user session"""
        if token in self.sessions:
            username = self.sessions[token]["username"]
            del self.sessions[token]
            logger.info(f"User {username} logged out")

    def get_current_user(self, token: str) -> str | None:
        """Get current authenticated user"""
        if self.validate_session(token):
            return self.sessions[token]["username"]
        return None

    def get_session_permissions(self, token: str) -> list:
        if self.validate_session(token):
            return self.sessions[token].get("permissions", [])
        return []

    def get_session_role(self, token: str) -> str | None:
        if self.validate_session(token):
            return self.sessions[token].get("rol")
        return None

    # ============ JWT Methods ============

    def create_access_token(self, username: str, rol: str, permissions: list) -> str:
        """Create a short-lived JWT access token."""
        now = datetime.utcnow()
        payload = {
            "sub": username,
            "rol": rol,
            "permissions": permissions,
            "iat": now,
            "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            "type": "access",
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    def create_refresh_token(self, username: str, user_id: int) -> str:
        """Create a long-lived refresh token and store it in DB."""
        now = datetime.utcnow()
        jti = secrets.token_hex(16)
        expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        # Store in database
        if self._db:
            try:
                with self._db._get_connection() as conn:
                    conn.execute(
                        """INSERT INTO refresh_tokens (jti, user_id, username, expires_at, created_at)
                           VALUES (?, ?, ?, ?, ?)""",
                        (jti, user_id, username, expires_at.isoformat(), now.isoformat()),
                    )
                    conn.commit()
            except Exception as e:
                logger.error(f"Failed to store refresh token: {e}")
                raise AuthenticationException("Failed to create refresh token")

        payload = {
            "sub": username,
            "jti": jti,
            "iat": now,
            "exp": expires_at,
            "type": "refresh",
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    def verify_access_token(self, token: str) -> dict | None:
        """Verify and decode an access token. Returns payload or None."""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            if payload.get("type") != "access":
                return None
            return payload
        except jwt.ExpiredSignatureError:
            logger.debug("Access token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"Invalid access token: {e}")
            return None

    def verify_refresh_token(self, token: str) -> dict | None:
        """Verify a refresh token. Checks JWT validity + DB revocation."""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            if payload.get("type") != "refresh":
                return None

            jti = payload.get("jti")
            if not jti or not self._db:
                return None

            # Check if revoked in database
            with self._db._get_connection() as conn:
                row = conn.execute(
                    "SELECT revoked FROM refresh_tokens WHERE jti = ?", (jti,)
                ).fetchone()
                if not row or row["revoked"]:
                    return None

            return payload
        except jwt.ExpiredSignatureError:
            logger.debug("Refresh token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"Invalid refresh token: {e}")
            return None

    def revoke_refresh_token(self, jti: str) -> bool:
        """Revoke a refresh token by marking it in the database."""
        if not self._db:
            return False
        try:
            with self._db._get_connection() as conn:
                conn.execute("UPDATE refresh_tokens SET revoked = 1 WHERE jti = ?", (jti,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to revoke refresh token: {e}")
            return False
