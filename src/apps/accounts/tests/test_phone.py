"""Tests for phone validation and normalization."""

from django.test import TestCase

from apps.accounts.services.phone import normalize_phone, validate_iranian_phone


class NormalizePhoneTest(TestCase):
    """Test phone number normalization."""

    def test_already_normalized(self):
        self.assertEqual(normalize_phone("09121234567"), "09121234567")

    def test_with_plus98_prefix(self):
        self.assertEqual(normalize_phone("+989121234567"), "09121234567")

    def test_with_98_prefix(self):
        self.assertEqual(normalize_phone("989121234567"), "09121234567")

    def test_strips_spaces(self):
        self.assertEqual(normalize_phone("0912 123 4567"), "09121234567")

    def test_strips_dashes(self):
        self.assertEqual(normalize_phone("0912-123-4567"), "09121234567")


class ValidateIranianPhoneTest(TestCase):
    """Test Iranian mobile phone validation."""

    def test_valid_phone(self):
        self.assertTrue(validate_iranian_phone("09121234567"))

    def test_valid_with_prefix(self):
        self.assertTrue(validate_iranian_phone("+989121234567"))

    def test_invalid_too_short(self):
        self.assertFalse(validate_iranian_phone("0912123"))

    def test_invalid_landline(self):
        self.assertFalse(validate_iranian_phone("02112345678"))

    def test_invalid_empty(self):
        self.assertFalse(validate_iranian_phone(""))

    def test_invalid_letters(self):
        self.assertFalse(validate_iranian_phone("0912abc4567"))
