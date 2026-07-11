"""HomePageService — Epic 06."""

from apps.accounts.models.profiles import CaregiverProviderType, OrgMembershipStatus

from ..services.home_service import HomePageService
from .helpers import PublicSiteTestCase


class HomePageServiceTest(PublicSiteTestCase):
    def test_service_categories_come_from_real_catalog(self):
        home = HomePageService.get_home_view(tenant_id=self.tenant.id)

        names = {category.name for category in home.service_categories}
        self.assertIn(self.category.name, names)

    def test_featured_caregivers_are_real_and_bounded(self):
        for i in range(6):
            self._create_caregiver_supplier(display_name=f"مراقب {i}")

        home = HomePageService.get_home_view(tenant_id=self.tenant.id)

        self.assertEqual(len(home.featured_caregivers), 4)

    def test_reviews_are_empty_when_none_approved_yet(self):
        supplier, _ = self._create_caregiver_supplier()
        self._add_pending_review(supplier=supplier)

        home = HomePageService.get_home_view(tenant_id=self.tenant.id)

        self.assertEqual(home.reviews, ())

    def test_reviews_show_only_approved_ones(self):
        supplier, _ = self._create_caregiver_supplier()
        self._add_approved_review(supplier=supplier, text="تجربه خوبی بود")

        home = HomePageService.get_home_view(tenant_id=self.tenant.id)

        self.assertEqual(len(home.reviews), 1)
        self.assertEqual(home.reviews[0].written_text, "تجربه خوبی بود")

    def test_city_options_reflect_real_caregiver_cities(self):
        self._create_caregiver_supplier(city="mashhad")

        home = HomePageService.get_home_view(tenant_id=self.tenant.id)

        self.assertIn("mashhad", [option.value for option in home.city_options])

    def test_no_data_yields_empty_sections_not_fabricated_content(self):
        home = HomePageService.get_home_view(tenant_id=self.tenant.id)

        self.assertEqual(home.featured_caregivers, ())
        self.assertEqual(home.reviews, ())
        self.assertEqual(home.city_options, ())

    def test_featured_excludes_caregiver_with_suspended_organization_membership(self):
        """Architecture Review M2: the Home Page's Featured Caregivers
        section must honor the same eligibility rule as the directory."""
        self._create_caregiver_supplier(
            display_name="سازمانی معلق",
            provider_type=CaregiverProviderType.ORGANIZATION_AFFILIATED,
            membership_status=OrgMembershipStatus.SUSPENDED,
        )

        home = HomePageService.get_home_view(tenant_id=self.tenant.id)

        self.assertEqual(home.featured_caregivers, ())
