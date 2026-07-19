"""HTTP-level tests for the Epic 06 public views.

All four public caregiver/organization views (find_a_caregiver,
caregiver_profile, find_an_organization, organization_profile) resolve
an optional ?tenant=<slug> hint via the single shared
_resolve_optional_tenant_hint() helper, falling back to
TenantService.get_default_tenant_id() when no hint is given — see the
*TenantHintTest classes below for that behavior specifically. The plain
FindACaregiverViewTest/FindAnOrganizationViewTest/*ProfileViewTest
classes below deliberately build their fixtures against the platform's
real default tenant (TenantService.get_default_tenant()) and never pass
a hint, so they exercise exactly the no-hint/default-tenant path every
other unauthenticated view in this codebase also takes
(apps.accounts.services.registration). This is the one place in this
test suite where that distinction matters: the service-level tests above
use isolated tenants and pass tenant_id explicitly instead."""

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


class FindACaregiverViewTenantHintTest(PublicSiteTestCase):
    """Regression: find_a_caregiver() (the directory view) never resolved
    the ?tenant=<slug> hint that caregiver_profile() (the detail view)
    already honored — a caregiver publicly visible at its own direct
    detail URL under an explicit tenant hint silently vanished from the
    directory search for that same tenant/hint, because the directory
    always searched TenantService.get_default_tenant_id() regardless of
    the query string. Reproduced against a real running server against
    seed_product_walkthrough's own dedicated demo tenant before this fix
    (directory: 0 results; detail: 200, fully rendered).

    self.tenant here (from PublicSiteTestCase.setUp) is deliberately NOT
    the default tenant — mirrors CaregiverProfileTenantHintTest exactly."""

    def test_correct_tenant_hint_lists_the_caregiver(self):
        self._create_caregiver_supplier(display_name="مراقب چندمستأجری فهرست تست")

        response = self.client.get(reverse("public_site:find-a-caregiver"), {"tenant": self.tenant.slug})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "مراقب چندمستأجری فهرست تست")

    def test_missing_hint_falls_back_to_default_tenant_and_does_not_list_non_default_supplier(self):
        self._create_caregiver_supplier(display_name="نباید بدون تنانت دیده شود")

        response = self.client.get(reverse("public_site:find-a-caregiver"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "نباید بدون تنانت دیده شود")

    def test_unknown_tenant_slug_404s_no_leak(self):
        self._create_caregiver_supplier()

        response = self.client.get(reverse("public_site:find-a-caregiver"), {"tenant": "no-such-tenant-slug"})

        self.assertEqual(response.status_code, 404)

    def test_wrong_tenant_hint_cannot_reach_a_different_tenants_caregivers(self):
        """The hint narrows the directory to exactly one tenant — it is
        never a global, cross-tenant search."""
        from apps.kernel.models import Tenant

        self._create_caregiver_supplier(display_name="این نباید در فهرست دیده شود")
        other_tenant = Tenant.objects.create(slug=f"other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        response = self.client.get(reverse("public_site:find-a-caregiver"), {"tenant": other_tenant.slug})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "این نباید در فهرست دیده شود")

    def test_unverified_caregiver_not_listed_even_with_correct_tenant_hint(self):
        self._create_caregiver_supplier(display_name="تأییدنشده تست", verification_status="unverified")

        response = self.client.get(reverse("public_site:find-a-caregiver"), {"tenant": self.tenant.slug})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "تأییدنشده تست")

    def test_draft_caregiver_not_listed_even_with_correct_tenant_hint(self):
        self._create_caregiver_supplier(display_name="پیش‌نویس تست", profile_status="draft")

        response = self.client.get(reverse("public_site:find-a-caregiver"), {"tenant": self.tenant.slug})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "پیش‌نویس تست")

    def test_inactive_supplier_not_listed_even_with_correct_tenant_hint(self):
        from apps.kernel.models.supplier import SupplierStatus

        self._create_caregiver_supplier(display_name="تعلیق تست", supplier_status=SupplierStatus.SUSPENDED)

        response = self.client.get(reverse("public_site:find-a-caregiver"), {"tenant": self.tenant.slug})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "تعلیق تست")

    def test_caregiver_visible_at_detail_hint_is_also_visible_at_directory_hint(self):
        """Consistency invariant: for an unfiltered directory request in
        the same tenant, every caregiver eligible for public detail
        visibility must also be eligible for directory visibility."""
        supplier, _ = self._create_caregiver_supplier(display_name="سازگاری جزئیات و فهرست تست")

        detail_response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        directory_response = self.client.get(reverse("public_site:find-a-caregiver"), {"tenant": self.tenant.slug})

        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(directory_response, "سازگاری جزئیات و فهرست تست")


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

    def test_logo_rendered_when_present(self):
        """PR #13 remediation: the real uploaded logo is rendered on the
        public profile page (an <img> tag pointing at the logo's own
        storage URL), not just the initials avatar."""
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        supplier, organization = self._create_organization_supplier(name="سازمان با لوگو")
        buffer = io.BytesIO()
        Image.new("RGB", (1, 1), color=(0, 255, 0)).save(buffer, format="PNG")
        organization.logo.save(
            "logo.png", SimpleUploadedFile("logo.png", buffer.getvalue(), content_type="image/png"), save=True,
        )

        response = self.client.get(
            reverse("public_site:organization-profile", args=[supplier.id]),
            {"tenant": self.tenant.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, organization.logo.url)
        self.assertContains(response, "<img")

    def test_initials_fallback_when_no_logo(self):
        """No logo uploaded — the page still renders (initials avatar
        fallback), and no broken/empty <img src=""> is emitted."""
        supplier, organization = self._create_organization_supplier(name="سازمان بدون لوگو")
        self.assertFalse(organization.logo)

        response = self.client.get(
            reverse("public_site:organization-profile", args=[supplier.id]),
            {"tenant": self.tenant.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<img src=""')

    def test_query_count_unaffected_by_logo_presence(self):
        """Reading `entity.logo.url` off the already-resolved entity adds
        no query — proven by comparing the page's query count with and
        without a logo present."""
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.db import connection, reset_queries
        from django.test.utils import CaptureQueriesContext
        from PIL import Image

        supplier_without, _ = self._create_organization_supplier(name="بدون لوگو")
        supplier_with, organization_with = self._create_organization_supplier(name="با لوگو")
        buffer = io.BytesIO()
        Image.new("RGB", (1, 1), color=(0, 255, 0)).save(buffer, format="PNG")
        organization_with.logo.save(
            "logo.png", SimpleUploadedFile("logo.png", buffer.getvalue(), content_type="image/png"), save=True,
        )

        reset_queries()
        with CaptureQueriesContext(connection) as without_logo:
            self.client.get(
                reverse("public_site:organization-profile", args=[supplier_without.id]),
                {"tenant": self.tenant.slug},
            )
        with CaptureQueriesContext(connection) as with_logo:
            self.client.get(
                reverse("public_site:organization-profile", args=[supplier_with.id]),
                {"tenant": self.tenant.slug},
            )

        self.assertEqual(len(without_logo.captured_queries), len(with_logo.captured_queries))


class FindAnOrganizationViewTest(PublicSiteTestCase):
    """Phase 3 Sprint 3.3 (Company Public Directory and Discovery) — HTTP-level
    coverage mirroring FindACaregiverViewTest's own structure exactly."""

    def setUp(self):
        super().setUp()
        self.default_tenant = TenantService.get_default_tenant()
        self.tenant = self.default_tenant

    def test_directory_page_returns_200(self):
        response = self.client.get(reverse("public_site:organization-directory"))
        self.assertEqual(response.status_code, 200)

    def test_directory_page_lists_real_organization(self):
        self._create_organization_supplier(name="سازمان نمای تست")

        response = self.client.get(reverse("public_site:organization-directory"))

        self.assertContains(response, "سازمان نمای تست")

    def test_unverified_organization_not_listed(self):
        self._create_organization_supplier(
            name="سازمان تأییدنشده تست", verification_status=VerificationStatus.UNVERIFIED,
        )

        response = self.client.get(reverse("public_site:organization-directory"))

        self.assertNotContains(response, "سازمان تأییدنشده تست")

    def test_city_filter_via_querystring(self):
        self._create_organization_supplier(name="سازمان تهرانی تست", city="tehran")
        self._create_organization_supplier(name="سازمان مشهدی تست", city="mashhad")

        response = self.client.get(reverse("public_site:organization-directory"), {"city": "mashhad"})

        self.assertContains(response, "سازمان مشهدی تست")
        self.assertNotContains(response, "سازمان تهرانی تست")

    def test_malformed_page_query_param_falls_back_to_page_1_not_a_500(self):
        response = self.client.get(reverse("public_site:organization-directory"), {"page": "abc"})
        self.assertEqual(response.status_code, 200)

    def test_existing_organizations_marketing_page_still_works(self):
        """Regression guard: /organizations/ (the pre-existing B2B
        recruitment page — ADM-025 Option B) must remain untouched by the
        new /find-an-organization/ directory route."""
        response = self.client.get(reverse("public_site:organizations"))
        self.assertEqual(response.status_code, 200)

    def test_directory_route_is_distinct_from_profile_route(self):
        """path("find-an-organization/", ...) must resolve before
        path("find-an-organization/<uuid:supplier_id>/", ...) — the list
        route must never be swallowed by the detail route's pattern."""
        supplier, _ = self._create_organization_supplier(name="سازمان مسیر تست")

        list_response = self.client.get("/find-an-organization/")
        detail_response = self.client.get(f"/find-an-organization/{supplier.id}/")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)


class FindAnOrganizationViewTenantHintTest(PublicSiteTestCase):
    """Regression: find_an_organization() (the organization directory view)
    never resolved the ?tenant=<slug> hint that organization_profile()
    (the detail view) already honored — the same class of defect fixed
    for find_a_caregiver() in FindACaregiverViewTenantHintTest, applied
    symmetrically to the organization directory. Reproduced against a
    real running server with a real verified/ACTIVE organization in
    seed_product_walkthrough's own dedicated demo tenant before this fix
    (directory: 0 results; detail: 200, fully rendered).

    self.tenant here (from PublicSiteTestCase.setUp) is deliberately NOT
    the default tenant — mirrors FindACaregiverViewTenantHintTest and
    OrganizationProfileTenantHintTest exactly."""

    def test_correct_tenant_hint_lists_the_organization(self):
        self._create_organization_supplier(name="سازمان چندمستأجری فهرست تست")

        response = self.client.get(reverse("public_site:organization-directory"), {"tenant": self.tenant.slug})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "سازمان چندمستأجری فهرست تست")

    def test_missing_hint_falls_back_to_default_tenant_and_does_not_list_non_default_organization(self):
        self._create_organization_supplier(name="نباید بدون تنانت دیده شود سازمان")

        response = self.client.get(reverse("public_site:organization-directory"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "نباید بدون تنانت دیده شود سازمان")

    def test_unknown_tenant_slug_404s_no_leak(self):
        self._create_organization_supplier()

        response = self.client.get(reverse("public_site:organization-directory"), {"tenant": "no-such-tenant-slug"})

        self.assertEqual(response.status_code, 404)

    def test_wrong_tenant_hint_cannot_reach_a_different_tenants_organizations(self):
        """The hint narrows the directory to exactly one tenant — it is
        never a global, cross-tenant search."""
        from apps.kernel.models import Tenant

        self._create_organization_supplier(name="این نباید در فهرست دیده شود سازمان")
        other_tenant = Tenant.objects.create(slug=f"other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        response = self.client.get(reverse("public_site:organization-directory"), {"tenant": other_tenant.slug})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "این نباید در فهرست دیده شود سازمان")

    def test_unverified_organization_not_listed_even_with_correct_tenant_hint(self):
        self._create_organization_supplier(name="تأییدنشده تست سازمان", verification_status=VerificationStatus.UNVERIFIED)

        response = self.client.get(reverse("public_site:organization-directory"), {"tenant": self.tenant.slug})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "تأییدنشده تست سازمان")

    def test_draft_organization_not_listed_even_with_correct_tenant_hint(self):
        self._create_organization_supplier(name="پیش‌نویس تست سازمان", status="draft")

        response = self.client.get(reverse("public_site:organization-directory"), {"tenant": self.tenant.slug})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "پیش‌نویس تست سازمان")

    def test_inactive_supplier_not_listed_even_with_correct_tenant_hint(self):
        supplier, _ = self._create_organization_supplier(name="تعلیق تست سازمان")
        supplier.status = SupplierStatus.SUSPENDED
        supplier.save(update_fields=["status"])

        response = self.client.get(reverse("public_site:organization-directory"), {"tenant": self.tenant.slug})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "تعلیق تست سازمان")

    def test_organization_visible_at_detail_hint_is_also_visible_at_directory_hint(self):
        """Consistency invariant: for an unfiltered directory request in
        the same tenant, every organization eligible for public detail
        visibility must also be eligible for directory visibility."""
        supplier, _ = self._create_organization_supplier(name="سازگاری جزئیات و فهرست تست سازمان")

        detail_response = self.client.get(
            reverse("public_site:organization-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        directory_response = self.client.get(
            reverse("public_site:organization-directory"), {"tenant": self.tenant.slug},
        )

        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(directory_response, "سازگاری جزئیات و فهرست تست سازمان")
