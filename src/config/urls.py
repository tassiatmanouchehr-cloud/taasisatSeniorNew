"""URL configuration for the Enterprise Service Marketplace Platform."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

# FR-018: distinguishes an anonymous visitor (redirected to login) from an
# authenticated-but-unauthorized one (branded 403) — see
# apps.kernel.views.forbidden's own module docstring for the full
# rationale. No permission-check logic changed, only how the resulting
# PermissionDenied is rendered.
handler403 = "apps.kernel.views.forbidden"

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

if settings.DEBUG:
    # Only MEDIA_ROOT/public (avatars/covers) is ever registered here —
    # verification documents live under MEDIA_ROOT/private and are never
    # reachable via a raw static path, in dev or production; see
    # apps.accounts.models.media_paths's module docstring. In production,
    # MEDIA_ROOT/public would instead be served by a real web
    # server/CDN in front of Django, same split.
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL + "public/", document_root=str(settings.MEDIA_ROOT / "public"))
