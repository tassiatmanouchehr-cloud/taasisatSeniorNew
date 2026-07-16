"""
Customer auth-resolution helpers for public_site — Phase 4 Sprint 4.1
(Customer Favorites and Saved Providers).

apps.public_site's pages have never before been auth-aware — every page
is anonymous-safe by design. This sprint adds the *first* narrow,
authenticated surface (the favorite toggle) without turning public_site
into a general-purpose authenticated app. Deliberately NOT importing
apps.portal.permissions: that module's resolve_customer_profile() raises
PermissionDenied on any resolution failure, which is exactly right for
apps.portal (every page there requires authentication) but wrong for a
public profile page's read-only "is this favorited" check, which must
degrade to False/no-button rather than 500 a public page. The two
functions below intentionally mirror apps.portal.permissions's own
resolution logic (read request.user.person.customer_profile /
request.user.tenant_id, never accept either from the request body/URL)
but differ in failure mode, matching each call site's own requirement:

- resolve_customer_or_none(): fails closed silently — for the read-only
  is_favorited flag on GET profile pages. An authenticated caregiver or
  organization staff member browsing their own public listing (who has
  no CustomerProfile) must see a normal page, never a 500.
- require_customer(): fails loud (PermissionDenied -> 403), for the
  mutating toggle views, matching the exact 403 convention every other
  authenticated mutation in this codebase already uses
  (apps.portal.permissions.require_authenticated()).
"""

from django.core.exceptions import PermissionDenied


def resolve_customer_or_none(request):
    """Returns the request's own CustomerProfile, or None on any
    resolution failure (anonymous, no Person, no CustomerProfile) —
    never raises."""
    if not getattr(request.user, "is_authenticated", False):
        return None
    person = getattr(request.user, "person", None)
    if person is None:
        return None
    return getattr(person, "customer_profile", None)


def require_customer(request):
    """Returns (customer, tenant_id) for the authenticated caller, or
    raises PermissionDenied (-> 403) — for mutating views only. Never
    accepts a customer/tenant identifier from the request itself."""
    if not getattr(request.user, "is_authenticated", False):
        raise PermissionDenied("Authentication is required to manage favorites.")
    customer = resolve_customer_or_none(request)
    if customer is None:
        raise PermissionDenied("The authenticated account has no associated customer profile.")
    tenant_id = getattr(request.user, "tenant_id", None)
    if not tenant_id:
        raise PermissionDenied("The authenticated account has no tenant context.")
    return customer, tenant_id
