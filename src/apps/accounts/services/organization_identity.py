"""
Organization admin identity resolution — Epic 02 (Marketplace Operational
Experience).

Resolves a logged-in UserAccount to the OrganizationProfile(s) they
administer, and provides an ownership-scoped single-org lookup. Mirrors
apps.portal.permissions.resolve_customer_profile's shape (resolve the
caller's own identity from the session, never accept one from the
request) rather than apps.admin_portal's RBAC/permission-key model —
an organization admin accessing their own organization's data is closer
in kind to a customer accessing their own data than to a platform
operator accessing everyone's, so ownership (an ACTIVE, ADMIN-role
OrganizationMembership) is the security boundary here, not a permission
key. See DECISION_HISTORY.md for the explicit reasoning.
"""

from .errors import AccountsError


def list_administered_organizations(user):
    """Every OrganizationProfile this user is an active admin member of."""
    from ..models.profiles import OrganizationMembership, OrgMembershipRole, OrgMembershipStatus

    membership_org_ids = OrganizationMembership.objects.filter(
        user=user, role_type=OrgMembershipRole.ADMIN, status=OrgMembershipStatus.ACTIVE,
    ).values_list("organization_id", flat=True)

    from ..models.profiles import OrganizationProfile

    return OrganizationProfile.objects.filter(id__in=membership_org_ids)


def resolve_admin_organization(user, organization_id):
    """Ownership-safe lookup: returns the OrganizationProfile only if `user`
    is an active admin member of it. Raises AccountsError otherwise — never
    distinguishes "doesn't exist" from "not yours"."""
    organization = list_administered_organizations(user).filter(id=organization_id).first()
    if organization is None:
        raise AccountsError("Organization not found.")
    return organization
