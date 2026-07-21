"""Tests for FR-018 (Public Site Coherence Remediation, PSA-004): the
organization directory's empty state must distinguish "no filters
applied, no verified organizations exist" from "your filters matched
nothing" — the audit found the bare, unfiltered /find-an-organization/
page (zero filters) unconditionally blamed "these filters" even though
none were applied.

has_active_filters (OrganizationDirectoryFiltersViewModel) is derived
from normalized, validated filter inputs — non-empty trimmed search
text, a city string that survives whitespace/casing normalization, or a
service-category id that actually matches a real category — never
merely from raw query-string presence, so a garbage/unrecognized
`?service=` value does not falsely trigger the "filtered" message."""

import uuid

from django.urls import reverse

from apps.orders.models import CatalogStatus, ServiceCategory

from .helpers import PublicSiteTestCase


class OrganizationEmptyStateTest(PublicSiteTestCase):
    def test_zero_filters_and_zero_results_shows_no_verified_organizations_message(self):
        response = self.client.get(reverse("public_site:organization-directory"), {"tenant": self.tenant.slug})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "در حال حاضر سازمان تأییدشده‌ای برای نمایش وجود ندارد")
        self.assertNotContains(response, "سازمانی با این فیلترها یافت نشد")
        self.assertNotContains(response, "پاک کردن فیلترها")

    def test_valid_filter_and_zero_results_shows_filtered_message_with_reset(self):
        response = self.client.get(
            reverse("public_site:organization-directory"),
            {"tenant": self.tenant.slug, "city": "mashhad"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "سازمانی با این فیلترها یافت نشد")
        self.assertContains(response, "پاک کردن فیلترها")
        self.assertNotContains(response, "در حال حاضر سازمان تأییدشده‌ای برای نمایش وجود ندارد")

    def test_invalid_service_category_value_is_ignored_not_treated_as_active_filter(self):
        response = self.client.get(
            reverse("public_site:organization-directory"),
            {"tenant": self.tenant.slug, "service": str(uuid.uuid4())},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "در حال حاضر سازمان تأییدشده‌ای برای نمایش وجود ندارد")
        self.assertNotContains(response, "سازمانی با این فیلترها یافت نشد")

    def test_reset_link_only_appears_when_filters_active(self):
        no_filter_response = self.client.get(
            reverse("public_site:organization-directory"),
            {"tenant": self.tenant.slug},
        )
        filtered_response = self.client.get(
            reverse("public_site:organization-directory"),
            {"tenant": self.tenant.slug, "q": "zzz-no-match"},
        )

        self.assertNotContains(no_filter_response, "پاک کردن فیلترها")
        self.assertContains(filtered_response, "پاک کردن فیلترها")

    def test_verified_organization_result_still_renders_normally(self):
        self._create_organization_supplier(name="سازمان معتبر تست خالی")

        response = self.client.get(reverse("public_site:organization-directory"), {"tenant": self.tenant.slug})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "سازمان معتبر تست خالی")
        self.assertNotContains(response, "در حال حاضر سازمان تأییدشده‌ای برای نمایش وجود ندارد")

    def test_real_category_filter_with_results_still_works(self):
        other_category = ServiceCategory.objects.create(
            tenant=self.tenant,
            name="مراقبت شبانه",
            slug="night-care",
            status=CatalogStatus.ACTIVE,
        )
        self._create_organization_supplier(
            name="سازمان دسته‌بندی تست",
            service_category_ids=[str(other_category.id)],
        )

        response = self.client.get(
            reverse("public_site:organization-directory"),
            {"tenant": self.tenant.slug, "service": str(other_category.id)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "سازمان دسته‌بندی تست")
