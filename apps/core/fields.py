"""
Encrypted field for storing secrets in the database.

Uses cryptography.Fernet (AES-128-CBC + HMAC-SHA256).
The key is read from settings.FIELD_ENCRYPTION_KEY (env var).
Values are NEVER logged.
"""

from __future__ import annotations

import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    key = getattr(settings, "FIELD_ENCRYPTION_KEY", "")
    if not key:
        raise ValueError(
            "FIELD_ENCRYPTION_KEY is not set. "
            "Generate: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""  # noqa: E501
        )
    # Accept both bytes and str
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


class EncryptedCharField(models.TextField):
    """
    A TextField that transparently encrypts/decrypts its value using Fernet.

    - Stores base64-encoded ciphertext in the database.
    - Returns the plaintext string when accessed from Python.
    - Never logs the plaintext value.
    """

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            fernet = _get_fernet()
            decrypted = fernet.decrypt(value.encode())
            return decrypted.decode("utf-8")
        except (InvalidToken, Exception):
            # Log a warning WITHOUT the value
            logger.warning("EncryptedCharField: failed to decrypt a value")
            return None

    def to_python(self, value):
        return value

    def get_prep_value(self, value):
        if value is None:
            return value
        fernet = _get_fernet()
        encrypted = fernet.encrypt(value.encode("utf-8"))
        return encrypted.decode("ascii")
