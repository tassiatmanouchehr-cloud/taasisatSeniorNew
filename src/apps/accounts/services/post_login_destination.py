"""
Post-login destination resolution.

Resolves an authenticated UserAccount to the real portal route they
should land on right after OTP verification, replacing the previous
unconditional redirect to accounts:success (a page that claimed "the
user portal will be activated in later stages" — no longer true now
that the customer, provider, and organization portals all exist).

Deliberately read-only: existence/status checks only, never creates or
mutates anything. This resolver only decides *where* to send the
browser — the destination view itself remains the sole place that
resolves the caller's own supplier/organization/profile identity for
actual portal access (apps.provider_portal.permissions.resolve_supplier(),
apps.organization_portal.permissions.resolve_organization(), etc.), so
no permission or ownership logic is duplicated here, and nothing here
can grant access a portal view wouldn't already grant on its own.

Priority (highest to lowest) for an account that qualifies for more
than one destination:

    1. Active organization administrator -> /organization/
    2. Provider, independent or organization-affiliated -> /provider/
    3. Customer -> /portal/
    4. Platform staff/superuser with no marketplace profile -> /admin/
    5. No resolvable role/profile -> None (caller falls back to
       accounts:success)

Rationale: organization-admin and provider are both "work" roles someone
is actively logging in to perform (managing a team, attending to
assignments/earnings), so they take priority over the customer role,
this platform's default/most common participation type. Platform staff
is checked last among resolvable destinations because is_staff/
is_superuser is an orthogonal system capability, not a marketplace
participation role — an account that also holds a real marketplace
profile is assumed to be logging in for that, not to reach Django admin.
Django's own built-in admin site is used (gated by Django's own is_staff
check, not any RBAC key here) rather than /admin-portal/, which requires
a separate RBAC permission this resolver must not evaluate on the
portal's behalf.
"""

from django.urls import reverse

from .organization_identity import list_administered_organizations


def resolve_post_login_destination(user) -> str | None:
    """Returns the URL path to redirect an authenticated user to, or None
    if no supported role/profile could be resolved (caller should fall
    back to the neutral accounts:success page)."""
    if _is_active_organization_admin(user):
        return reverse("organization_portal:dashboard")
    if _has_provider_profile(user):
        return reverse("provider_portal:dashboard")
    if _has_customer_profile(user):
        return reverse("portal:dashboard")
    if user.is_staff or user.is_superuser:
        return reverse("admin:index")
    return None


def _is_active_organization_admin(user) -> bool:
    """Tenant- and status-scoped by construction: list_administered_
    organizations() only ever returns organizations where this exact
    user holds an ACTIVE, ADMIN-role OrganizationMembership — a
    suspended membership, or another tenant's membership, can never
    satisfy this."""
    return list_administered_organizations(user).exists()


def _has_provider_profile(user) -> bool:
    """Existence-only, matching apps.provider_portal's own access policy:
    apps.accounts.services.provider_identity.resolve_supplier_for_user
    likewise never gates on CaregiverProfile.status. This resolver does
    not invent a stricter policy than the portal itself enforces."""
    return getattr(user, "caregiver_profile", None) is not None


def _has_customer_profile(user) -> bool:
    """Existence-only, matching apps.portal's own access policy (which
    also never gates on CustomerProfile.status)."""
    return getattr(user, "customer_profile", None) is not None
