"""Customer portal "My Favorites" page — Phase 4 Sprint 4.1 (Customer
Favorites and Saved Providers).

Uses PortalTestCase's own tenant/customer fixture (helpers.py), plus a
local supplier-fixture mixin mirroring apps.public_site.tests.helpers
.PublicSiteTestCase's own caregiver/organization supplier construction —
the portal side has no equivalent fixture of its own since this is the
first portal page that needs a real ServiceSupplier."""

import uuid

from django.test.utils import CaptureQueriesContext
from django.db import connection

from apps.accounts.models.favorites import Favorite
from apps.accounts.models.profiles import CaregiverProfile, OrganizationProfile
from apps.accounts.services.supplier_bridge import (
    get_or_create_supplier_for_caregiver,
    get_or_create_supplier_for_organization,
)
from apps.kernel.models import Person, UserAccount
from apps.kernel.models.supplier import SupplierStatus

from .helpers import PortalTestCase


class _SupplierFixtureMixin:
    def _create_caregiver_supplier(self, *, tenant=None, display_name="Test Caregiver", active=True):
        tenant = tenant or self.tenant
        phone = f"0916{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=display_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        caregiver = CaregiverProfile.objects.create(
            user=user, person=person, phone=phone, display_name=display_name, verification_status="verified",
        )
        supplier = get_or_create_supplier_for_caregiver(caregiver, tenant_id=tenant.id)
        supplier.status = SupplierStatus.ACTIVE if active else SupplierStatus.SUSPENDED
        supplier.save(update_fields=["status"])
        return supplier, caregiver

    def _create_organization_supplier(self, *, tenant=None, name="Test Organization", active=True):
        tenant = tenant or self.tenant
        admin_person = Person.objects.create(tenant=tenant, full_name="Org Admin")
        admin_user = UserAccount.objects.create_user(
            phone=f"0917{uuid.uuid4().hex[:7]}", person=admin_person, tenant=tenant,
        )
        organization = OrganizationProfile.objects.create(
            name=name, code=f"org-{uuid.uuid4().hex[:8]}", admin_user=admin_user, tenant=tenant,
            status="active", verification_status="verified",
        )
        supplier = get_or_create_supplier_for_organization(organization, tenant_id=tenant.id)
        supplier.status = SupplierStatus.ACTIVE if active else SupplierStatus.SUSPENDED
        supplier.save(update_fields=["status"])
        return supplier, organization


class FavoritesViewEmptyStateTest(_SupplierFixtureMixin, PortalTestCase):
    def test_empty_state_is_shown_when_no_favorites(self):
        self.login_as_customer()
        response = self.client.get("/portal/favorites/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page"].rows), 0)

    def test_requires_authentication(self):
        response = self.client.get("/portal/favorites/")
        self.assertEqual(response.status_code, 403)


class FavoritesViewListingTest(_SupplierFixtureMixin, PortalTestCase):
    def test_lists_only_the_callers_own_favorites(self):
        caregiver_supplier, _ = self._create_caregiver_supplier(display_name="مراقب من")
        other_supplier, _ = self._create_caregiver_supplier(display_name="مراقب دیگری")
        Favorite.objects.create(customer_profile=self.customer, supplier=caregiver_supplier)
        Favorite.objects.create(customer_profile=self.other_customer, supplier=other_supplier)

        self.login_as_customer()
        response = self.client.get("/portal/favorites/")
        rows = response.context["page"].rows
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].supplier_id, str(caregiver_supplier.id))

    def test_supports_mixed_caregiver_and_organization_favorites(self):
        caregiver_supplier, _ = self._create_caregiver_supplier(display_name="مراقب من")
        org_supplier, _ = self._create_organization_supplier(name="سازمان من")
        Favorite.objects.create(customer_profile=self.customer, supplier=caregiver_supplier)
        Favorite.objects.create(customer_profile=self.customer, supplier=org_supplier)

        self.login_as_customer()
        response = self.client.get("/portal/favorites/")
        rows = response.context["page"].rows
        self.assertEqual({row.supplier_type for row in rows}, {"caregiver", "organization"})
        for row in rows:
            self.assertTrue(row.is_currently_public)
            if row.supplier_type == "caregiver":
                self.assertIsNotNone(row.caregiver_card)
                self.assertIsNone(row.organization_card)
            else:
                self.assertIsNotNone(row.organization_card)
                self.assertIsNone(row.caregiver_card)

    def test_no_longer_public_supplier_is_flagged_not_linked(self):
        inactive_supplier, _ = self._create_caregiver_supplier(display_name="غیرفعال", active=False)
        Favorite.objects.create(customer_profile=self.customer, supplier=inactive_supplier)

        self.login_as_customer()
        response = self.client.get("/portal/favorites/")
        rows = response.context["page"].rows
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0].is_currently_public)
        self.assertIsNone(rows[0].caregiver_card)
        self.assertIsNone(rows[0].organization_card)
        self.assertNotContains(response, f"/find-a-caregiver/{inactive_supplier.id}/")

    def test_nav_includes_favorites_item(self):
        self.login_as_customer()
        response = self.client.get("/portal/favorites/")
        nav_urls = [item.url for item in response.context["nav_items"]]
        self.assertIn("/portal/favorites/", nav_urls)


class FavoritesRemoveViewTest(_SupplierFixtureMixin, PortalTestCase):
    def test_post_removes_own_favorite(self):
        supplier, _ = self._create_caregiver_supplier()
        Favorite.objects.create(customer_profile=self.customer, supplier=supplier)

        self.login_as_customer()
        response = self.client.post(f"/portal/favorites/{supplier.id}/remove/")
        self.assertRedirects(response, "/portal/favorites/")
        self.assertFalse(Favorite.objects.filter(customer_profile=self.customer, supplier=supplier).exists())

    def test_cannot_remove_another_customers_favorite(self):
        supplier, _ = self._create_caregiver_supplier()
        Favorite.objects.create(customer_profile=self.other_customer, supplier=supplier)

        self.login_as_customer()
        self.client.post(f"/portal/favorites/{supplier.id}/remove/")
        self.assertTrue(Favorite.objects.filter(customer_profile=self.other_customer, supplier=supplier).exists())

    def test_remove_requires_post(self):
        supplier, _ = self._create_caregiver_supplier()
        Favorite.objects.create(customer_profile=self.customer, supplier=supplier)
        self.login_as_customer()
        response = self.client.get(f"/portal/favorites/{supplier.id}/remove/")
        self.assertEqual(response.status_code, 405)

    def test_remove_requires_authentication(self):
        supplier, _ = self._create_caregiver_supplier()
        response = self.client.post(f"/portal/favorites/{supplier.id}/remove/")
        self.assertEqual(response.status_code, 403)


class FavoritesViewPaginationTest(_SupplierFixtureMixin, PortalTestCase):
    def test_second_page_is_reachable_beyond_page_size(self):
        for index in range(13):
            supplier, _ = self._create_caregiver_supplier(display_name=f"مراقب {index}")
            Favorite.objects.create(customer_profile=self.customer, supplier=supplier)

        self.login_as_customer()
        first_page = self.client.get("/portal/favorites/")
        self.assertEqual(len(first_page.context["page"].rows), 12)
        self.assertEqual(first_page.context["page"].pagination.total_pages, 2)

        second_page = self.client.get("/portal/favorites/", {"page": 2})
        self.assertEqual(len(second_page.context["page"].rows), 1)


class FavoritesViewQueryBudgetTest(_SupplierFixtureMixin, PortalTestCase):
    """KL-012 discipline: the page's query count must stay bounded as the
    number of favorites grows — never a per-row supplier/rating/visibility
    query. Measured at 0/1/5/20 favorites (0 and 1 within the page size,
    5 well within, 20 spanning two pages)."""

    def _measure(self, count):
        for index in range(count):
            supplier, _ = self._create_caregiver_supplier(display_name=f"مراقب {index}")
            Favorite.objects.create(customer_profile=self.customer, supplier=supplier)

        self.login_as_customer()
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get("/portal/favorites/")
        self.assertEqual(response.status_code, 200)
        return len(ctx.captured_queries)

    def test_query_count_bounded_at_representative_sizes(self):
        counts = {}
        for size in (0, 1, 5, 20):
            with self.subTest(size=size):
                Favorite.objects.filter(customer_profile=self.customer).delete()
                counts[size] = self._measure(size)

        # The query count must not grow linearly with favorite count — a
        # generous fixed upper bound, well under one-query-per-row.
        self.assertLessEqual(counts[20] - counts[0], 8)
