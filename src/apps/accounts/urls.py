"""URL configuration for authentication and onboarding."""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("register/customer/", views.register_customer_view, name="register-customer"),
    path("register/caregiver/", views.register_caregiver_view, name="register-caregiver"),
    path("register/company/", views.register_company_view, name="register-company"),
    path("verify/", views.verify_view, name="verify"),
    path("success/", views.success_view, name="success"),
    path("pending/", views.pending_view, name="pending"),
    path("logout/", views.logout_view, name="logout"),
]
