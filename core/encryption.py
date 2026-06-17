"""Symmetric encryption for secrets stored at rest (e.g. OAuth tokens).

Uses Fernet (AES-128-CBC + HMAC). The key comes from ``FIELD_ENCRYPTION_KEY``
when set (a urlsafe-base64 32-byte Fernet key); otherwise it is derived
deterministically from ``SECRET_KEY`` so the app works out of the box in dev.
For production, set a dedicated ``FIELD_ENCRYPTION_KEY`` and rotate ``SECRET_KEY``
independently.
"""

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


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
    written before encryption was introduced keep working.
    """
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return token
