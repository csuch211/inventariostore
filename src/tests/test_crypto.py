"""Tests for utils/crypto.py — encryption/decryption."""

from utils.crypto import ENCRYPTED_PREFIX, decrypt_value, encrypt_value


class TestEncryptDecrypt:
    def test_roundtrip_basic(self):
        plain = "my_secret_password"
        encrypted = encrypt_value(plain)
        assert encrypted.startswith(ENCRYPTED_PREFIX)
        decrypted = decrypt_value(encrypted)
        assert decrypted == plain

    def test_roundtrip_empty_string(self):
        assert encrypt_value("") == ""
        assert decrypt_value("") == ""

    def test_roundtrip_special_chars(self):
        plain = "p@$$w0rd!#%^&*()"
        encrypted = encrypt_value(plain)
        assert decrypt_value(encrypted) == plain

    def test_roundtrip_unicode(self):
        plain = "contraseña_secreta_日本語"
        encrypted = encrypt_value(plain)
        assert decrypt_value(encrypted) == plain

    def test_roundtrip_long_string(self):
        plain = "A" * 1000
        encrypted = encrypt_value(plain)
        assert decrypt_value(encrypted) == plain

    def test_encrypted_has_prefix(self):
        encrypted = encrypt_value("test")
        assert encrypted.startswith(ENCRYPTED_PREFIX)

    def test_different_encryptions_same_result(self):
        """Fernet uses random IV, so same input produces different ciphertext."""
        plain = "test"
        enc1 = encrypt_value(plain)
        enc2 = encrypt_value(plain)
        # Both should decrypt to same value
        assert decrypt_value(enc1) == decrypt_value(enc2)

    def test_legacy_plaintext_passthrough(self):
        """Legacy plaintext values should pass through with a warning."""
        result = decrypt_value("plaintext_password")
        assert result == "plaintext_password"

    def test_decrypt_invalid_encrypted_returns_empty(self):
        """Decrypting invalid encrypted data should return empty string."""
        result = decrypt_value("enc:invalid_data_here")
        assert result == ""
