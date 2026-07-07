"""
Django forms for authentication and onboarding.

Server-side validation for all registration and login flows.
Uses Iranian phone validation from services.phone.
"""

from django import forms

from .services.phone import normalize_phone, validate_iranian_phone


class LoginPhoneForm(forms.Form):
    """Phone number input for login OTP request."""

    phone = forms.CharField(
        max_length=20,
        min_length=11,
        error_messages={
            "required": "شماره موبایل الزامی است.",
            "min_length": "شماره موبایل باید حداقل ۱۱ رقم باشد.",
            "max_length": "شماره موبایل نامعتبر است.",
        },
    )

    def clean_phone(self):
        phone = self.cleaned_data["phone"]
        phone = normalize_phone(phone)
        if not validate_iranian_phone(phone):
            raise forms.ValidationError("شماره موبایل وارد شده معتبر نیست. فرمت صحیح: 09xxxxxxxxx")
        return phone


class OTPVerifyForm(forms.Form):
    """OTP code verification form."""

    code = forms.CharField(
        max_length=5,
        min_length=5,
        error_messages={
            "required": "کد تأیید الزامی است.",
            "min_length": "کد تأیید باید ۵ رقم باشد.",
            "max_length": "کد تأیید باید ۵ رقم باشد.",
        },
    )

    def clean_code(self):
        code = self.cleaned_data["code"]
        if not code.isdigit():
            raise forms.ValidationError("کد تأیید باید فقط شامل اعداد باشد.")
        return code


class CustomerRegistrationForm(forms.Form):
    """Customer/family registration form."""

    full_name = forms.CharField(
        max_length=255,
        error_messages={"required": "نام و نام خانوادگی الزامی است."},
    )
    phone = forms.CharField(
        max_length=20,
        min_length=11,
        error_messages={
            "required": "شماره موبایل الزامی است.",
            "min_length": "شماره موبایل باید حداقل ۱۱ رقم باشد.",
        },
    )
    city = forms.CharField(
        max_length=100,
        required=False,
    )
    relation_to_elder = forms.CharField(
        max_length=50,
        required=False,
    )
    terms = forms.BooleanField(
        error_messages={"required": "پذیرش قوانین استفاده الزامی است."},
    )

    def clean_phone(self):
        phone = self.cleaned_data["phone"]
        phone = normalize_phone(phone)
        if not validate_iranian_phone(phone):
            raise forms.ValidationError("شماره موبایل وارد شده معتبر نیست.")
        return phone


class CaregiverRegistrationForm(forms.Form):
    """Caregiver/provider registration form with optional company affiliation."""

    full_name = forms.CharField(
        max_length=255,
        error_messages={"required": "نام و نام خانوادگی الزامی است."},
    )
    phone = forms.CharField(
        max_length=20,
        min_length=11,
        error_messages={
            "required": "شماره موبایل الزامی است.",
            "min_length": "شماره موبایل باید حداقل ۱۱ رقم باشد.",
        },
    )
    specialty = forms.CharField(
        max_length=100,
        required=False,
    )
    city = forms.CharField(
        max_length=100,
        required=False,
    )
    # Optional company affiliation
    company_code = forms.CharField(
        max_length=100,
        required=False,
    )
    company_name = forms.CharField(
        max_length=255,
        required=False,
    )
    terms = forms.BooleanField(
        error_messages={"required": "پذیرش قوانین استفاده الزامی است."},
    )

    def clean_phone(self):
        phone = self.cleaned_data["phone"]
        phone = normalize_phone(phone)
        if not validate_iranian_phone(phone):
            raise forms.ValidationError("شماره موبایل وارد شده معتبر نیست.")
        return phone

    @property
    def has_company_request(self):
        """Check if caregiver wants company affiliation."""
        return bool(
            self.cleaned_data.get("company_code") or self.cleaned_data.get("company_name")
        )


class CompanyRegistrationForm(forms.Form):
    """Company admin registration — creates organization + admin user."""

    # Admin info
    admin_name = forms.CharField(
        max_length=255,
        error_messages={"required": "نام مدیر الزامی است."},
    )
    phone = forms.CharField(
        max_length=20,
        min_length=11,
        error_messages={
            "required": "شماره موبایل الزامی است.",
            "min_length": "شماره موبایل باید حداقل ۱۱ رقم باشد.",
        },
    )
    admin_role = forms.CharField(
        max_length=100,
        required=False,
    )

    # Organization info
    company_name = forms.CharField(
        max_length=255,
        error_messages={"required": "نام شرکت الزامی است."},
    )
    company_type = forms.CharField(
        max_length=100,
        required=False,
    )
    city = forms.CharField(
        max_length=100,
        required=False,
    )
    team_size = forms.CharField(
        max_length=20,
        required=False,
    )
    terms = forms.BooleanField(
        error_messages={"required": "پذیرش قوانین استفاده الزامی است."},
    )

    def clean_phone(self):
        phone = self.cleaned_data["phone"]
        phone = normalize_phone(phone)
        if not validate_iranian_phone(phone):
            raise forms.ValidationError("شماره موبایل وارد شده معتبر نیست.")
        return phone
