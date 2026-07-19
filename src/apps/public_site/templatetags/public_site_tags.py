"""Template filters shared across apps.public_site's server-rendered pages.

Follow-up to FR-017/FR-018: seo_meta.html needs an absolute URL for
og:url (the Open Graph spec requires one — a bare relative path like "/"
is invalid and breaks link-preview crawlers). Building it from the
current request (never a hard-coded host) keeps every environment
(local dev, any future deployment) correct without a settings change."""

from django import template

register = template.Library()


@register.filter
def absolute_url(path, request):
    """`{{ page_url|absolute_url:request }}` — resolves `path` (a
    relative or already-absolute URL) against the current request's own
    scheme+host via Django's own request.build_absolute_uri(), never a
    hard-coded domain. Returns `path` unchanged if `request` is missing
    (defensive only — every public_site template already has `request`
    in context via django.template.context_processors.request)."""
    if not request:
        return path
    return request.build_absolute_uri(path)
