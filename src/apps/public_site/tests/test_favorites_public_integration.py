"""Public profile favorite-toggle integration — Phase 4 Sprint 4.1
(Customer Favorites and Saved Providers).

Covers: anonymous visitors never see a broken control, authenticated
non-customer actors are rejected (403) rather than 500ing, an eligible
customer can add/remove via POST, the redirect target is always the
server-resolved profile URL (never a client-supplied "next"), a
wrong-tenant/unknown supplier is absorbed silently (no existence
disclosure), and GET is rejected on the mutation endpoint."""

import uuid

from django.test import TestCase

from apps.accounts.models import CustomerProfile
from apps.accounts.models.favorites import Favorite
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.services.tenant_service import TenantService

from .helpers import PublicSiteTestCase


class _CustomerMixin:
    def _create_customer(self, *, tenant, display_name="Test Customer"):
        phone = f"0915{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=display_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return CustomerProfile.objects.create(user=user, person=person, phone=phone, display_name=display_name)


class CaregiverFavoriteToggleTest(_CustomerMixin, PublicSiteTestCase, TestCase):
    def setUp(self):
        super().setUp()
        # Profile views resolve the platform's single default tenant when no
        # ?tenant= hint is given (see test_views.py's own CaregiverProfileViewTest) —
        # mirror that precedent rather than the isolated per-test tenant
        # PublicSiteTestCase.setUp() creates by default.
        self.tenant = TenantService.get_default_tenant()
        self.supplier, self.caregiver = self._create_caregiver_supplier(verification_status="verified")
        self.customer = self._create_customer(tenant=self.tenant)
        self.toggle_url = f"/find-a-caregiver/{self.supplier.id}/favorite/"
        self.profile_url = f"/find-a-caregiver/{self.supplier.id}/"

    def test_anonymous_profile_page_renders_without_favorite_control(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["can_favorite"])
        self.assertFalse(response.context["profile"].is_favorited)

    def test_anonymous_toggle_post_is_rejected(self):
        response = self.client.post(self.toggle_url, {"action": "add"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Favorite.objects.count(), 0)

    def test_toggle_get_is_rejected(self):
        self.client.force_login(self.customer.user)
        response = self.client.get(self.toggle_url)
        self.assertEqual(response.status_code, 405)

    def test_authenticated_non_customer_actor_gets_403_not_500(self):
        """A caregiver or organization staff member browsing the directory
        while logged into their own account (no CustomerProfile) must
        never see a broken control on GET, and must get a clean 403 (not
        an unhandled exception) if they somehow POST the toggle."""
        response = self.client.get(self.profile_url)
        self.client.force_login(self.caregiver.user)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["can_favorite"])

        response = self.client.post(self.toggle_url, {"action": "add"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Favorite.objects.count(), 0)

    def test_customer_can_add_favorite_via_post(self):
        self.client.force_login(self.customer.user)
        response = self.client.post(self.toggle_url, {"action": "add"})
        self.assertRedirects(response, self.profile_url)
        self.assertTrue(Favorite.objects.filter(customer_profile=self.customer, supplier=self.supplier).exists())

    def test_customer_can_remove_favorite_via_post(self):
        Favorite.objects.create(customer_profile=self.customer, supplier=self.supplier)
        self.client.force_login(self.customer.user)
        response = self.client.post(self.toggle_url, {"action": "remove"})
        self.assertRedirects(response, self.profile_url)
        self.assertFalse(Favorite.objects.filter(customer_profile=self.customer, supplier=self.supplier).exists())

    def test_profile_page_reflects_saved_state_for_owning_customer(self):
        Favorite.objects.create(customer_profile=self.customer, supplier=self.supplier)
        self.client.force_login(self.customer.user)
        response = self.client.get(self.profile_url)
        self.assertTrue(response.context["profile"].is_favorited)
        self.assertTrue(response.context["can_favorite"])

    def test_redirect_target_ignores_client_supplied_next_parameter(self):
        self.client.force_login(self.customer.user)
        response = self.client.post(
            self.toggle_url, {"action": "add", "next": "https://evil.example.com/phish"},
        )
        self.assertEqual(response["Location"], self.profile_url)

    def test_toggle_on_unknown_supplier_id_does_not_disclose_existence(self):
        self.client.force_login(self.customer.user)
        unknown_id = uuid.uuid4()
        response = self.client.post(f"/find-a-caregiver/{unknown_id}/favorite/", {"action": "add"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Favorite.objects.count(), 0)

    def test_toggle_on_wrong_tenant_supplier_is_silently_absorbed(self):
        other_tenant = Tenant.objects.create(slug=f"pub-fav-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")
        cross_supplier, _ = self._create_caregiver_supplier_in_tenant(other_tenant)
        self.client.force_login(self.customer.user)
        response = self.client.post(f"/find-a-caregiver/{cross_supplier.id}/favorite/", {"action": "add"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Favorite.objects.filter(customer_profile=self.customer).count(), 0)

    def test_organization_supplier_is_rejected_by_the_caregiver_route(self):
        """PR #16 architecture-review remediation (merge blocker F1): a
        same-tenant organization supplier posted to the caregiver toggle
        route must be refused exactly like a wrong-tenant/unknown one —
        no Favorite row created, same non-disclosing 302 response."""
        org_supplier, _ = self._create_organization_supplier()
        self.client.force_login(self.customer.user)
        response = self.client.post(f"/find-a-caregiver/{org_supplier.id}/favorite/", {"action": "add"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Favorite.objects.filter(customer_profile=self.customer).count(), 0)

    def _create_caregiver_supplier_in_tenant(self, tenant):
        old_tenant = self.tenant
        self.tenant = tenant
        try:
            return self._create_caregiver_supplier(display_name="Cross Tenant Caregiver")
        finally:
            self.tenant = old_tenant


class OrganizationFavoriteToggleTest(_CustomerMixin, PublicSiteTestCase, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = TenantService.get_default_tenant()
        self.supplier, self.organization = self._create_organization_supplier()
        self.customer = self._create_customer(tenant=self.tenant)
        self.toggle_url = f"/find-an-organization/{self.supplier.id}/favorite/"
        self.profile_url = f"/find-an-organization/{self.supplier.id}/"

    def test_anonymous_profile_page_renders_without_favorite_control(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["can_favorite"])

    def test_anonymous_toggle_post_is_rejected(self):
        response = self.client.post(self.toggle_url, {"action": "add"})
        self.assertEqual(response.status_code, 403)

    def test_customer_can_add_and_remove_favorite(self):
        self.client.force_login(self.customer.user)
        self.client.post(self.toggle_url, {"action": "add"})
        self.assertTrue(Favorite.objects.filter(customer_profile=self.customer, supplier=self.supplier).exists())

        self.client.post(self.toggle_url, {"action": "remove"})
        self.assertFalse(Favorite.objects.filter(customer_profile=self.customer, supplier=self.supplier).exists())

    def test_profile_page_reflects_saved_state(self):
        Favorite.objects.create(customer_profile=self.customer, supplier=self.supplier)
        self.client.force_login(self.customer.user)
        response = self.client.get(self.profile_url)
        self.assertTrue(response.context["profile"].is_favorited)

    def test_caregiver_supplier_is_rejected_by_the_organization_route(self):
        """PR #16 architecture-review remediation (merge blocker F1): a
        same-tenant caregiver supplier posted to the organization toggle
        route must be refused exactly like a wrong-tenant/unknown one —
        no Favorite row created, same non-disclosing 302 response."""
        caregiver_supplier, _ = self._create_caregiver_supplier()
        self.client.force_login(self.customer.user)
        response = self.client.post(f"/find-an-organization/{caregiver_supplier.id}/favorite/", {"action": "add"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Favorite.objects.filter(customer_profile=self.customer).count(), 0)
