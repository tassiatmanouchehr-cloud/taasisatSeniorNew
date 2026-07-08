"""
/api/v1/ routing — Module 17A foundation.

The single canonical entrypoint for all versioned API routes. Reuses the
existing (Module 05-era) HealthCheckView rather than duplicating it.
"""

from django.urls import path

from apps.kernel.api.health import HealthCheckView

from .views import OrderCountsSampleView, ProviderReportsSampleView

app_name = "api"

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("sample/order-counts/", OrderCountsSampleView.as_view(), name="sample-order-counts"),
    path("sample/providers/", ProviderReportsSampleView.as_view(), name="sample-providers"),
]
