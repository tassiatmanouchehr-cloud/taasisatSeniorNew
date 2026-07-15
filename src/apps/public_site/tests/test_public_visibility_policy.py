"""Canonical public-visibility policy (BG-022) — proves the caregiver
directory, home-page listings, and the single-profile detail page all
apply the exact same eligibility rule via
apps.public_site.services.common.is_publicly_visible_attrs()."""

from django.urls import reverse

from ..services.directory_service import CaregiverDirectoryService
from ..services.profile_service import CaregiverPublicProfileService
from .helpers import PublicSiteTestCase


class CanonicalVisibilityAcrossSurfacesTest(PublicSiteTestCase):
    """One caregiver, every eligibility-breaking condition, checked
    against directory search, home-page featured cards, and the detail
    page in the same test — proves there is no divergence between
    surfaces (the root defect BG-022 records)."""

    def _assert_hidden_everywhere(self, supplier, *, display_name):
        search_page = CaregiverDirectoryService.search(tenant_id=self.tenant.id)
        self.assertNotIn(display_name, {c.display_name for c in search_page.caregivers})
        self.assertEqual(search_page.pagination.total_count, 0)

        featured = CaregiverDirectoryService.featured(tenant_id=self.tenant.id)
        self.assertNotIn(display_name, {c.display_name for c in featured})

        self.assertIsNone(CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))

        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        self.assertEqual(response.status_code, 404)

    def _assert_visible_everywhere(self, supplier, *, display_name):
        search_page = CaregiverDirectoryService.search(tenant_id=self.tenant.id)
        self.assertIn(display_name, {c.display_name for c in search_page.caregivers})
        self.assertEqual(search_page.pagination.total_count, 1)

        featured = CaregiverDirectoryService.featured(tenant_id=self.tenant.id)
        self.assertIn(display_name, {c.display_name for c in featured})

        self.assertIsNotNone(CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))

        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        self.assertEqual(response.status_code, 200)

    def test_active_verified_caregiver_visible_on_every_surface(self):
        supplier, _ = self._create_caregiver_supplier(display_name="فعال و تأییدشده", verification_status="verified")
        self._assert_visible_everywhere(supplier, display_name="فعال و تأییدشده")

    def test_draft_caregiver_hidden_on_every_surface(self):
        supplier, _ = self._create_caregiver_supplier(
            display_name="پیش‌نویس", verification_status="verified", profile_status="draft",
        )
        self._assert_hidden_everywhere(supplier, display_name="پیش‌نویس")

    def test_suspended_caregiver_hidden_on_every_surface(self):
        supplier, _ = self._create_caregiver_supplier(
            display_name="معلق", verification_status="verified", profile_status="suspended",
        )
        self._assert_hidden_everywhere(supplier, display_name="معلق")

    def test_archived_caregiver_hidden_on_every_surface(self):
        supplier, _ = self._create_caregiver_supplier(
            display_name="آرشیوشده", verification_status="verified", profile_status="archived",
        )
        self._assert_hidden_everywhere(supplier, display_name="آرشیوشده")

    def test_unverified_caregiver_hidden_on_every_surface(self):
        supplier, _ = self._create_caregiver_supplier(display_name="تأییدنشده", verification_status="unverified")
        self._assert_hidden_everywhere(supplier, display_name="تأییدنشده")

    def test_pending_verification_caregiver_hidden_on_every_surface(self):
        supplier, _ = self._create_caregiver_supplier(display_name="در انتظار بررسی", verification_status="pending")
        self._assert_hidden_everywhere(supplier, display_name="در انتظار بررسی")

    def test_inactive_account_caregiver_hidden_on_every_surface(self):
        supplier, caregiver = self._create_caregiver_supplier(
            display_name="حساب غیرفعال", verification_status="verified",
        )
        caregiver.user.is_active = False
        caregiver.user.save(update_fields=["is_active"])
        self._assert_hidden_everywhere(supplier, display_name="حساب غیرفعال")

    def test_inactive_organization_membership_caregiver_hidden_on_every_surface(self):
        from apps.accounts.models.profiles import CaregiverProviderType, OrgMembershipStatus

        supplier, _ = self._create_caregiver_supplier(
            display_name="وابستگی معلق",
            verification_status="verified",
            provider_type=CaregiverProviderType.ORGANIZATION_AFFILIATED,
            membership_status=OrgMembershipStatus.SUSPENDED,
        )
        self._assert_hidden_everywhere(supplier, display_name="وابستگی معلق")


class ListingCountAndPrivacyTest(PublicSiteTestCase):
    def test_hidden_profiles_do_not_inflate_directory_count(self):
        self._create_caregiver_supplier(display_name="دیده می‌شود", verification_status="verified")
        self._create_caregiver_supplier(display_name="پنهان ۱", verification_status="unverified")
        self._create_caregiver_supplier(display_name="پنهان ۲", profile_status="suspended", verification_status="verified")

        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id)
        self.assertEqual(page.pagination.total_count, 1)
        self.assertEqual(len(page.caregivers), 1)
        self.assertEqual(page.caregivers[0].display_name, "دیده می‌شود")

    def test_hidden_profile_absent_from_available_cities(self):
        self._create_caregiver_supplier(city="tehran", verification_status="verified")
        self._create_caregiver_supplier(city="isfahan", verification_status="unverified")

        cities = CaregiverDirectoryService.available_cities(tenant_id=self.tenant.id)
        self.assertIn("tehran", cities)
        self.assertNotIn("isfahan", cities)

    def test_directory_listing_excludes_private_contact_fields(self):
        supplier, caregiver = self._create_caregiver_supplier(
            display_name="مراقب نمونه دو", verification_status="verified",
        )
        response = self.client.get(reverse("public_site:find-a-caregiver"), {"tenant": self.tenant.slug})
        self.assertNotContains(response, caregiver.phone)
        self.assertNotContains(response, caregiver.user.phone)


class ListingQueryCountTest(PublicSiteTestCase):
    """Proves the BG-022 eligibility resolution itself (bulk_supplier_attrs())
    is O(1) query-wise regardless of candidate count — never one query per
    caregiver. Card-building/ranking enrichment (reputation, completed-jobs,
    capacity) is a separate, pre-existing per-item cost this remediation did
    not introduce and does not touch — see quality/DEFECT_AND_RISK_REGISTER.md
    KL-012 for that already-existing, out-of-scope limitation."""

    def test_eligibility_resolution_query_count_is_constant_regardless_of_candidate_count(self):
        from apps.kernel.models.supplier import ServiceSupplier, SupplierType

        from ..services import common

        for i in range(3):
            self._create_caregiver_supplier(display_name=f"few-{i}", verification_status="verified")
        small_suppliers = list(
            ServiceSupplier.objects.filter(tenant_id=self.tenant.id, supplier_type=SupplierType.INDEPENDENT_PROVIDER),
        )
        with self.assertNumQueries(2) as small_ctx:
            common.bulk_supplier_attrs(small_suppliers)
        small_query_count = len(small_ctx.captured_queries)

        for i in range(10):
            self._create_caregiver_supplier(display_name=f"many-{i}", verification_status="verified")
        large_suppliers = list(
            ServiceSupplier.objects.filter(tenant_id=self.tenant.id, supplier_type=SupplierType.INDEPENDENT_PROVIDER),
        )
        with self.assertNumQueries(small_query_count):
            common.bulk_supplier_attrs(large_suppliers)

    def test_directory_search_still_returns_correct_results_at_scale(self):
        for i in range(10):
            self._create_caregiver_supplier(display_name=f"caregiver-{i}", verification_status="verified")
        self._create_caregiver_supplier(display_name="hidden", verification_status="unverified")

        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id)
        self.assertEqual(page.pagination.total_count, 10)
        self.assertNotIn("hidden", {c.display_name for c in page.caregivers})
