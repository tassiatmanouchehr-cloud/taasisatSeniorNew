"""
Organization admin identity resolution — Epic 02 (Marketplace Operational
Experience).

Resolves a logged-in UserAccount to the OrganizationProfile(s) they
administer. Mirrors apps.portal.permissions.resolve_customer_profile's
shape (resolve the caller's own identity from the session, never accept
one from the request) rather than apps.admin_portal's RBAC/permission-key
model — an organization admin accessing their own organization's data is
closer in kind to a customer accessing their own data than to a platform
operator accessing everyone's, so ownership (an ACTIVE, ADMIN-role
OrganizationMembership) is the security boundary here, not a permission
key. See DECISION_HISTORY.md for the explicit reasoning.

The one and only ownership-resolution entry point for the organization
portal is apps.organization_portal.permissions.resolve_organization(),
which calls list_administered_organizations(request.user).first() below
— it never accepts an organization id from the request (the portal is
deliberately single-org-per-admin this phase, see that module's
docstring), so there is no id-based "resolve *this* organization if I
own it" lookup in this codebase today. Do not add one speculatively; if
multi-organization switching is built later, an id-based lookup can be
added at that point, scoped to whatever URL/session shape that feature
actually needs.
"""


def list_administered_organizations(user):
    """Every OrganizationProfile this user is an active admin member of."""
    from ..models.profiles import OrganizationMembership, OrgMembershipRole, OrgMembershipStatus

    membership_org_ids = OrganizationMembership.objects.filter(
        user=user,
        role_type=OrgMembershipRole.ADMIN,
        status=OrgMembershipStatus.ACTIVE,
    ).values_list("organization_id", flat=True)

    from ..models.profiles import OrganizationProfile

    return OrganizationProfile.objects.filter(id__in=membership_org_ids)
