"""URL configuration for authentication and onboarding pages.

These are UI-only views — no backend authentication logic is implemented yet.
All forms navigate via client-side JS for demo/flow purposes.
"""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # Login
    path("login/", views.login_view, name="login"),

    # Registration — role selection
    path("register/", views.register_view, name="register"),

    # Registration — per-role forms
    path("register/customer/", views.register_customer_view, name="register-customer"),
    path("register/caregiver/", views.register_caregiver_view, name="register-caregiver"),
    path("register/company/", views.register_company_view, name="register-company"),

    # OTP verification
    path("verify/", views.verify_view, name="verify"),

    # Outcome pages
    path("success/", views.success_view, name="success"),
    path("pending/", views.pending_view, name="pending"),
]
