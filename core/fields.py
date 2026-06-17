"""Custom model fields."""

from django.db import models

from .encryption import decrypt, encrypt


class EncryptedCharField(models.CharField):
    """A CharField that is encrypted at rest.

    Values are transparently encrypted on the way to the database and decrypted
    on the way out, so application code reads and writes plain strings. The
    stored ciphertext is longer than the plaintext, so size ``max_length``
    accordingly (a ~40-char token encrypts to ~180 chars).
    """

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return decrypt(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        return encrypt(value)
