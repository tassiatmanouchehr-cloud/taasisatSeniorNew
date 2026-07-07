"""
Authentication and onboarding views.

Working form-based views for phone OTP login and multi-path registration.
Uses Django session auth. OTP verified before account creation.
"""

import logging

from django.conf import settings
from django.contrib.auth import login as auth_login
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.kernel.models import UserAccount

from .forms import (
    CaregiverRegistrationForm,
    CompanyRegistrationForm,
    CustomerRegistrationForm,
    LoginPhoneForm,
    OTPVerifyForm,
)
from .models.otp import OTPPurpose
from .services.otp import OTPService
from .services.phone import normalize_phone
from .services.registration import RegistrationService

logger = logging.getLogger(__name__)


AUTHENTICATION_BACKEND = "django.contrib.auth.backends.ModelBackend"


def _get_client_ip(request):
    """Extract client IP from request."""
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Phone number entry for login. Sends OTP on valid submission."""
    if request.method == "POST":
        form = LoginPhoneForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data["phone"]
            try:
                challenge, dev_code = OTPService.request_otp(
                    phone=phone,
                    purpose=OTPPurpose.LOGIN,
                    request_ip=_get_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                )
                # Store phone in session for verify step
                request.session["otp_phone"] = phone
                request.session["otp_purpose"] = OTPPurpose.LOGIN
                if dev_code and settings.DEBUG:
                    request.session["dev_otp"] = dev_code
                return redirect("accounts:verify")
            except ValueError as e:
                form.add_error(None, str(e))
    else:
        form = LoginPhoneForm()

    return render(request, "accounts/login.html", {"form": form})


@require_http_methods(["GET"])
def register_view(request):
    """Role selection page — no form, just links to registration paths."""
    return render(request, "accounts/register.html")


@require_http_methods(["GET", "POST"])
def register_customer_view(request):
    """Customer registration form. Stores data in session, sends OTP."""
    if request.method == "POST":
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data["phone"]
            # Check if phone already registered
            if UserAccount.objects.filter(phone=phone).exists():
                form.add_error("phone", "این شماره موبایل قبلاً ثبت‌نام شده است. لطفاً وارد شوید.")
            else:
                try:
                    challenge, dev_code = OTPService.request_otp(
                        phone=phone,
                        purpose=OTPPurpose.REGISTER,
                        request_ip=_get_client_ip(request),
                        user_agent=request.META.get("HTTP_USER_AGENT", ""),
                    )
                    # Store registration data in session
                    request.session["otp_phone"] = phone
                    request.session["otp_purpose"] = OTPPurpose.REGISTER
                    request.session["reg_type"] = "customer"
                    request.session["reg_data"] = {
                        "full_name": form.cleaned_data["full_name"],
                        "phone": phone,
                        "city": form.cleaned_data.get("city", ""),
                        "relation_to_elder": form.cleaned_data.get("relation_to_elder", ""),
                    }
                    if dev_code and settings.DEBUG:
                        request.session["dev_otp"] = dev_code
                    return redirect("accounts:verify")
                except ValueError as e:
                    form.add_error(None, str(e))
    else:
        form = CustomerRegistrationForm()

    return render(request, "accounts/register_customer.html", {"form": form})


@require_http_methods(["GET", "POST"])
def register_caregiver_view(request):
    """Caregiver registration form. Stores data in session, sends OTP."""
    if request.method == "POST":
        form = CaregiverRegistrationForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data["phone"]
            if UserAccount.objects.filter(phone=phone).exists():
                form.add_error("phone", "این شماره موبایل قبلاً ثبت‌نام شده است. لطفاً وارد شوید.")
            else:
                try:
                    challenge, dev_code = OTPService.request_otp(
                        phone=phone,
                        purpose=OTPPurpose.REGISTER,
                        request_ip=_get_client_ip(request),
                        user_agent=request.META.get("HTTP_USER_AGENT", ""),
                    )
                    request.session["otp_phone"] = phone
                    request.session["otp_purpose"] = OTPPurpose.REGISTER
                    request.session["reg_type"] = "caregiver"
                    request.session["reg_data"] = {
                        "full_name": form.cleaned_data["full_name"],
                        "phone": phone,
                        "specialty": form.cleaned_data.get("specialty", ""),
                        "city": form.cleaned_data.get("city", ""),
                        "company_code": form.cleaned_data.get("company_code", ""),
                        "company_name": form.cleaned_data.get("company_name", ""),
                    }
                    if dev_code and settings.DEBUG:
                        request.session["dev_otp"] = dev_code
                    return redirect("accounts:verify")
                except ValueError as e:
                    form.add_error(None, str(e))
    else:
        form = CaregiverRegistrationForm()

    return render(request, "accounts/register_caregiver.html", {"form": form})


@require_http_methods(["GET", "POST"])
def register_company_view(request):
    """Company admin registration form. Stores data in session, sends OTP."""
    if request.method == "POST":
        form = CompanyRegistrationForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data["phone"]
            if UserAccount.objects.filter(phone=phone).exists():
                form.add_error("phone", "این شماره موبایل قبلاً ثبت‌نام شده است. لطفاً وارد شوید.")
            else:
                try:
                    challenge, dev_code = OTPService.request_otp(
                        phone=phone,
                        purpose=OTPPurpose.REGISTER,
                        request_ip=_get_client_ip(request),
                        user_agent=request.META.get("HTTP_USER_AGENT", ""),
                    )
                    request.session["otp_phone"] = phone
                    request.session["otp_purpose"] = OTPPurpose.REGISTER
                    request.session["reg_type"] = "company"
                    request.session["reg_data"] = {
                        "admin_name": form.cleaned_data["admin_name"],
                        "phone": phone,
                        "admin_role": form.cleaned_data.get("admin_role", ""),
                        "company_name": form.cleaned_data["company_name"],
                        "company_type": form.cleaned_data.get("company_type", ""),
                        "city": form.cleaned_data.get("city", ""),
                        "team_size": form.cleaned_data.get("team_size", ""),
                    }
                    if dev_code and settings.DEBUG:
                        request.session["dev_otp"] = dev_code
                    return redirect("accounts:verify")
                except ValueError as e:
                    form.add_error(None, str(e))
    else:
        form = CompanyRegistrationForm()

    return render(request, "accounts/register_company.html", {"form": form})


@require_http_methods(["GET", "POST"])
def verify_view(request):
    """OTP verification. On success: login (existing) or create account (register)."""
    phone = request.session.get("otp_phone")
    purpose = request.session.get("otp_purpose")

    if not phone or not purpose:
        return redirect("accounts:login")

    dev_otp = request.session.get("dev_otp") if settings.DEBUG else None

    if request.method == "POST":
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"]
            if OTPService.verify_otp(phone=phone, code=code, purpose=purpose):
                # OTP verified successfully
                if purpose == OTPPurpose.LOGIN:
                    user = _handle_login(request, phone)
                    if user:
                        return redirect("accounts:success")
                    else:
                        form.add_error(None, "حساب کاربری با این شماره یافت نشد. لطفاً ابتدا ثبت‌نام کنید.")
                elif purpose == OTPPurpose.REGISTER:
                    redirect_url = _handle_registration(request)
                    return redirect(redirect_url)
            else:
                form.add_error("code", "کد تأیید نادرست یا منقضی شده است.")
    else:
        form = OTPVerifyForm()

    return render(request, "accounts/verify.html", {
        "form": form,
        "phone": phone,
        "dev_otp": dev_otp,
    })


def _handle_login(request, phone):
    """Login an existing user by phone after OTP verification."""
    user = UserAccount.objects.filter(phone=phone, is_active=True).first()
    if user:
        auth_login(request, user, backend=AUTHENTICATION_BACKEND)
        _clear_otp_session(request)
        logger.info("Login success: %s", phone)
        return user
    return None


def _handle_registration(request):
    """Create account from session data after OTP verification."""
    reg_type = request.session.get("reg_type")
    reg_data = request.session.get("reg_data", {})

    if reg_type == "customer":
        user, profile = RegistrationService.create_customer(**reg_data)
        auth_login(request, user, backend=AUTHENTICATION_BACKEND)
        _clear_otp_session(request)
        return "accounts:success"

    elif reg_type == "caregiver":
        user, profile, affiliation = RegistrationService.create_caregiver(**reg_data)
        auth_login(request, user, backend=AUTHENTICATION_BACKEND)
        _clear_otp_session(request)
        if affiliation:
            return "accounts:pending"
        return "accounts:success"

    elif reg_type == "company":
        user, org = RegistrationService.create_company_admin(
            phone=reg_data["phone"],
            admin_name=reg_data["admin_name"],
            admin_role_title=reg_data.get("admin_role", ""),
            company_name=reg_data["company_name"],
            company_type=reg_data.get("company_type", ""),
            city=reg_data.get("city", ""),
            team_size=reg_data.get("team_size", ""),
        )
        auth_login(request, user, backend=AUTHENTICATION_BACKEND)
        _clear_otp_session(request)
        return "accounts:success"

    # Fallback
    _clear_otp_session(request)
    return "accounts:login"


def _clear_otp_session(request):
    """Remove OTP-related session data."""
    for key in ("otp_phone", "otp_purpose", "reg_type", "reg_data", "dev_otp"):
        request.session.pop(key, None)


@require_http_methods(["GET"])
def success_view(request):
    """Registration/login success page."""
    return render(request, "accounts/success.html")


@require_http_methods(["GET"])
def pending_view(request):
    """Affiliation pending approval page."""
    return render(request, "accounts/pending.html")


@require_http_methods(["GET"])
def logout_view(request):
    """Logout the user and redirect to home."""
    from django.contrib.auth import logout as auth_logout
    auth_logout(request)
    return redirect("/")
