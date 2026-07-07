"""URL configuration for the Enterprise Service Marketplace Platform."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.kernel.api.urls", namespace="kernel-api")),
    path("ui/", include("apps.showcase.urls", namespace="showcase")),
]
