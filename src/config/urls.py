"""URL configuration for the Enterprise Service Marketplace Platform."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("apps.public_site.urls", namespace="public_site")),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("admin/", admin.site.urls),
    path("admin-portal/", include("apps.admin_portal.urls", namespace="admin_portal")),
    path("api/v1/", include("apps.api.urls", namespace="api-v1")),
    path("organization/", include("apps.organization_portal.urls", namespace="organization_portal")),
    path("portal/", include("apps.portal.urls", namespace="portal")),
    path("provider/", include("apps.provider_portal.urls", namespace="provider_portal")),
    path("ui/", include("apps.showcase.urls", namespace="showcase")),
]
