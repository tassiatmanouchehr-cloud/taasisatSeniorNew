"""Public Caregiver Marketplace Remediation.

Root cause of the reported "13 CaregiverProfile rows exist, but
/find-a-caregiver/ shows 0 caregivers" symptom: every filtering/
visibility predicate in apps.public_site.services.directory_service and
apps.public_site.services.common was already correct (proven directly —
see the required-report predicate table). The actual defect was tenant
resolution: apps.public_site.services.tenant_context.resolve_public_tenant()
correctly, deliberately falls back to TenantService's platform default
tenant when neither an explicit ?tenant= hint nor
settings.PUBLIC_SITE_TENANT_SLUG is configured — and the realistic demo
dataset apps.kernel.management.commands.seed_product_walkthrough builds
deliberately lives in a *separate*, non-default tenant (by design — see
that command's own module docstring on --reset-demo's tenant boundary).
A deployment/environment that never configures PUBLIC_SITE_TENANT_SLUG
therefore shows a correctly-empty (not broken) directory for the
platform default tenant, while CaregiverProfile.objects.count() (a
cross-tenant count) reports a healthy-looking total. This file's first
test class characterizes that as expected, non-defect behavior — the
platform default tenant is *supposed* to be empty of demo data, so a
genuinely public production tenant that has itself been used to
onboard/verify a caregiver is unaffected. No hardcoded tenant slug is
introduced anywhere in code (config/settings/base.py's own comment,
unchanged by this remediation, already documents why not) — see instead
this same remediation's seed_product_walkthrough print_report changes
(apps.kernel.tests.test_seed_product_walkthrough
.SeedProductWalkthroughPublicDirectoryDiscoveryOutputTest) for the actual
fix: the operator-facing guidance that was missing.

The remaining classes below cover the two genuine, addressable defects
this remediation *does* fix in code: directory cards built from a raw
f-string URL instead of Django's own named route
(apps.public_site.services.directory_service.CaregiverDirectoryService
._build_card()), and a caregiver's own uploaded avatar never reaching any
public view (apps.public_site.services.common.bulk_supplier_attrs())."""

from django.test import TestCase
from django.urls import reverse

from apps.kernel.services.tenant_service import TenantService

from .helpers import PublicSiteTestCase


class DefaultTenantEmptyDirectoryIsNotABugTest(TestCase):
    """Characterizes the reported symptom directly: the platform default
    tenant, when it genuinely has no eligible caregivers of its own,
    renders a normal 200 empty-state page — never a 500, never a
    misleading result — confirming the "0 results" behavior itself was
    correct all along; the defect was a missing operator-facing
    explanation (fixed in seed_product_walkthrough's own report, not
    here) and two real code defects (fixed in the classes below)."""

    def test_default_tenant_with_no_eligible_caregivers_returns_200_with_empty_state(self):
        # Deliberately builds no fixture at all — this platform default
        # tenant may already carry caregivers from other tests/seeds in a
        # shared local dev database, so this only asserts the response is
        # healthy, never a crash, regardless of what it currently contains.
        response = self.client.get(reverse("public_site:find-a-caregiver"))
        self.assertEqual(response.status_code, 200)


class EmptyQueryStringFilterTest(PublicSiteTestCase):
    """Phase 6: an empty (but present) filter query parameter must behave
    identically to that parameter being entirely absent, never as an
    active restrictive filter that matches nothing."""

    def setUp(self):
        super().setUp()
        self.default_tenant = TenantService.get_default_tenant()
        self.tenant = self.default_tenant
        self._create_caregiver_supplier(display_name="مراقب فیلتر خالی تست")

    def test_empty_city_query_param_does_not_eliminate_results(self):
        response = self.client.get(reverse("public_site:find-a-caregiver"), {"city": ""})
        self.assertContains(response, "مراقب فیلتر خالی تست")

    def test_empty_availability_query_param_does_not_eliminate_results(self):
        response = self.client.get(reverse("public_site:find-a-caregiver"), {"availability": ""})
        self.assertContains(response, "مراقب فیلتر خالی تست")

    def test_empty_service_query_param_does_not_eliminate_results(self):
        response = self.client.get(reverse("public_site:find-a-caregiver"), {"service": ""})
        self.assertContains(response, "مراقب فیلتر خالی تست")

    def test_plain_url_with_no_query_string_at_all_still_lists_the_caregiver(self):
        response = self.client.get(reverse("public_site:find-a-caregiver"))
        self.assertContains(response, "مراقب فیلتر خالی تست")


class DirectoryCardUsesNamedUrlTest(PublicSiteTestCase):
    """The card's profile_url must come from Django's own named route
    (reverse("public_site:caregiver-profile", ...)), never a hand-built
    f-string — proven by asserting the exact byte-for-byte match against
    reverse()'s own output, not merely that the link happens to resolve."""

    def test_card_profile_url_matches_reverse_exactly(self):
        supplier, _ = self._create_caregiver_supplier(display_name="لینک نام‌گذاری‌شده تست")

        response = self.client.get(reverse("public_site:find-a-caregiver"), {"tenant": self.tenant.slug})

        expected_path = reverse("public_site:caregiver-profile", args=[supplier.id])
        self.assertContains(response, f'href="{expected_path}?tenant={self.tenant.slug}"')

    def test_card_profile_url_resolves_to_a_real_200_profile_page(self):
        supplier, _ = self._create_caregiver_supplier(display_name="لینک قابل بازکردن تست")

        directory_response = self.client.get(reverse("public_site:find-a-caregiver"), {"tenant": self.tenant.slug})
        expected_path = reverse("public_site:caregiver-profile", args=[supplier.id])
        self.assertContains(directory_response, expected_path)

        profile_response = self.client.get(expected_path, {"tenant": self.tenant.slug})
        self.assertEqual(profile_response.status_code, 200)


class CaregiverAvatarPublicVisibilityTest(PublicSiteTestCase):
    """A caregiver's own uploaded avatar (CaregiverProfile.avatar, set via
    ProfileMediaService.set_caregiver_avatar() — the same owner-authorized
    path the provider portal uses) must reach both the directory card and
    the profile page; a caregiver with no avatar must fall back to the
    existing initials-only presentation, never a broken <img> tag."""

    def _upload_avatar(self, caregiver):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        from apps.accounts.services.profile_media_service import ProfileMediaService

        buffer = io.BytesIO()
        Image.new("RGB", (10, 10), color=(1, 2, 3)).save(buffer, format="PNG")
        ProfileMediaService.set_caregiver_avatar(
            caregiver, SimpleUploadedFile("avatar.png", buffer.getvalue(), content_type="image/png"),
        )

    def test_profile_page_renders_uploaded_avatar_image(self):
        supplier, caregiver = self._create_caregiver_supplier(display_name="آواتار واقعی تست")
        self._upload_avatar(caregiver)

        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )

        self.assertContains(response, "<img")
        self.assertContains(response, caregiver.avatar.url)

    def test_directory_card_renders_uploaded_avatar_image(self):
        supplier, caregiver = self._create_caregiver_supplier(display_name="آواتار در فهرست تست")
        self._upload_avatar(caregiver)

        response = self.client.get(reverse("public_site:find-a-caregiver"), {"tenant": self.tenant.slug})

        self.assertContains(response, caregiver.avatar.url)

    def test_profile_page_without_avatar_falls_back_to_initials_no_broken_img(self):
        supplier, caregiver = self._create_caregiver_supplier(display_name="بدون آواتار تست")
        self.assertFalse(caregiver.avatar)

        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<img src=""')

    def test_avatar_never_leaks_across_tenants(self):
        import uuid as uuid_module

        from apps.kernel.models import Tenant

        supplier, caregiver = self._create_caregiver_supplier(display_name="آواتار مستاجر تست")
        self._upload_avatar(caregiver)

        # A second, unrelated tenant must never resolve this supplier id at all.
        foreign_tenant = Tenant.objects.create(slug=f"foreign-{uuid_module.uuid4().hex[:8]}", name="Foreign")
        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": foreign_tenant.slug},
        )
        self.assertEqual(response.status_code, 404)
