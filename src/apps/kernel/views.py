"""Global HTTP error handlers — platform-wide, not tied to any one app.

FR-018 (Public Site Coherence Remediation, PSA-005): every browser-facing
portal (apps.portal/provider_portal/organization_portal/admin_portal)
enforces access with its own require_authenticated()-style helper, all of
which raise django.core.exceptions.PermissionDenied on failure —
previously converted, uniformly, into Django's raw/unbranded default 403
page.

Before changing this, this module's own docstring investigated whether
an anonymous visitor should instead be redirected to log in (the
audit's first suggestion). Running the existing suite surfaced the real
answer: every one of these four portals already has its own explicit,
redundant "anonymous access is denied — 403, not a redirect" test
(apps.portal.tests.test_access_control.UnauthenticatedAccessTest,
apps.provider_portal's and apps.organization_portal's identically-named
siblings, apps.admin_portal.tests.test_views
.AdminPortalAccessControlTest, plus several more per-view variants) —
15 tests total, across 4 separate apps, all asserting status_code == 403
for an anonymous GET. That is exactly "an established security policy
[that] explicitly requires non-disclosure" (PSA-005's own stated
exception to the login-redirect default): these portals are internal
operational tools, not consumer-facing pages a visitor "should" be
nudged to log into, and a redirect would itself disclose "this route
exists and requires login" to an anonymous prober. So this module makes
only the change PSA-005 actually root-caused as broken — Django's raw,
unbranded 403 page — replacing it with a clear, branded, Persian one for
every browser-facing PermissionDenied, whether the caller is anonymous
or logged in as the wrong role. No permission-check function anywhere
was touched, no status code changed, and no existing test needed to
change. Registered as the project's handler403 in config/urls.py.
"""

from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils.http import url_has_allowed_host_and_scheme

#: Path prefixes that keep Django's plain 403 response untouched. REST
#: clients (apps.api) already raise their own ApiError with a JSON body
#: and the correct 401/403 status before this handler is ever reached —
#: this prefix check is a defense-in-depth fallback only, in case some
#: unexpected code path under /api/ ever raises PermissionDenied directly.
_API_PATH_PREFIX = "/api/"


def _safe_next_path(request) -> str:
    """Open-redirect guard for a same-origin "return to this page"
    value: Django's own url_has_allowed_host_and_scheme(), not a
    hand-rolled check. Not currently wired into any live redirect (see
    this module's docstring — this codebase's established policy is
    non-disclosing 403s, not login redirects, for every route audited
    under PSA-005), kept here — tested in isolation — as the vetted
    building block any future login-redirect flow on this project
    should reuse rather than re-implement."""
    candidate = request.get_full_path()
    if url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return "/"


def forbidden(request, exception=None):
    """handler403: every browser-facing PermissionDenied (anonymous or
    authenticated-wrong-role alike — this codebase's established policy,
    confirmed against its own test suite, does not distinguish the two)
    gets one branded, Persian, non-disclosing 403 page instead of
    Django's raw default. /api/ requests are left untouched (ApiError
    already governs their real 401/403 shape before this handler is ever
    reached; this is a defense-in-depth fallback only). Never discloses
    *why* access was denied (no role/permission name, no confirmation
    the target resource exists)."""
    if request.path.startswith(_API_PATH_PREFIX):
        return HttpResponseForbidden("Forbidden")

    return render(request, "errors/403.html", status=403)
