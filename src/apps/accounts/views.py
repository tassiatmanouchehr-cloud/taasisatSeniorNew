"""Authentication and onboarding views.

UI-only — no backend logic, no database models, no actual authentication.
These views render templates for the onboarding flow architecture.
Backend implementation will be added in a future sprint.
"""

from django.shortcuts import render


def login_view(request):
    """Phone + OTP login page."""
    return render(request, "accounts/login.html")


def register_view(request):
    """Role selection: Customer vs Caregiver vs Company Admin."""
    return render(request, "accounts/register.html")


def register_customer_view(request):
    """Customer (family/patient) registration form."""
    return render(request, "accounts/register_customer.html")


def register_caregiver_view(request):
    """Caregiver/provider registration with optional company affiliation."""
    return render(request, "accounts/register_caregiver.html")


def register_company_view(request):
    """Company/organization admin registration."""
    return render(request, "accounts/register_company.html")


def verify_view(request):
    """OTP verification page."""
    return render(request, "accounts/verify.html")


def success_view(request):
    """Registration success page."""
    return render(request, "accounts/success.html")


def pending_view(request):
    """Affiliation pending approval page."""
    return render(request, "accounts/pending.html")
