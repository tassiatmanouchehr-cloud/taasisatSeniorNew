"""HTTP-level tests for the Epic 06 public views.

Tests run against the platform's real default tenant (TenantService
.get_default_tenant()) rather than an isolated per-test tenant, because
the views never accept a tenant_id — they always resolve it via
TenantService, exactly like every other unauthenticated view in this
codebase (apps.accounts.services.registration). This is the one place in
this test suite where that matters: the service-level tests above use
isolated tenants and pass tenant_id explicitly instead."""

import uuid

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models.profiles import OrganizationProfile, VerificationStatus
from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_organization
from apps.kernel.models import Person, UserAccount
from apps.kernel.models.supplier import SupplierStatus
from apps.kernel.services.tenant_service import TenantService

from .helpers import PublicSiteTestCase


class HomeViewTest(TestCase):
    def test_home_page_returns_200(self):
        response = self.client.get(reverse("public_site:home"))
        self.assertEqual(response.status_code, 200)


class FindACaregiverViewTest(PublicSiteTestCase):
    def setUp(self):
        super().setUp()
        # Views always resolve the default tenant — build fixtures there too.
        self.default_tenant = TenantService.get_default_tenant()
        self.tenant = self.default_tenant

    def test_directory_page_returns_200(self):
        response = self.client.get(reverse("public_site:find-a-caregiver"))
        self.assertEqual(response.status_code, 200)

    def test_directory_page_lists_real_caregiver(self):
        self._create_caregiver_supplier(display_name="مریم احمدی تست")

        response = self.client.get(reverse("public_site:find-a-caregiver"))

        self.assertContains(response, "مریم احمدی تست")

    def test_city_filter_via_querystring(self):
        self._create_caregiver_supplier(display_name="تهرانی تست", city="tehran")
        self._create_caregiver_supplier(display_name="مشهدی تست", city="mashhad")

        response = self.client.get(reverse("public_site:find-a-caregiver"), {"city": "mashhad"})

        self.assertContains(response, "مشهدی تست")
        self.assertNotContains(response, "تهرانی تست")

    def test_invalid_supplier_type_query_param_is_ignored_not_a_500(self):
        response = self.client.get(reverse("public_site:find-a-caregiver"), {"type": "not-a-real-type"})
        self.assertEqual(response.status_code, 200)

    def test_malformed_page_query_param_falls_back_to_page_1_not_a_500(self):
        """Architecture Review M3."""
        response = self.client.get(reverse("public_site:find-a-caregiver"), {"page": "abc"})
        self.assertEqual(response.status_code, 200)

    def test_negative_page_query_param_does_not_500(self):
        response = self.client.get(reverse("public_site:find-a-caregiver"), {"page": "-1"})
        self.assertEqual(response.status_code, 200)

    def test_organization_affiliated_caregiver_with_suspended_membership_not_listed(self):
        """Architecture Review M2, exercised at the HTTP layer."""
        from apps.accounts.models.profiles import CaregiverProviderType, OrgMembershipStatus

        self._create_caregiver_supplier(
            display_name="سازمانی معلق تست",
            provider_type=CaregiverProviderType.ORGANIZATION_AFFILIATED,
            membership_status=OrgMembershipStatus.SUSPENDED,
        )

        response = self.client.get(reverse("public_site:find-a-caregiver"))

        self.assertNotContains(response, "سازمانی معلق تست")


class CaregiverProfileViewTest(PublicSiteTestCase):
    def setUp(self):
        super().setUp()
        self.default_tenant = TenantService.get_default_tenant()
        self.tenant = self.default_tenant

    def test_profile_page_returns_200_for_real_caregiver(self):
        supplier, _ = self._create_caregiver_supplier(display_name="نگار حسینی تست", verification_status="verified")

        response = self.client.get(reverse("public_site:caregiver-profile", args=[supplier.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "نگار حسینی تست")

    def test_unknown_supplier_returns_404(self):
        response = self.client.get(reverse("public_site:caregiver-profile", args=[uuid.uuid4()]))
        self.assertEqual(response.status_code, 404)

    def test_non_uuid_path_segment_returns_404(self):
        response = self.client.get("/find-a-caregiver/not-a-uuid/")
        self.assertEqual(response.status_code, 404)

    def test_existing_join_as_caregiver_marketing_page_still_works(self):
        """Regression guard: /caregivers/ (the pre-existing 'join as a
        caregiver' recruiting page) must remain untouched by the new
        /find-a-caregiver/ directory routes."""
        response = self.client.get(reverse("public_site:caregivers"))
        self.assertEqual(response.status_code, 200)


class CaregiverProfileTenantHintTest(PublicSiteTestCase):
    """Frontend remediation R2: a supplier that lives in a tenant other than
    TenantService.get_default_tenant() (e.g. seed_product_walkthrough's own
    dedicated tenant) can be previewed via an explicit, validated ?tenant=
    hint — without weakening isolation for every other caller, who never
    passes this parameter and gets exactly the pre-existing behavior.

    self.tenant here (from PublicSiteTestCase.setUp) is deliberately NOT
    the default tenant — that is the whole point of this test class."""

    def test_correct_tenant_hint_returns_200_with_real_data(self):
        supplier, _ = self._create_caregiver_supplier(
            display_name="مراقب چندمستأجری تست", verification_status="verified",
        )

        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]),
            {"tenant": self.tenant.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "مراقب چندمستأجری تست")

    def test_missing_hint_falls_back_to_default_tenant_and_404s_for_non_default_supplier(self):
        supplier, _ = self._create_caregiver_supplier()

        response = self.client.get(reverse("public_site:caregiver-profile", args=[supplier.id]))

        self.assertEqual(response.status_code, 404)

    def test_unknown_tenant_slug_404s_no_leak(self):
        supplier, _ = self._create_caregiver_supplier()

        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]),
            {"tenant": "no-such-tenant-slug"},
        )

        self.assertEqual(response.status_code, 404)

    def test_wrong_tenant_hint_cannot_reach_a_different_tenants_supplier(self):
        """The hint narrows to exactly one tenant — it is never a global,
        cross-tenant search."""
        from apps.kernel.models import Tenant

        supplier, _ = self._create_caregiver_supplier(display_name="این نباید دیده شود")
        other_tenant = Tenant.objects.create(slug=f"other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]),
            {"tenant": other_tenant.slug},
        )

        self.assertEqual(response.status_code, 404)


class OrganizationProfileTenantHintTest(PublicSiteTestCase):
    """Mirrors CaregiverProfileTenantHintTest for the organization public
    preview route."""

    def _create_organization_supplier(self, *, name="سازمان نمونه"):
        admin_person = Person.objects.create(tenant=self.tenant, full_name="مدیر سازمان")
        admin_user = UserAccount.objects.create_user(
            phone=f"0913{uuid.uuid4().hex[:7]}",
            person=admin_person,
            tenant=self.tenant,
        )
        organization = OrganizationProfile.objects.create(
            name=name,
            code=f"org-{uuid.uuid4().hex[:8]}",
            admin_user=admin_user,
            tenant=self.tenant,
            status="active",
            verification_status=VerificationStatus.VERIFIED,
        )
        supplier = get_or_create_supplier_for_organization(organization, tenant_id=self.tenant.id)
        supplier.status = SupplierStatus.ACTIVE
        supplier.service_categories = [str(self.category.id)]
        supplier.save(update_fields=["status", "service_categories"])
        return supplier, organization

    def test_profile_page_returns_200_for_real_organization(self):
        supplier, _ = self._create_organization_supplier(name="سازمان مراقبت نمونه تست")

        response = self.client.get(
            reverse("public_site:organization-profile", args=[supplier.id]),
            {"tenant": self.tenant.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "سازمان مراقبت نمونه تست")

    def test_missing_hint_falls_back_to_default_tenant_and_404s_for_non_default_supplier(self):
        supplier, _ = self._create_organization_supplier()

        response = self.client.get(reverse("public_site:organization-profile", args=[supplier.id]))

        self.assertEqual(response.status_code, 404)

    def test_unknown_tenant_slug_404s_no_leak(self):
        supplier, _ = self._create_organization_supplier()

        response = self.client.get(
            reverse("public_site:organization-profile", args=[supplier.id]),
            {"tenant": "no-such-tenant-slug"},
        )

        self.assertEqual(response.status_code, 404)

    def test_wrong_tenant_hint_cannot_reach_a_different_tenants_supplier(self):
        from apps.kernel.models import Tenant

        supplier, _ = self._create_organization_supplier(name="این نباید دیده شود")
        other_tenant = Tenant.objects.create(slug=f"other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        response = self.client.get(
            reverse("public_site:organization-profile", args=[supplier.id]),
            {"tenant": other_tenant.slug},
        )

        self.assertEqual(response.status_code, 404)

    def test_unknown_supplier_still_404s(self):
        response = self.client.get(
            reverse("public_site:organization-profile", args=[uuid.uuid4()]),
            {"tenant": self.tenant.slug},
        )
        self.assertEqual(response.status_code, 404)
