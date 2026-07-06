"""URL configuration for the Kernel API."""

from django.urls import path

from .health import HealthCheckView

app_name = "kernel"

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
]
