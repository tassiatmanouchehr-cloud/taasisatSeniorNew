"""
OTP Challenge model.

Stores OTP challenges for phone-based authentication.
OTP codes are stored as hashes — never as plaintext.
"""

import uuid

from django.db import models
from django.utils import timezone


class OTPPurpose(models.TextChoices):
    """Purpose of the OTP challenge."""

    LOGIN = "login", "Login"
    REGISTER = "register", "Register"


class OTPChallenge(models.Model):
    """
    Phone-based OTP challenge record.

    Security:
    - code_hash stores bcrypt/sha256 hash, never plaintext
    - max_attempts prevents brute force
    - expires_at prevents stale challenges
    - consumed_at prevents replay
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=20, db_index=True)
    purpose = models.CharField(
        max_length=20,
        choices=OTPPurpose.choices,
        default=OTPPurpose.LOGIN,
    )
    code_hash = models.CharField(
        max_length=128,
        help_text="SHA-256 hash of the OTP code.",
    )
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=5)
    request_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_otp_challenge"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["phone", "purpose", "-created_at"], name="idx_otp_phone_purpose"),
        ]

    def __str__(self):
        return f"OTP({self.phone}, {self.purpose}, expires={self.expires_at})"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_consumed(self):
        return self.consumed_at is not None

    @property
    def is_locked(self):
        return self.attempts >= self.max_attempts

    @property
    def is_valid(self):
        """Challenge is usable: not expired, not consumed, not locked."""
        return not self.is_expired and not self.is_consumed and not self.is_locked
