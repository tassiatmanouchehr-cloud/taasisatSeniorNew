"""URL configuration for the Enterprise Service Marketplace Platform."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("apps.public_site.urls", namespace="public_site")),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("admin/", admin.site.urls),
    path("admin-portal/", include("apps.admin_portal.urls", namespace="admin_portal")),
    path("api/v1/", include("apps.api.urls", namespace="api-v1")),
    path("portal/", include("apps.portal.urls", namespace="portal")),
    path("ui/", include("apps.showcase.urls", namespace="showcase")),
]
