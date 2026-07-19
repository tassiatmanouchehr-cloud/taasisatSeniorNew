"""Tests for FR-018 (Public Site Coherence Remediation, PSA-003): the
caregiver profile's consultation-request CTA carries the selected
caregiver forward to /contact/ as a server-validated id, and /contact/
greets the visitor by name — without inventing direct booking,
messaging, payment, or order placement, and without ever trusting a
free-form name from the query string.

self.tenant (from PublicSiteTestCase.setUp) is a fresh, isolated,
non-default tenant — used as the explicit-hint tenant throughout,
mirroring every other *TenantHintTest class in this suite."""

import re
import uuid

from django.urls import reverse

from apps.kernel.models import Tenant
from apps.orders.models import Order

from .helpers import PublicSiteTestCase


class CaregiverContactContextTest(PublicSiteTestCase):
    def test_caregiver_profile_cta_carries_validated_caregiver_context(self):
        supplier, _ = self._create_caregiver_supplier(display_name="سمیرا کریمی تماس")

        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn(f"caregiver={supplier.id}", html)
        self.assertIn("درخواست مشاوره درباره این مراقب", html)

    def test_contact_destination_renders_caregiver_name_safely(self):
        supplier, _ = self._create_caregiver_supplier(display_name="سمیرا کریمی تماس دو")

        response = self.client.get(
            reverse("public_site:contact"), {"caregiver": str(supplier.id), "tenant": self.tenant.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "سمیرا کریمی تماس دو")

    def test_no_raw_uuid_appears_as_visible_text_on_contact_page(self):
        supplier, _ = self._create_caregiver_supplier(display_name="سمیرا کریمی تماس سه")

        response = self.client.get(
            reverse("public_site:contact"), {"caregiver": str(supplier.id), "tenant": self.tenant.slug},
        )
        html = response.content.decode()

        # Strip tags to inspect only visible text content, not attributes/URLs.
        visible_text = re.sub(r"<[^>]+>", " ", html)
        self.assertNotIn(str(supplier.id), visible_text)

    def test_malformed_caregiver_reference_returns_404(self):
        response = self.client.get(
            reverse("public_site:contact"), {"caregiver": "not-a-uuid", "tenant": self.tenant.slug},
        )
        self.assertEqual(response.status_code, 404)

    def test_unknown_wellformed_caregiver_id_returns_404(self):
        response = self.client.get(
            reverse("public_site:contact"), {"caregiver": str(uuid.uuid4()), "tenant": self.tenant.slug},
        )
        self.assertEqual(response.status_code, 404)

    def test_foreign_tenant_caregiver_reference_is_rejected(self):
        supplier, _ = self._create_caregiver_supplier(display_name="سمیرا کریمی تماس چهار")
        other_tenant = Tenant.objects.create(slug=f"other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        response = self.client.get(
            reverse("public_site:contact"), {"caregiver": str(supplier.id), "tenant": other_tenant.slug},
        )

        self.assertEqual(response.status_code, 404)

    def test_explicit_public_tenant_context_remains_intact(self):
        supplier, _ = self._create_caregiver_supplier(display_name="سمیرا کریمی تماس پنج")

        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        html = response.content.decode()

        self.assertIn(f"tenant={self.tenant.slug}", html)

    def test_ordinary_generic_contact_access_still_works_without_caregiver_context(self):
        response = self.client.get(reverse("public_site:contact"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "درخواست مشاوره شما درباره")

    def test_opening_contact_page_with_caregiver_context_creates_no_order(self):
        supplier, _ = self._create_caregiver_supplier(display_name="سمیرا کریمی تماس شش")
        before = Order.objects.count()

        response = self.client.get(
            reverse("public_site:contact"), {"caregiver": str(supplier.id), "tenant": self.tenant.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), before)

    def test_directory_back_link_present_on_caregiver_profile(self):
        supplier, _ = self._create_caregiver_supplier(display_name="سمیرا کریمی تماس هفت")

        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )

        self.assertContains(response, "بازگشت به فهرست مراقبان")
        self.assertContains(response, f'href="/find-a-caregiver/?tenant={self.tenant.slug}"')
