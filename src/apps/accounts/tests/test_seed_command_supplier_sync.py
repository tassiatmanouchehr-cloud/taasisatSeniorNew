"""
Core Profile-ServiceSupplier Invariant Remediation — committed regression
coverage for the seed-command fix (independent pre-merge review of
PR #18, Required Fix 8).

`seed_demo_accounts`/`seed_demo_people` originally created ACTIVE-by-
default `CaregiverProfile`/`OrganizationProfile` rows with zero
`ServiceSupplier` sync — the exact bug class the live "empty public
directory" report traced to. That was fixed by calling the sanctioned
bridge right after creation, but the fix previously had no committed
regression test — only a one-time, ad-hoc manual verification during
implementation. This module is that missing coverage.
"""

from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models.profiles import CaregiverProfile, OrganizationProfile, ProfileStatus
from apps.accounts.services.supplier_bridge import CAREGIVER_LINKED_TYPE, ORGANIZATION_LINKED_TYPE
from apps.kernel.models import Person, UserAccount
from apps.kernel.models.supplier import ServiceSupplier, SupplierStatus, SupplierType
from apps.kernel.services.tenant_service import TenantService
from apps.orders.models import CatalogStatus, ServiceCategory


class SeedDemoAccountsSupplierSyncTest(TestCase):
    def test_active_organization_gets_an_active_supplier(self):
        call_command("seed_demo_accounts")

        tenant = TenantService.get_default_tenant()
        organization = OrganizationProfile.objects.get(code="DEMO-COMPANY")
        self.assertEqual(organization.status, ProfileStatus.ACTIVE)

        supplier = ServiceSupplier.objects.get(
            linked_entity_id=organization.id, linked_entity_type=ORGANIZATION_LINKED_TYPE,
        )
        self.assertEqual(supplier.status, SupplierStatus.ACTIVE)
        self.assertEqual(supplier.supplier_type, SupplierType.ORGANIZATION)
        self.assertEqual(supplier.tenant_id, tenant.id)

    def test_draft_caregiver_profiles_get_no_supplier(self):
        """ensure_caregiver_profile() still correctly defaults to DRAFT —
        this seed command must not have accidentally started activating
        caregivers as a side effect of adding the organization's
        supplier sync."""
        call_command("seed_demo_accounts")

        independent_nurse = UserAccount.objects.get(email="nurse.independent@salmandyar.local")
        caregiver = CaregiverProfile.objects.get(user=independent_nurse)
        self.assertEqual(caregiver.status, ProfileStatus.DRAFT)
        self.assertFalse(
            ServiceSupplier.objects.filter(
                linked_entity_id=caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
            ).exists(),
        )

    def test_double_run_creates_no_duplicate_profiles_or_suppliers(self):
        call_command("seed_demo_accounts")
        organization = OrganizationProfile.objects.get(code="DEMO-COMPANY")
        profile_count_1 = OrganizationProfile.objects.count()
        user_count_1 = UserAccount.objects.count()
        supplier_count_1 = ServiceSupplier.objects.filter(
            linked_entity_id=organization.id, linked_entity_type=ORGANIZATION_LINKED_TYPE,
        ).count()

        call_command("seed_demo_accounts")

        self.assertEqual(OrganizationProfile.objects.count(), profile_count_1)
        self.assertEqual(UserAccount.objects.count(), user_count_1)
        self.assertEqual(
            ServiceSupplier.objects.filter(
                linked_entity_id=organization.id, linked_entity_type=ORGANIZATION_LINKED_TYPE,
            ).count(),
            supplier_count_1,
        )
        self.assertEqual(supplier_count_1, 1)

    def test_double_run_supplier_row_is_stable_not_recreated(self):
        call_command("seed_demo_accounts")
        organization = OrganizationProfile.objects.get(code="DEMO-COMPANY")
        supplier_id_1 = ServiceSupplier.objects.get(
            linked_entity_id=organization.id, linked_entity_type=ORGANIZATION_LINKED_TYPE,
        ).id

        call_command("seed_demo_accounts")

        supplier_id_2 = ServiceSupplier.objects.get(
            linked_entity_id=organization.id, linked_entity_type=ORGANIZATION_LINKED_TYPE,
        ).id
        self.assertEqual(supplier_id_1, supplier_id_2)


class SeedDemoPeopleSupplierSyncTest(TestCase):
    def _independent_caregiver(self) -> CaregiverProfile:
        return CaregiverProfile.objects.get(phone="09133333333")

    def _organization(self) -> OrganizationProfile:
        return OrganizationProfile.objects.get(code="DEMO-0001")

    def _affiliated_caregiver(self) -> CaregiverProfile:
        return CaregiverProfile.objects.get(phone="09155555555")

    def test_active_independent_caregiver_gets_an_active_supplier(self):
        call_command("seed_demo_people")

        tenant = TenantService.get_default_tenant()
        caregiver = self._independent_caregiver()
        self.assertEqual(caregiver.status, ProfileStatus.ACTIVE)

        supplier = ServiceSupplier.objects.get(
            linked_entity_id=caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
        )
        self.assertEqual(supplier.status, SupplierStatus.ACTIVE)
        self.assertEqual(supplier.supplier_type, SupplierType.INDEPENDENT_PROVIDER)
        self.assertEqual(supplier.tenant_id, tenant.id)

    def test_active_organization_gets_an_active_supplier(self):
        call_command("seed_demo_people")

        organization = self._organization()
        self.assertEqual(organization.status, ProfileStatus.ACTIVE)
        supplier = ServiceSupplier.objects.get(
            linked_entity_id=organization.id, linked_entity_type=ORGANIZATION_LINKED_TYPE,
        )
        self.assertEqual(supplier.status, SupplierStatus.ACTIVE)
        self.assertEqual(supplier.supplier_type, SupplierType.ORGANIZATION)

    def test_caregiver_with_pending_affiliation_gets_an_active_supplier(self):
        call_command("seed_demo_people")

        caregiver = self._affiliated_caregiver()
        self.assertEqual(caregiver.status, ProfileStatus.ACTIVE)
        self.assertTrue(
            ServiceSupplier.objects.filter(
                linked_entity_id=caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
                status=SupplierStatus.ACTIVE,
            ).exists(),
        )

    def test_double_run_creates_no_duplicate_profiles_or_suppliers(self):
        call_command("seed_demo_people")
        user_count_1 = UserAccount.objects.count()
        caregiver_count_1 = CaregiverProfile.objects.count()
        organization_count_1 = OrganizationProfile.objects.count()
        supplier_count_1 = ServiceSupplier.objects.count()

        call_command("seed_demo_people")

        self.assertEqual(UserAccount.objects.count(), user_count_1)
        self.assertEqual(CaregiverProfile.objects.count(), caregiver_count_1)
        self.assertEqual(OrganizationProfile.objects.count(), organization_count_1)
        self.assertEqual(ServiceSupplier.objects.count(), supplier_count_1)
        self.assertEqual(supplier_count_1, 3, "independent caregiver + organization + affiliated caregiver")

    def test_double_run_supplier_rows_are_stable_not_recreated(self):
        call_command("seed_demo_people")
        caregiver = self._independent_caregiver()
        supplier_id_1 = ServiceSupplier.objects.get(
            linked_entity_id=caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
        ).id

        call_command("seed_demo_people")

        supplier_id_2 = ServiceSupplier.objects.get(
            linked_entity_id=caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
        ).id
        self.assertEqual(supplier_id_1, supplier_id_2)


class SeedDemoOrdersDoesNotCreateSupplierForDraftCaregiverTest(TestCase):
    """Core Profile-ServiceSupplier Invariant Remediation — call-graph
    recheck finding (independent pre-merge review of PR #18): the
    original `CaregiverProfile.objects.first()` had no status filter and
    no guaranteed ordering, so on a database seeded with both a DRAFT and
    an ACTIVE caregiver it could non-deterministically hand the DRAFT one
    to `get_or_create_supplier_for_caregiver()`, creating a supplier for
    a profile that has never reached ACTIVE."""

    def setUp(self):
        self.tenant = TenantService.get_default_tenant()
        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug="home-care-seed-orders", status=CatalogStatus.ACTIVE,
        )

    def _create_caregiver(self, *, status, phone):
        person = Person.objects.create(tenant=self.tenant, full_name="Seed Order Caregiver")
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)
        return CaregiverProfile.objects.create(
            user=user, person=person, phone=phone, display_name="Seed Order Caregiver", status=status,
        )

    def test_draft_caregiver_created_first_gets_no_supplier(self):
        draft_caregiver = self._create_caregiver(status=ProfileStatus.DRAFT, phone="09147770001")
        active_caregiver = self._create_caregiver(status=ProfileStatus.ACTIVE, phone="09147770002")

        call_command("seed_demo_orders")

        self.assertFalse(
            ServiceSupplier.objects.filter(
                linked_entity_id=draft_caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
            ).exists(),
        )
        self.assertTrue(
            ServiceSupplier.objects.filter(
                linked_entity_id=active_caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
                status=SupplierStatus.ACTIVE,
            ).exists(),
        )
