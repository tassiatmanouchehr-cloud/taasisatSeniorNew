"""Template context processors for apps.public_site.

Registered globally in TEMPLATES['OPTIONS']['context_processors'], but
scoped internally to public_site's own routes only (via
request.resolver_match.namespace) — zero cost, zero tenant resolution,
for every other app's page (portal, admin, api, ...).
"""

from .services.tenant_context import resolve_public_tenant


def public_tenant_context(request) -> dict:
    """Exposes `public_tenant_slug` — the same tenant context
    resolve_public_tenant() gives each public_site view — to every
    public template, so base_public.html's shared navigation chrome
    (desktop nav, mobile nav, footer) can carry the resolved tenant
    forward on every link, exactly like the FR-016 directory-generated
    links already do, without every single public view (including the
    many content-only pages: /about/, /services/, /faq/, ...) having to
    resolve and pass it through by hand.

    An unknown explicit ?tenant= slug or a misconfigured
    settings.PUBLIC_SITE_TENANT_SLUG raises here exactly as it would in
    the view itself (Http404 / ImproperlyConfigured) — if the view
    already executed successfully, this call is idempotent and resolves
    identically, so it never surfaces a *new* failure the view itself
    wouldn't already have raised first."""
    match = request.resolver_match
    if match is None or match.namespace != "public_site":
        return {}
    _tenant_id, tenant_slug = resolve_public_tenant(request)
    return {"public_tenant_slug": tenant_slug}
