"""CaregiverDirectoryService — Epic 06."""

from apps.accounts.models.profiles import CaregiverProviderType
from apps.kernel.models.supplier import AvailabilityStatus, SupplierStatus, SupplierType

from ..services.directory_service import CaregiverDirectoryService
from .helpers import PublicSiteTestCase


class DirectorySearchTest(PublicSiteTestCase):
    def test_lists_active_independent_and_organization_provider_caregivers(self):
        self._create_caregiver_supplier(display_name="مریم احمدی")
        self._create_caregiver_supplier(
            display_name="زهرا موسوی",
            provider_type=CaregiverProviderType.ORGANIZATION_AFFILIATED,
        )

        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id)

        self.assertEqual(page.pagination.total_count, 2)
        names = {card.display_name for card in page.caregivers}
        self.assertEqual(names, {"مریم احمدی", "زهرا موسوی"})

    def test_excludes_plain_organization_suppliers(self):
        from apps.accounts.models.profiles import OrganizationProfile
        from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_organization
        from apps.kernel.models import Person, UserAccount

        admin_person = Person.objects.create(tenant=self.tenant, full_name="مدیر سازمان")
        admin_user = UserAccount.objects.create_user(phone="09121230000", person=admin_person, tenant=self.tenant)
        org = OrganizationProfile.objects.create(
            name="شرکت نمونه",
            code="TEST-ORG-1",
            admin_user=admin_user,
            tenant=self.tenant,
            status="active",
        )
        get_or_create_supplier_for_organization(org, tenant_id=self.tenant.id)
        self._create_caregiver_supplier(display_name="مراقب واقعی")

        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id)

        self.assertEqual(page.pagination.total_count, 1)
        self.assertEqual(page.caregivers[0].display_name, "مراقب واقعی")

    def test_excludes_inactive_supplier_status(self):
        self._create_caregiver_supplier(display_name="فعال")
        self._create_caregiver_supplier(display_name="غیرفعال", supplier_status=SupplierStatus.SUSPENDED)

        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id)

        self.assertEqual(page.pagination.total_count, 1)
        self.assertEqual(page.caregivers[0].display_name, "فعال")

    def test_excludes_archived_caregiver_profile_even_if_supplier_row_active(self):
        self._create_caregiver_supplier(display_name="فعال")
        self._create_caregiver_supplier(display_name="آرشیوشده", profile_status="archived")

        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id)

        self.assertEqual(page.pagination.total_count, 1)
        self.assertEqual(page.caregivers[0].display_name, "فعال")

    def test_filters_by_city(self):
        self._create_caregiver_supplier(display_name="تهرانی", city="tehran")
        self._create_caregiver_supplier(display_name="مشهدی", city="mashhad")

        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id, city="mashhad")

        self.assertEqual(page.pagination.total_count, 1)
        self.assertEqual(page.caregivers[0].display_name, "مشهدی")

    def test_filters_by_supplier_type(self):
        self._create_caregiver_supplier(display_name="مستقل", provider_type=CaregiverProviderType.INDEPENDENT)
        self._create_caregiver_supplier(
            display_name="سازمانی",
            provider_type=CaregiverProviderType.ORGANIZATION_AFFILIATED,
        )

        page = CaregiverDirectoryService.search(
            tenant_id=self.tenant.id, supplier_type=SupplierType.ORGANIZATION_PROVIDER
        )

        self.assertEqual(page.pagination.total_count, 1)
        self.assertEqual(page.caregivers[0].display_name, "سازمانی")
        self.assertTrue(page.caregivers[0].is_organization_affiliated)

    def test_filters_by_availability_status(self):
        self._create_caregiver_supplier(display_name="در دسترس", availability_status=AvailabilityStatus.AVAILABLE)
        self._create_caregiver_supplier(display_name="مشغول", availability_status=AvailabilityStatus.BUSY)

        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id, availability_status=AvailabilityStatus.BUSY)

        self.assertEqual(page.pagination.total_count, 1)
        self.assertEqual(page.caregivers[0].display_name, "مشغول")

    def test_filters_by_text_search(self):
        self._create_caregiver_supplier(display_name="سارا محمدی")
        self._create_caregiver_supplier(display_name="نگار حسینی")

        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id, text="سارا")

        self.assertEqual(page.pagination.total_count, 1)
        self.assertEqual(page.caregivers[0].display_name, "سارا محمدی")

    def test_pagination_splits_results_across_pages(self):
        for i in range(15):
            self._create_caregiver_supplier(display_name=f"مراقب {i}")

        page1 = CaregiverDirectoryService.search(tenant_id=self.tenant.id, page=1)
        page2 = CaregiverDirectoryService.search(tenant_id=self.tenant.id, page=2)

        self.assertEqual(page1.pagination.total_count, 15)
        self.assertEqual(page1.pagination.total_pages, 2)
        self.assertEqual(len(page1.caregivers), 12)
        self.assertEqual(len(page2.caregivers), 3)
        self.assertIsNone(page1.pagination.previous_url)
        self.assertIsNotNone(page1.pagination.next_url)
        self.assertIsNotNone(page2.pagination.previous_url)
        self.assertIsNone(page2.pagination.next_url)

    def test_card_exposes_completed_jobs_and_rating(self):
        supplier, _ = self._create_caregiver_supplier(display_name="با سابقه")
        self._create_completed_order(supplier=supplier)
        self._create_completed_order(supplier=supplier)
        self._add_approved_review(supplier=supplier, rating="4.00")

        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id)

        card = page.caregivers[0]
        self.assertEqual(card.completed_jobs, 2)
        self.assertEqual(card.rating.review_count, 1)
        self.assertEqual(card.rating.average, 4)

    def test_card_with_zero_reviews_reports_no_rating_honestly(self):
        self._create_caregiver_supplier(display_name="بدون نظر")

        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id)

        self.assertIsNone(page.caregivers[0].rating.average)
        self.assertEqual(page.caregivers[0].rating.review_count, 0)

    def test_gender_filter_is_not_supported_and_reported_honestly(self):
        page = CaregiverDirectoryService.search(tenant_id=self.tenant.id)
        self.assertFalse(page.filters.gender_filter_supported)

    def test_tenant_isolation(self):
        from apps.kernel.models import Tenant

        other_tenant = Tenant.objects.create(slug="other-public-site-tenant", name="Other")
        self._create_caregiver_supplier(display_name="مال این تننت")

        page = CaregiverDirectoryService.search(tenant_id=other_tenant.id)

        self.assertEqual(page.pagination.total_count, 0)


class DirectoryFeaturedAndCitiesTest(PublicSiteTestCase):
    def test_featured_returns_top_ranked_caregivers_up_to_limit(self):
        for i in range(6):
            self._create_caregiver_supplier(display_name=f"مراقب {i}")

        featured = CaregiverDirectoryService.featured(tenant_id=self.tenant.id, limit=4)

        self.assertEqual(len(featured), 4)

    def test_available_cities_are_distinct_and_sorted(self):
        self._create_caregiver_supplier(display_name="a", city="tehran")
        self._create_caregiver_supplier(display_name="b", city="mashhad")
        self._create_caregiver_supplier(display_name="c", city="tehran")

        cities = CaregiverDirectoryService.available_cities(tenant_id=self.tenant.id)

        self.assertEqual(cities, ("mashhad", "tehran"))
