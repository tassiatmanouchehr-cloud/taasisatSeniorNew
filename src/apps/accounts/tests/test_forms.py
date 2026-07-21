"""Tests for authentication forms."""

from django.test import TestCase

from apps.accounts.forms import (
    CaregiverRegistrationForm,
    CompanyRegistrationForm,
    CustomerRegistrationForm,
    LoginPhoneForm,
    OTPVerifyForm,
)


class LoginPhoneFormTest(TestCase):
    """Test login phone form validation."""

    def test_valid_phone(self):
        form = LoginPhoneForm(data={"phone": "09121234567"})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["phone"], "09121234567")

    def test_valid_phone_with_prefix(self):
        form = LoginPhoneForm(data={"phone": "+989121234567"})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["phone"], "09121234567")

    def test_invalid_phone_too_short(self):
        form = LoginPhoneForm(data={"phone": "0912123"})
        self.assertFalse(form.is_valid())

    def test_empty_phone(self):
        form = LoginPhoneForm(data={"phone": ""})
        self.assertFalse(form.is_valid())

    def test_invalid_landline(self):
        form = LoginPhoneForm(data={"phone": "02112345678"})
        self.assertFalse(form.is_valid())


class OTPVerifyFormTest(TestCase):
    """Test OTP verification form."""

    def test_valid_code(self):
        form = OTPVerifyForm(data={"code": "12345"})
        self.assertTrue(form.is_valid())

    def test_code_too_short(self):
        form = OTPVerifyForm(data={"code": "123"})
        self.assertFalse(form.is_valid())

    def test_code_with_letters(self):
        form = OTPVerifyForm(data={"code": "12ab5"})
        self.assertFalse(form.is_valid())

    def test_empty_code(self):
        form = OTPVerifyForm(data={"code": ""})
        self.assertFalse(form.is_valid())


class CustomerRegistrationFormTest(TestCase):
    """Test customer registration form."""

    def test_valid_form(self):
        form = CustomerRegistrationForm(
            data={
                "full_name": "فاطمه رضایی",
                "phone": "09121234567",
                "city": "tehran",
                "relation_to_elder": "child",
                "terms": True,
            }
        )
        self.assertTrue(form.is_valid())

    def test_missing_name(self):
        form = CustomerRegistrationForm(
            data={
                "full_name": "",
                "phone": "09121234567",
                "terms": True,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("full_name", form.errors)

    def test_missing_terms(self):
        form = CustomerRegistrationForm(
            data={
                "full_name": "Test",
                "phone": "09121234567",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("terms", form.errors)


class CaregiverRegistrationFormTest(TestCase):
    """Test caregiver registration form."""

    def test_valid_without_company(self):
        form = CaregiverRegistrationForm(
            data={
                "full_name": "مریم احمدی",
                "phone": "09129876543",
                "specialty": "nurse",
                "city": "isfahan",
                "terms": True,
            }
        )
        self.assertTrue(form.is_valid())
        self.assertFalse(form.has_company_request)

    def test_valid_with_company_code(self):
        form = CaregiverRegistrationForm(
            data={
                "full_name": "مریم احمدی",
                "phone": "09129876543",
                "terms": True,
                "company_code": "TEST-1234",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.has_company_request)

    def test_valid_with_company_name(self):
        form = CaregiverRegistrationForm(
            data={
                "full_name": "Test",
                "phone": "09129876543",
                "terms": True,
                "company_name": "آژانس نور",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.has_company_request)


class CompanyRegistrationFormTest(TestCase):
    """Test company admin registration form."""

    def test_valid_form(self):
        form = CompanyRegistrationForm(
            data={
                "admin_name": "محمد کریمی",
                "phone": "09131112222",
                "admin_role": "owner",
                "company_name": "شرکت مراقبتی نور",
                "company_type": "care_agency",
                "city": "tehran",
                "team_size": "6-20",
                "terms": True,
            }
        )
        self.assertTrue(form.is_valid())

    def test_missing_company_name(self):
        form = CompanyRegistrationForm(
            data={
                "admin_name": "Test",
                "phone": "09131112222",
                "company_name": "",
                "terms": True,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("company_name", form.errors)
