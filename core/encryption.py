"""Symmetric encryption for secrets stored at rest (e.g. OAuth tokens).

Uses Fernet (AES-128-CBC + HMAC). The key comes from ``FIELD_ENCRYPTION_KEY``
when set (a urlsafe-base64 32-byte Fernet key); otherwise it is derived
deterministically from ``SECRET_KEY`` so the app works out of the box in dev.
For production, set a dedicated ``FIELD_ENCRYPTION_KEY`` and rotate ``SECRET_KEY``
independently.
"""

import base64
import hashlib
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

logger = logging.getLogger(__name__)

# Fernet tokens are urlsafe-base64 of a payload whose first byte is the version
# 0x80, which always base64-encodes to a leading "gAAAAA".
_FERNET_PREFIX = "gAAAAA"


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    configured = getattr(settings, "FIELD_ENCRYPTION_KEY", "") or ""
    if configured:
        key = configured.encode()
    else:
        # Derive a stable 32-byte Fernet key from SECRET_KEY.
        digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt(value: str) -> str:
    """Encrypt a plaintext string to a urlsafe token string."""
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a token produced by :func:`encrypt`.

    Tolerates legacy plaintext values (returns them unchanged) so existing rows
    written before encryption was introduced keep working. A value that *looks*
    encrypted but fails to decrypt (wrong/rotated key, corruption) is NOT silently
    returned as-is — that would hand ciphertext back as a secret; it raises so the
    failure is visible instead of masked.
    """
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        if token.startswith(_FERNET_PREFIX):
            logger.warning("Failed to decrypt an encrypted field value (key rotated or corrupt?)")
            raise
        return token
