"""Tests for OTP service."""

from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models.otp import OTPChallenge, OTPPurpose
from apps.accounts.services.otp import OTPService


@override_settings(DEBUG=True)
class OTPServiceTest(TestCase):
    """Test OTP generation, hashing, and verification."""

    def test_request_otp_creates_challenge(self):
        challenge, dev_code = OTPService.request_otp(phone="09121234567", purpose=OTPPurpose.LOGIN)
        self.assertIsNotNone(challenge)
        self.assertIsNotNone(dev_code)
        self.assertEqual(len(dev_code), 5)
        self.assertTrue(dev_code.isdigit())
        self.assertEqual(challenge.phone, "09121234567")
        self.assertEqual(challenge.purpose, OTPPurpose.LOGIN)
        self.assertFalse(challenge.is_expired)
        self.assertFalse(challenge.is_consumed)

    def test_verify_otp_success(self):
        challenge, dev_code = OTPService.request_otp(phone="09121234567", purpose=OTPPurpose.LOGIN)
        result = OTPService.verify_otp(phone="09121234567", code=dev_code, purpose=OTPPurpose.LOGIN)
        self.assertTrue(result)
        challenge.refresh_from_db()
        self.assertIsNotNone(challenge.consumed_at)

    def test_verify_otp_wrong_code(self):
        OTPService.request_otp(phone="09121234567", purpose=OTPPurpose.LOGIN)
        result = OTPService.verify_otp(phone="09121234567", code="00000", purpose=OTPPurpose.LOGIN)
        self.assertFalse(result)

    def test_verify_otp_expired(self):
        challenge, dev_code = OTPService.request_otp(phone="09121234567", purpose=OTPPurpose.LOGIN)
        # Force expiry
        challenge.expires_at = timezone.now() - timedelta(seconds=1)
        challenge.save()

        result = OTPService.verify_otp(phone="09121234567", code=dev_code, purpose=OTPPurpose.LOGIN)
        self.assertFalse(result)

    def test_verify_otp_max_attempts(self):
        challenge, dev_code = OTPService.request_otp(phone="09121234567", purpose=OTPPurpose.LOGIN)
        # Exhaust attempts
        challenge.attempts = challenge.max_attempts
        challenge.save()

        result = OTPService.verify_otp(phone="09121234567", code=dev_code, purpose=OTPPurpose.LOGIN)
        self.assertFalse(result)

    def test_rate_limit_cooldown(self):
        """Second OTP request within cooldown period should fail."""
        OTPService.request_otp(phone="09121234567", purpose=OTPPurpose.LOGIN)
        with self.assertRaises(ValueError):
            OTPService.request_otp(phone="09121234567", purpose=OTPPurpose.LOGIN)

    def test_rate_limit_max_per_hour(self):
        """Exceeding max requests per hour should fail."""
        phone = "09129999999"
        # Create challenges to fill the hour quota
        for i in range(5):
            OTPChallenge.objects.create(
                phone=phone,
                purpose=OTPPurpose.LOGIN,
                code_hash="fake",
                expires_at=timezone.now() + timedelta(minutes=2),
                created_at=timezone.now() - timedelta(minutes=i * 2),
            )
        with self.assertRaises(ValueError):
            OTPService.request_otp(phone=phone, purpose=OTPPurpose.LOGIN)
