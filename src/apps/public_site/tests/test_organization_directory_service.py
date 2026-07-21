"""Phase 3 Sprint 3.3 (Company Public Directory and Discovery).

Focused tests for OrganizationDirectoryService — mirrors
apps.public_site.tests.test_phase2_acceptance.Phase2QueryBudgetAcceptanceTest's
own structure for the caregiver directory (0/1/5/20+ candidate query-budget
tests), plus visibility/search/filter/pagination/privacy coverage for the
new organization directory. See traceability/ARCHITECTURE_DECISION_LOG.md
ADM-025 for the architecture decision this implements.
"""

from apps.accounts.models.profiles import VerificationStatus

from ..services.organization_directory_service import PAGE_SIZE, OrganizationDirectoryService
from .helpers import PublicSiteTestCase


class OrganizationDirectorySearchTest(PublicSiteTestCase):
    def test_verified_active_organization_is_listed(self):
        self._create_organization_supplier(name="سازمان مراقبت تست")

        page = OrganizationDirectoryService.search(tenant_id=self.tenant.id)

        self.assertEqual(page.pagination.total_count, 1)
        self.assertEqual(page.organizations[0].name, "سازمان مراقبت تست")

    def test_unverified_organization_is_excluded(self):
        self._create_organization_supplier(verification_status=VerificationStatus.UNVERIFIED)

        page = OrganizationDirectoryService.search(tenant_id=self.tenant.id)

        self.assertEqual(page.pagination.total_count, 0)

    def test_archived_organization_is_excluded(self):
        self._create_organization_supplier(status="archived")

        page = OrganizationDirectoryService.search(tenant_id=self.tenant.id)

        self.assertEqual(page.pagination.total_count, 0)

    def test_deactivated_admin_account_excludes_organization(self):
        self._create_organization_supplier(admin_is_active=False)

        page = OrganizationDirectoryService.search(tenant_id=self.tenant.id)

        self.assertEqual(page.pagination.total_count, 0)

    def test_independent_caregiver_supplier_never_appears_in_organization_directory(self):
        """The organization directory is scoped to SupplierType.ORGANIZATION
        only — CAREGIVER_SUPPLIER_TYPES suppliers (real caregivers) must
        never leak into it, and vice versa (ADM-025's disjointness claim)."""
        self._create_caregiver_supplier(display_name="مراقب مستقل تست", verification_status="verified")

        page = OrganizationDirectoryService.search(tenant_id=self.tenant.id)

        self.assertEqual(page.pagination.total_count, 0)

    def test_text_search_matches_display_name(self):
        self._create_organization_supplier(name="سازمان الف")
        self._create_organization_supplier(name="سازمان ب")

        page = OrganizationDirectoryService.search(tenant_id=self.tenant.id, text="الف")

        self.assertEqual(page.pagination.total_count, 1)
        self.assertEqual(page.organizations[0].name, "سازمان الف")

    def test_city_filter(self):
        self._create_organization_supplier(name="سازمان تهرانی", city="tehran")
        self._create_organization_supplier(name="سازمان مشهدی", city="mashhad")

        page = OrganizationDirectoryService.search(tenant_id=self.tenant.id, city="mashhad")

        self.assertEqual(page.pagination.total_count, 1)
        self.assertEqual(page.organizations[0].name, "سازمان مشهدی")

    def test_service_category_filter(self):
        from apps.orders.models import CatalogStatus, ServiceCategory

        other_category = ServiceCategory.objects.create(
            tenant=self.tenant,
            name="خدمت دیگر",
            slug="other-service",
            status=CatalogStatus.ACTIVE,
        )
        self._create_organization_supplier(name="سازمان با خدمت اصلی")
        self._create_organization_supplier(
            name="سازمان با خدمت دیگر",
            service_category_ids=[str(other_category.id)],
        )

        page = OrganizationDirectoryService.search(tenant_id=self.tenant.id, service_category_id=str(other_category.id))

        self.assertEqual(page.pagination.total_count, 1)
        self.assertEqual(page.organizations[0].name, "سازمان با خدمت دیگر")

    def test_malformed_page_falls_back_to_page_1(self):
        self._create_organization_supplier()
        page = OrganizationDirectoryService.search(tenant_id=self.tenant.id, page="not-a-number")
        self.assertEqual(page.pagination.current_page, 1)

    def test_pagination_bounds_page_size(self):
        for i in range(15):
            self._create_organization_supplier(name=f"سازمان-{i}")

        page = OrganizationDirectoryService.search(tenant_id=self.tenant.id, page=1)
        self.assertEqual(page.pagination.total_count, 15)
        self.assertEqual(page.pagination.total_pages, 2)  # ceil(15 / 12)
        self.assertEqual(len(page.organizations), PAGE_SIZE)

        last_page = OrganizationDirectoryService.search(tenant_id=self.tenant.id, page=2)
        self.assertEqual(len(last_page.organizations), 3)


class OrganizationDirectoryCardDataTest(PublicSiteTestCase):
    def test_logo_url_present_when_logo_uploaded(self):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buffer = io.BytesIO()
        Image.new("RGB", (1, 1), color=(0, 255, 0)).save(buffer, format="PNG")

        _, organization = self._create_organization_supplier(name="سازمان با لوگو")
        organization.logo = SimpleUploadedFile("logo.png", buffer.getvalue(), content_type="image/png")
        organization.save(update_fields=["logo"])

        page = OrganizationDirectoryService.search(tenant_id=self.tenant.id)

        self.assertTrue(page.organizations[0].logo_url)
        self.assertIn(".png", page.organizations[0].logo_url)

    def test_logo_url_empty_when_no_logo_uploaded(self):
        self._create_organization_supplier(name="سازمان بدون لوگو")

        page = OrganizationDirectoryService.search(tenant_id=self.tenant.id)

        self.assertEqual(page.organizations[0].logo_url, "")
        self.assertTrue(page.organizations[0].logo_initial)

    def test_active_provider_count_reflects_active_caregiver_memberships(self):
        _, organization = self._create_organization_supplier(name="سازمان با مراقب")
        self._add_active_caregiver_to_organization(organization=organization)
        self._add_active_caregiver_to_organization(organization=organization)

        page = OrganizationDirectoryService.search(tenant_id=self.tenant.id)

        self.assertEqual(page.organizations[0].active_provider_count, 2)

    def test_headline_and_service_names_present_on_card(self):
        self._create_organization_supplier(name="سازمان با تیتر", headline="خدمات درجه یک")

        page = OrganizationDirectoryService.search(tenant_id=self.tenant.id)

        self.assertEqual(page.organizations[0].headline, "خدمات درجه یک")
        self.assertIn("مراقبت روزانه", page.organizations[0].service_names)

    def test_no_private_field_leakage(self):
        """The card ViewModel must never carry staff details, admin
        account identifiers, or internal notes — only the fields
        OrganizationCardViewModel declares."""
        self._create_organization_supplier(name="سازمان محرمانه")

        page = OrganizationDirectoryService.search(tenant_id=self.tenant.id)
        card_fields = set(vars(page.organizations[0]).keys())

        self.assertEqual(
            card_fields,
            {
                "supplier_id",
                "name",
                "logo_initial",
                "logo_url",
                "headline",
                "city",
                "service_names",
                "verification_status",
                "verification_label",
                "is_verified",
                "rating",
                "active_provider_count",
                "profile_url",
            },
        )


class OrganizationDirectoryQueryBudgetTest(PublicSiteTestCase):
    """Mirrors Phase2QueryBudgetAcceptanceTest's own structure for the
    caregiver directory — proves the organization directory's query count
    is a stable maximum, bounded by PAGE_SIZE, not candidate count."""

    def _seed(self, count, *, city="tehran", name_prefix="org"):
        for i in range(count):
            self._create_organization_supplier(name=f"{name_prefix}-{i}", city=city)

    def _query_count(self, callable_):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            callable_()
        return len(ctx.captured_queries)

    def test_query_count_does_not_grow_from_1_to_5_organizations(self):
        self._seed(1)
        count_at_1 = self._query_count(lambda: OrganizationDirectoryService.search(tenant_id=self.tenant.id))
        self._seed(4)  # 5 total
        count_at_5 = self._query_count(lambda: OrganizationDirectoryService.search(tenant_id=self.tenant.id))
        self.assertEqual(count_at_1, count_at_5)

    def test_query_count_is_a_stable_maximum_beyond_one_page(self):
        self._seed(20)
        count_at_20 = self._query_count(lambda: OrganizationDirectoryService.search(tenant_id=self.tenant.id))
        self._seed(80)  # 100 total
        count_at_100 = self._query_count(lambda: OrganizationDirectoryService.search(tenant_id=self.tenant.id))
        self.assertEqual(count_at_20, count_at_100)

    def test_city_filter_query_count_is_a_stable_maximum(self):
        self._seed(20, city="tehran")
        count_at_20 = self._query_count(
            lambda: OrganizationDirectoryService.search(tenant_id=self.tenant.id, city="tehran"),
        )
        self._seed(80, city="tehran", name_prefix="more")  # 100 total
        count_at_100 = self._query_count(
            lambda: OrganizationDirectoryService.search(tenant_id=self.tenant.id, city="tehran"),
        )
        self.assertEqual(count_at_20, count_at_100)
