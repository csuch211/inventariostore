"""Encryption/decryption helpers for database secret values.

Uses **cryptography.fernet** when the package is available (recommended)
and falls back to a reversible XOR + base64 scheme otherwise.
"""

import base64
import hashlib

from config.settings import JWT_SECRET_KEY
from utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    from cryptography.fernet import Fernet as _Fernet

    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

ENCRYPTED_PREFIX = "enc:"

SECRET_KEYS = frozenset({"smtp_password", "wa_api_key", "tg_bot_token"})


def _derive_key() -> bytes:
    """Derive a 32-byte key from *JWT_SECRET_KEY* via SHA-256."""
    return hashlib.sha256(JWT_SECRET_KEY.encode("utf-8")).digest()


def encrypt_value(plain_text: str) -> str:
    """Encrypt *plain_text* and return a string prefixed with ``enc:``."""
    if not plain_text:
        return plain_text

    if HAS_CRYPTOGRAPHY:
        raw_key = base64.urlsafe_b64encode(_derive_key())
        f = _Fernet(raw_key)
        return ENCRYPTED_PREFIX + f.encrypt(plain_text.encode("utf-8")).decode("utf-8")

    _key = _derive_key()
    data = plain_text.encode("utf-8")
    keystream = _key * (len(data) // len(_key) + 1)
    keystream = keystream[:len(data)]
    encrypted = bytes(a ^ b for a, b in zip(data, keystream))
    return ENCRYPTED_PREFIX + base64.urlsafe_b64encode(encrypted).decode("utf-8")


def decrypt_value(encrypted: str) -> str:
    """Decrypt a value previously produced by :func:`encrypt_value`.

    If the value does **not** start with the ``enc:`` prefix it is
    considered legacy plaintext - a warning is logged and the value is
    returned unchanged so existing data keeps working transparently.
    """
    if not encrypted:
        return encrypted

    if not encrypted.startswith(ENCRYPTED_PREFIX):
        logger.warning(
            "Legacy plaintext secret detected for key - "
            "consider re-saving to enable encryption"
        )
        return encrypted

    payload = encrypted[len(ENCRYPTED_PREFIX):]

    if HAS_CRYPTOGRAPHY:
        raw_key = base64.urlsafe_b64encode(_derive_key())
        f = _Fernet(raw_key)
        try:
            return f.decrypt(payload.encode("utf-8")).decode("utf-8")
        except Exception as exc:
            logger.error("Fernet decryption failed: %s", exc)
            return ""

    try:
        _key = _derive_key()
        data = base64.urlsafe_b64decode(payload)
        keystream = _key * (len(data) // len(_key) + 1)
        keystream = keystream[:len(data)]
        return bytes(a ^ b for a, b in zip(data, keystream)).decode("utf-8")
    except Exception as exc:
        logger.error("Fallback decryption failed: %s", exc)
        return ""
