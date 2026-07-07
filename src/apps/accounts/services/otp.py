"""
OTP Service — generate, hash, verify, rate-limit.

In DEBUG mode, the OTP code is logged to console for development.
In production, this will integrate with an SMS provider (Kavenegar, etc.).
"""

import hashlib
import logging
import random
import string
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.accounts.models.otp import OTPChallenge, OTPPurpose

logger = logging.getLogger(__name__)

# Configuration
OTP_LENGTH = 5
OTP_EXPIRY_SECONDS = 120  # 2 minutes
OTP_MAX_ATTEMPTS = 5
OTP_COOLDOWN_SECONDS = 90  # Min seconds between OTP requests for same phone
OTP_MAX_REQUESTS_PER_HOUR = 5  # Max OTP requests per phone per hour


class OTPService:
    """
    Central service for OTP lifecycle management.

    Responsibilities:
    - Generate numeric OTP codes
    - Store hashed OTP challenges
    - Verify OTP attempts with rate limiting
    - Enforce cooldown between requests
    """

    @classmethod
    def request_otp(
        cls,
        *,
        phone: str,
        purpose: str = OTPPurpose.LOGIN,
        request_ip: str | None = None,
        user_agent: str = "",
    ) -> tuple[OTPChallenge, str | None]:
        """
        Create a new OTP challenge for the given phone.

        Returns:
            (challenge, dev_code) — dev_code is the plaintext OTP in DEBUG mode only.

        Raises:
            ValueError: If rate limit exceeded or cooldown not met.
        """
        # Rate limit: max requests per hour
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_count = OTPChallenge.objects.filter(
            phone=phone,
            created_at__gte=one_hour_ago,
        ).count()

        if recent_count >= OTP_MAX_REQUESTS_PER_HOUR:
            raise ValueError("تعداد درخواست‌های کد تأیید بیش از حد مجاز است. لطفاً بعداً تلاش کنید.")

        # Cooldown: min time between requests
        cooldown_threshold = timezone.now() - timedelta(seconds=OTP_COOLDOWN_SECONDS)
        recent_challenge = OTPChallenge.objects.filter(
            phone=phone,
            created_at__gte=cooldown_threshold,
        ).first()

        if recent_challenge:
            raise ValueError("لطفاً قبل از درخواست مجدد کد، چند لحظه صبر کنید.")

        # Generate OTP code
        code = cls._generate_code()
        code_hash = cls._hash_code(code)

        # Create challenge
        challenge = OTPChallenge.objects.create(
            phone=phone,
            purpose=purpose,
            code_hash=code_hash,
            expires_at=timezone.now() + timedelta(seconds=OTP_EXPIRY_SECONDS),
            max_attempts=OTP_MAX_ATTEMPTS,
            request_ip=request_ip,
            user_agent=user_agent[:500] if user_agent else "",
        )

        # Development: log OTP to console
        dev_code = None
        if settings.DEBUG:
            logger.info("🔑 [DEV OTP] Phone: %s | Code: %s | Purpose: %s", phone, code, purpose)
            dev_code = code

        # TODO: Production SMS dispatch placeholder
        # cls._send_sms(phone, code)

        return challenge, dev_code

    @classmethod
    def verify_otp(cls, *, phone: str, code: str, purpose: str = OTPPurpose.LOGIN) -> bool:
        """
        Verify an OTP code for the given phone.

        Returns True if verification succeeds, False otherwise.
        Increments attempt count on failure. Consumes challenge on success.
        """
        # Get the latest unconsumed challenge for this phone+purpose
        challenge = OTPChallenge.objects.filter(
            phone=phone,
            purpose=purpose,
            consumed_at__isnull=True,
        ).order_by("-created_at").first()

        if not challenge:
            return False

        if not challenge.is_valid:
            return False

        # Check code
        code_hash = cls._hash_code(code)
        if code_hash != challenge.code_hash:
            # Increment attempts
            challenge.attempts += 1
            challenge.save(update_fields=["attempts"])
            return False

        # Success — consume the challenge
        challenge.consumed_at = timezone.now()
        challenge.save(update_fields=["consumed_at"])
        return True

    @classmethod
    def _generate_code(cls) -> str:
        """Generate a random numeric OTP code."""
        return "".join(random.choices(string.digits, k=OTP_LENGTH))

    @classmethod
    def _hash_code(cls, code: str) -> str:
        """Hash OTP code using SHA-256."""
        return hashlib.sha256(code.encode("utf-8")).hexdigest()
