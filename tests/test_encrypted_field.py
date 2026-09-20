"""
Tests for the EncryptedCharField.
"""

from cryptography.fernet import Fernet


class TestEncryptedCharField:
    """Unit tests for Fernet-based encrypted field (no DB required)."""

    def test_encrypt_decrypt_roundtrip(self, settings):
        key = Fernet.generate_key().decode()
        settings.FIELD_ENCRYPTION_KEY = key

        from apps.core.fields import EncryptedCharField

        field = EncryptedCharField()
        plaintext = "secret-api-key-12345"
        ciphertext = field.get_prep_value(plaintext)

        # Ciphertext should differ from plaintext
        assert ciphertext != plaintext
        # Decrypted value should match original
        decrypted = field.from_db_value(ciphertext, None, None)
        assert decrypted == plaintext

    def test_none_value_passthrough(self, settings):
        key = Fernet.generate_key().decode()
        settings.FIELD_ENCRYPTION_KEY = key

        from apps.core.fields import EncryptedCharField

        field = EncryptedCharField()
        assert field.get_prep_value(None) is None
        assert field.from_db_value(None, None, None) is None

    def test_invalid_ciphertext_returns_none(self, settings):
        key = Fernet.generate_key().decode()
        settings.FIELD_ENCRYPTION_KEY = key

        from apps.core.fields import EncryptedCharField

        field = EncryptedCharField()
        result = field.from_db_value("not-valid-ciphertext", None, None)
        assert result is None

    def test_different_keys_cannot_decrypt(self, settings):
        key1 = Fernet.generate_key().decode()
        key2 = Fernet.generate_key().decode()

        settings.FIELD_ENCRYPTION_KEY = key1
        from apps.core.fields import EncryptedCharField

        field = EncryptedCharField()
        ciphertext = field.get_prep_value("secret")

        settings.FIELD_ENCRYPTION_KEY = key2
        # Must reimport since field caches nothing — but _get_fernet reads settings live
        result = field.from_db_value(ciphertext, None, None)
        assert result is None  # wrong key → invalid token → returns None
