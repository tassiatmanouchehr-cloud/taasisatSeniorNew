"""
Cross-organization isolation for affiliated providers — Epic 04 Sprint 3.

Proves apps.accounts.services.organization_staff.OrganizationStaffService
.resolve_staff_supplier()'s existing organization=-scoped lookup already
prevents one organization from resolving another organization's affiliated
staff to a ServiceSupplier — no new code was required for this guarantee
once ORGANIZATION_PROVIDER became reachable (see supplier_bridge's module
docstring); this test is the evidence.
"""

import uuid

from django.test import TestCase

from apps.accounts.models.profiles import (
    CaregiverProfile,
    CaregiverProviderType,
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
)
from apps.accounts.services.errors import AccountsError
from apps.accounts.services.organization_staff import OrganizationStaffService
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.supplier import SupplierType


class CrossOrganizationAffiliatedProviderTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"crossorgprov-{uuid.uuid4().hex[:8]}", name="Cross Org Provider Tenant")

        self.org_a_admin = self._create_user(phone="09140000030")
        self.org_a = OrganizationProfile.objects.create(
            name="Org A", code=f"org-a-{uuid.uuid4().hex[:6]}", admin_user=self.org_a_admin, tenant=self.tenant,
        )
        self.org_b_admin = self._create_user(phone="09140000031")
        self.org_b = OrganizationProfile.objects.create(
            name="Org B", code=f"org-b-{uuid.uuid4().hex[:6]}", admin_user=self.org_b_admin, tenant=self.tenant,
        )

        self.affiliated_user = self._create_user(phone="09140000032")
        self.affiliated_caregiver = CaregiverProfile.objects.create(
            user=self.affiliated_user, person=self.affiliated_user.person, phone="09140000032",
            display_name="Org A Staff", provider_type=CaregiverProviderType.ORGANIZATION_AFFILIATED,
        )
        self.membership = OrganizationMembership.objects.create(
            organization=self.org_a, user=self.affiliated_user,
            role_type=OrgMembershipRole.CAREGIVER, status=OrgMembershipStatus.ACTIVE,
        )

    def _create_user(self, *, phone) -> UserAccount:
        person = Person.objects.create(tenant=self.tenant, full_name="Person")
        return UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)

    def test_owning_organization_resolves_its_affiliated_staff_to_organization_provider_supplier(self):
        supplier = OrganizationStaffService.resolve_staff_supplier(organization=self.org_a, membership_id=self.membership.id)
        self.assertEqual(supplier.supplier_type, SupplierType.ORGANIZATION_PROVIDER)

    def test_other_organization_cannot_resolve_this_affiliated_staff(self):
        with self.assertRaises(AccountsError):
            OrganizationStaffService.resolve_staff_supplier(organization=self.org_b, membership_id=self.membership.id)
