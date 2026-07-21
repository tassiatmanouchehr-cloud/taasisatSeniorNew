"""Organization services — membership, lookup."""

from django.utils import timezone

from ..models.profiles import (
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipStatus,
)


def create_organization_membership(*, organization, user, person=None, role_type, invited_by=None):
    """Create an organization membership. Idempotent for same org+user+role."""
    membership, created = OrganizationMembership.objects.get_or_create(
        organization=organization,
        user=user,
        role_type=role_type,
        defaults={
            "person": person,
            "status": OrgMembershipStatus.ACTIVE,
            "invited_by": invited_by,
            "joined_at": timezone.now(),
        },
    )
    return membership, created


def find_organization_by_code_or_name(query: str):
    """Find organization by exact code match or partial name match."""
    if not query:
        return None
    # Try exact code first
    org = OrganizationProfile.objects.filter(code__iexact=query.strip()).first()
    if org:
        return org
    # Try name contains
    org = OrganizationProfile.objects.filter(name__icontains=query.strip()).first()
    return org
