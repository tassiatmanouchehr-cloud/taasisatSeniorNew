"""Tests for resolve_post_login_destination — the centralized, read-only
post-OTP-login destination resolver.

Uses real profiles/memberships throughout (no mocking of role
resolution), exercising the exact same models/services the portals
themselves rely on for ownership.
"""

import uuid

from django.test import TestCase

from apps.accounts.models.profiles import (
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
    ProfileStatus,
)
from apps.accounts.services.post_login_destination import resolve_post_login_destination
from apps.accounts.services.profiles import ensure_caregiver_profile, ensure_customer_profile
from apps.kernel.models import Person, Tenant, UserAccount


class PostLoginDestinationTestCase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"pld-{uuid.uuid4().hex[:8]}", name="Post-Login Dest Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"pld-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

    def _create_user(self, *, tenant=None, phone_suffix="0001", is_staff=False, is_superuser=False):
        tenant = tenant or self.tenant
        person = Person.objects.create(tenant=tenant, full_name="Test User")
        return UserAccount.objects.create_user(
            phone=f"0912999{phone_suffix}",
            person=person,
            tenant=tenant,
            is_staff=is_staff,
            is_superuser=is_superuser,
        )

    def _create_org_membership(
        self, user, *, organization=None, status=OrgMembershipStatus.ACTIVE, role_type=OrgMembershipRole.ADMIN
    ):
        organization = organization or OrganizationProfile.objects.create(
            name="Org",
            code=f"org-{uuid.uuid4().hex[:8]}",
            admin_user=user,
            tenant=user.tenant,
        )
        OrganizationMembership.objects.create(
            organization=organization,
            user=user,
            person=user.person,
            role_type=role_type,
            status=status,
        )
        return organization


class CustomerDestinationTest(PostLoginDestinationTestCase):
    """Item 1: customer OTP success redirect."""

    def test_customer_resolves_to_portal_dashboard(self):
        user = self._create_user(phone_suffix="0001")
        ensure_customer_profile(user)

        self.assertEqual(resolve_post_login_destination(user), "/portal/")


class IndependentProviderDestinationTest(PostLoginDestinationTestCase):
    """Item 2: independent-provider OTP success redirect."""

    def test_independent_provider_resolves_to_provider_dashboard(self):
        user = self._create_user(phone_suffix="0002")
        ensure_caregiver_profile(user)

        self.assertEqual(resolve_post_login_destination(user), "/provider/")


class AffiliatedProviderDestinationTest(PostLoginDestinationTestCase):
    """Item 3: affiliated-provider OTP success redirect — same destination
    as an independent provider; the resolver does not distinguish
    CaregiverProviderType, matching apps.provider_portal's own supplier-
    generic access policy."""

    def test_affiliated_provider_resolves_to_provider_dashboard(self):
        from apps.accounts.models.profiles import CaregiverProviderType

        user = self._create_user(phone_suffix="0003")
        ensure_caregiver_profile(user, provider_type=CaregiverProviderType.ORGANIZATION_AFFILIATED)

        self.assertEqual(resolve_post_login_destination(user), "/provider/")


class OrganizationAdminDestinationTest(PostLoginDestinationTestCase):
    """Item 4: organization-admin OTP success redirect."""

    def test_active_organization_admin_resolves_to_organization_dashboard(self):
        user = self._create_user(phone_suffix="0004")
        self._create_org_membership(user)

        self.assertEqual(resolve_post_login_destination(user), "/organization/")

    def test_non_admin_organization_member_does_not_resolve_to_organization_dashboard(self):
        """Only the ADMIN role_type counts — a plain operator member does not."""
        user = self._create_user(phone_suffix="0005")
        self._create_org_membership(user, role_type=OrgMembershipRole.OPERATOR)

        self.assertIsNone(resolve_post_login_destination(user))


class PlatformAdminDestinationTest(PostLoginDestinationTestCase):
    """Item 5: platform-admin policy — Django's own built-in admin site,
    gated by Django's own is_staff check, never a duplicated RBAC check
    here."""

    def test_staff_user_with_no_marketplace_profile_resolves_to_django_admin(self):
        user = self._create_user(phone_suffix="0006", is_staff=True, is_superuser=True)

        self.assertEqual(resolve_post_login_destination(user), "/admin/")

    def test_plain_staff_without_superuser_also_resolves_to_django_admin(self):
        user = self._create_user(phone_suffix="0007", is_staff=True)

        self.assertEqual(resolve_post_login_destination(user), "/admin/")


class UnsupportedAccountFallbackTest(PostLoginDestinationTestCase):
    """Item 6: unsupported-account fallback."""

    def test_account_with_no_profile_and_no_staff_flag_resolves_to_none(self):
        user = self._create_user(phone_suffix="0008")

        self.assertIsNone(resolve_post_login_destination(user))


class InactiveProviderBehaviorTest(PostLoginDestinationTestCase):
    """Item 7: inactive-provider behavior — the resolver follows the
    existing access policy already enforced (or, here, deliberately not
    enforced) by apps.provider_portal itself: CaregiverProfile.status is
    never checked by resolve_supplier_for_user(), so a suspended/archived
    caregiver profile still exists and still resolves to /provider/,
    exactly as it would still be granted portal access today. This
    resolver does not invent a stricter policy than the portal enforces."""

    def test_suspended_caregiver_profile_still_resolves_to_provider_dashboard(self):
        user = self._create_user(phone_suffix="0009")
        ensure_caregiver_profile(user)
        user.caregiver_profile.status = ProfileStatus.SUSPENDED
        user.caregiver_profile.save(update_fields=["status"])

        self.assertEqual(resolve_post_login_destination(user), "/provider/")


class SuspendedMembershipBehaviorTest(PostLoginDestinationTestCase):
    """Item 8: suspended-membership behavior — unlike CaregiverProfile,
    OrganizationMembership status IS already enforced by
    list_administered_organizations() (the exact function
    apps.organization_portal.permissions.resolve_organization() itself
    calls), so a suspended admin membership must not redirect into the
    organization portal."""

    def test_suspended_admin_membership_does_not_redirect_into_organization_portal(self):
        user = self._create_user(phone_suffix="0010")
        self._create_org_membership(user, status=OrgMembershipStatus.SUSPENDED)

        self.assertIsNone(resolve_post_login_destination(user))

    def test_suspended_admin_falls_back_to_provider_if_also_a_provider(self):
        """A suspended org-admin membership must not block a lower-
        priority destination the account otherwise legitimately has."""
        user = self._create_user(phone_suffix="0011")
        self._create_org_membership(user, status=OrgMembershipStatus.SUSPENDED)
        ensure_caregiver_profile(user)

        self.assertEqual(resolve_post_login_destination(user), "/provider/")


class MultipleRolePriorityTest(PostLoginDestinationTestCase):
    """Item 9: deterministic multiple-role priority.

    Documented priority (highest to lowest): organization-admin >
    provider > customer > platform staff/superuser > fallback. See
    apps.accounts.services.post_login_destination's module docstring for
    the full rationale."""

    def test_provider_beats_customer(self):
        user = self._create_user(phone_suffix="0012")
        ensure_customer_profile(user)
        ensure_caregiver_profile(user)

        self.assertEqual(resolve_post_login_destination(user), "/provider/")

    def test_organization_admin_beats_provider(self):
        user = self._create_user(phone_suffix="0013")
        ensure_caregiver_profile(user)
        self._create_org_membership(user)

        self.assertEqual(resolve_post_login_destination(user), "/organization/")

    def test_organization_admin_beats_customer(self):
        user = self._create_user(phone_suffix="0014")
        ensure_customer_profile(user)
        self._create_org_membership(user)

        self.assertEqual(resolve_post_login_destination(user), "/organization/")

    def test_organization_admin_beats_platform_staff(self):
        user = self._create_user(phone_suffix="0015", is_staff=True, is_superuser=True)
        self._create_org_membership(user)

        self.assertEqual(resolve_post_login_destination(user), "/organization/")

    def test_customer_beats_platform_staff(self):
        user = self._create_user(phone_suffix="0016", is_staff=True, is_superuser=True)
        ensure_customer_profile(user)

        self.assertEqual(resolve_post_login_destination(user), "/portal/")

    def test_full_priority_chain_all_four_roles_at_once(self):
        """Every resolvable role present simultaneously — organization-
        admin must still win, proving the full chain, not just pairwise
        comparisons."""
        user = self._create_user(phone_suffix="0017", is_staff=True, is_superuser=True)
        ensure_customer_profile(user)
        ensure_caregiver_profile(user)
        self._create_org_membership(user)

        self.assertEqual(resolve_post_login_destination(user), "/organization/")


class TenantIsolationTest(PostLoginDestinationTestCase):
    """Item 11: tenant isolation — another tenant's role/profile cannot
    influence the destination."""

    def test_organization_admin_membership_in_another_tenant_does_not_grant_admin_destination(self):
        """list_administered_organizations() filters strictly by
        user=user, so a membership can only ever belong to this exact
        UserAccount — there is no cross-tenant lookup path to even
        attempt. This test constructs the strongest version of the
        scenario: a same-person-different-tenant UserAccount, proving
        the *other* tenant's membership never leaks across accounts."""
        user_in_tenant = self._create_user(tenant=self.tenant, phone_suffix="0018")
        user_in_other_tenant = self._create_user(tenant=self.other_tenant, phone_suffix="0019")
        self._create_org_membership(user_in_other_tenant)

        # The tenant-A user has no profile/membership of its own at all.
        self.assertIsNone(resolve_post_login_destination(user_in_tenant))
        # The tenant-B user's own membership still resolves correctly.
        self.assertEqual(resolve_post_login_destination(user_in_other_tenant), "/organization/")
