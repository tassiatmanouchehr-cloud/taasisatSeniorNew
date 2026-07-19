"""Canonical public-site tenant resolution.

Every apps.public_site view (and public_tenant_context, the context
processor that exposes the same result to shared navigation chrome) that
needs "which tenant does an anonymous visitor see" resolves it through
resolve_public_tenant() here — replacing what used to be a private,
per-view _resolve_optional_tenant_hint() in views.py that only the four
directory/detail views called (never the homepage), and that only ever
fell back to the platform default tenant, with no way for a deployment
to serve a different tenant as its public site.

Resolution order (most specific wins):

1. An explicit ?tenant=<slug> query hint — a caller-known, already-
   validated slug (e.g. a demo/preview link). Unknown/invalid slugs
   404 immediately; never silently substituted. Unchanged from the
   pre-existing _resolve_optional_tenant_hint() behavior (FR-015).

2. settings.PUBLIC_SITE_TENANT_SLUG — an explicit deployment/
   environment configuration value (see .env.example), never a
   hard-coded literal in source. Unset for the ordinary single-tenant
   deployment (every existing test and the shipped settings modules
   leave this unset), in which case resolution falls through to (3)
   unchanged. If set to a slug that does NOT resolve to a real tenant,
   resolution fails loudly (ImproperlyConfigured) rather than silently
   falling back to (4) — a deployer who mistypes this setting must see
   a clear, immediate error, not a public site that quietly serves the
   wrong tenant's data with no indication anything is wrong.

3. FR-019 corrective review: settings.DEBUG-only, best-effort lookup of
   apps.kernel.dev_tenant.CANONICAL_DEV_TENANT_SLUG — the exact same
   literal slug apps.kernel.management.commands.seed_product_walkthrough
   seeds its realistic demo dataset into (imported from that one shared
   module by both sides, so the two can never silently drift apart).
   This exists solely so a genuinely clean local-development workflow —
   clone, migrate, `seed_product_walkthrough`, `runserver`, open
   `/find-a-caregiver/` — shows real caregivers with zero `?tenant=`
   query parameter and zero manual `.env` edit, without weakening
   anything: it is gated on settings.DEBUG (hardcoded False in
   config.settings.production and config.settings.testing — this branch
   is therefore structurally unreachable outside local development,
   exactly like seed_product_walkthrough's own "refuses to run when
   DEBUG is False" guard), it looks up one specific, known, named slug
   (never "the first active tenant" or any other heuristic), and if no
   tenant with that exact slug exists yet (the ordinary case for every
   test database and every deployment that hasn't run the walkthrough
   seed) it silently, harmlessly falls through to (4) — never raises,
   unlike case 2's deliberately-loud failure for a *human-configured*
   value that turns out to be wrong.

4. TenantService.get_default_tenant() — the platform's single default
   tenant. Unchanged, pre-existing fallback every deployment already
   relies on when nothing above resolved.

tenant_slug (the second element of the returned tuple) is the empty
string only for case 4 — matching every pre-existing test/behavior for
the ordinary default-tenant path (no ?tenant= ever appears in a
generated link). It is non-empty for cases 1, 2, and 3 so every
generated link/nav element carries the *resolved* tenant forward via
common.append_tenant_query(), exactly like the already-established
explicit-hint mechanism (FR-015/FR-016) — this is what actually keeps
navigation working when case 2 or case 3 resolves to a non-default
tenant, not merely resolving the tenant for the current page.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404

from apps.kernel.dev_tenant import CANONICAL_DEV_TENANT_SLUG
from apps.kernel.services.tenant_service import TenantService


def resolve_public_tenant(request) -> tuple[uuid.UUID, str]:
    """Returns (tenant_id, tenant_slug) per the module docstring's
    resolution order.

    Raises Http404 for an explicit, unknown ?tenant= slug (case 1) —
    unchanged FR-015 behavior, since an anonymous visitor's own typo/bad
    link is an ordinary "not found," not a deployment problem.

    Raises ImproperlyConfigured if settings.PUBLIC_SITE_TENANT_SLUG is
    set but does not resolve to a real tenant (case 2) — this is always
    a deployment/configuration defect, never something an ordinary
    visitor did, so it must not be swallowed into a silent fallback.

    Case 3 (DEBUG-only canonical dev tenant) never raises — a missing
    dev tenant is the ordinary, expected state before
    seed_product_walkthrough has run, not a configuration error.

    Case 4 (nothing resolved above) never raises — every deployment
    that leaves PUBLIC_SITE_TENANT_SLUG unset and has no dev tenant
    seeded gets exactly the pre-existing, unconditional default-tenant
    behavior."""
    hinted_slug = request.GET.get("tenant") or None
    if hinted_slug:
        tenant = TenantService.get_tenant_by_slug(hinted_slug)
        if tenant is None:
            raise Http404("Unknown tenant.")
        return tenant.id, hinted_slug

    configured_slug = getattr(settings, "PUBLIC_SITE_TENANT_SLUG", None)
    if configured_slug:
        tenant = TenantService.get_tenant_by_slug(configured_slug)
        if tenant is None:
            raise ImproperlyConfigured(
                f"settings.PUBLIC_SITE_TENANT_SLUG={configured_slug!r} does not match any existing "
                "Tenant. Fix the PUBLIC_SITE_TENANT_SLUG environment variable (see .env.example), or "
                "unset it entirely to use the platform default tenant."
            )
        return tenant.id, configured_slug

    if settings.DEBUG:
        dev_tenant = TenantService.get_tenant_by_slug(CANONICAL_DEV_TENANT_SLUG)
        if dev_tenant is not None:
            return dev_tenant.id, CANONICAL_DEV_TENANT_SLUG

    return TenantService.get_default_tenant_id(), ""
