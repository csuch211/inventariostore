"""Re-export AuthService from the canonical location.

The real implementation lives in ``services.auth``. This module exists
solely so that ``from modules.auth.services.auth_service import AuthService``
continues to work without changing every caller.
"""

from services.auth import _LEGACY_SALT, AuthService, _hash_with_salt

__all__ = ["_LEGACY_SALT", "AuthService", "_hash_with_salt"]
