"""Tests for apps.public_site.services.tenant_context.resolve_public_tenant()
— the canonical "which tenant does an anonymous visitor see" resolver
used by every public view (home, both directories, both detail pages)
and the public_tenant_context context processor that feeds shared
navigation chrome (base_public.html's desktop/mobile nav and footer).

Root cause this closes: PR #19/PR #20 (FR-015/FR-016) fixed tenant
*resolution* and *link propagation* for an explicit ?tenant=<slug> hint
on the two directories, but home() never resolved any tenant context at
all (always the platform default tenant, unconditionally), and there was
no way for a deployment to serve a *different* tenant (e.g. a local dev
environment's seed_product_walkthrough demo tenant) as its public site
without every visitor manually typing ?tenant=<slug> on every single
link. These tests prove: (1) settings.PUBLIC_SITE_TENANT_SLUG, when
configured, makes the entire public site — home, both directories, both
detail pages, and every nav/search/pagination/reset link — resolve to
that tenant with zero explicit hint required; (2) an explicit ?tenant=
hint still overrides it; (3) an unknown explicit hint still 404s; (4) a
misconfigured setting fails loudly (ImproperlyConfigured), never
silently; (5) leaving the setting unset is 100% behavior-identical to
every pre-existing test in this suite (the regression guard here is
test_unset_setting_still_uses_platform_default_unchanged); (6) tenant
isolation holds through the configured path exactly as it does through
the explicit-hint path."""

import html as html_lib
import importlib.util
import re
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.kernel.dev_tenant import CANONICAL_DEV_TENANT_SLUG
from apps.kernel.models import Tenant

from .helpers import PublicSiteTestCase


def _tenant_param(url):
    """`url` comes straight out of a rendered href="..." attribute, so a
    query string with more than one param is HTML-entity-escaped
    (`&amp;`, not `&`) exactly like any browser expects — unescape
    before parsing, or a param after the first `&` silently parses under
    the wrong key ("amp;tenant" instead of "tenant")."""
    return parse_qs(urlparse(html_lib.unescape(url)).query).get("tenant", [None])[0]


def _hrefs_matching(page_html, path_prefix):
    return re.findall(rf'href="({re.escape(path_prefix)}[^"]*)"', page_html)


def _caregiver_card_hrefs(page_html):
    """Only real caregiver-detail card links (/find-a-caregiver/<uuid>/...)
    — excludes the bare nav link, the category directory links
    (/find-a-caregiver/?service=...), and the reset link
    (/find-a-caregiver/?...), which all share the same path prefix but
    are not caregiver cards. Mirrors the FR-016 test suite's own
    precision fix for exactly this class of false positive."""
    return [
        h for h in _hrefs_matching(page_html, "/find-a-caregiver/") if re.match(r"^/find-a-caregiver/[0-9a-f-]{36}/", h)
    ]


class PublicSiteCanonicalTenantResolutionTest(PublicSiteTestCase):
    """self.tenant (from PublicSiteTestCase.setUp) is a fresh, isolated,
    non-default tenant — used here as "the configured public site
    tenant" via override_settings(PUBLIC_SITE_TENANT_SLUG=...), exactly
    mirroring how the other *TenantHintTest classes use it as the
    explicit-hint target."""

    def test_homepage_featured_caregivers_use_configured_public_tenant_with_no_hint(self):
        self._create_caregiver_supplier(display_name="مراقب برگزیده پیکربندی‌شده")

        with override_settings(PUBLIC_SITE_TENANT_SLUG=self.tenant.slug):
            response = self.client.get(reverse("public_site:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "مراقب برگزیده پیکربندی‌شده")

    def test_find_a_caregiver_uses_configured_public_tenant_with_no_hint(self):
        self._create_caregiver_supplier(display_name="مراقب دایرکتوری پیکربندی‌شده")

        with override_settings(PUBLIC_SITE_TENANT_SLUG=self.tenant.slug):
            response = self.client.get(reverse("public_site:find-a-caregiver"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "مراقب دایرکتوری پیکربندی‌شده")

    def test_find_an_organization_uses_configured_public_tenant_with_no_hint(self):
        self._create_organization_supplier(name="سازمان دایرکتوری پیکربندی‌شده")

        with override_settings(PUBLIC_SITE_TENANT_SLUG=self.tenant.slug):
            response = self.client.get(reverse("public_site:organization-directory"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "سازمان دایرکتوری پیکربندی‌شده")

    def test_caregiver_profile_detail_uses_configured_public_tenant_with_no_hint(self):
        supplier, _ = self._create_caregiver_supplier(display_name="پروفایل مراقب پیکربندی‌شده")

        with override_settings(PUBLIC_SITE_TENANT_SLUG=self.tenant.slug):
            response = self.client.get(reverse("public_site:caregiver-profile", args=[supplier.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "پروفایل مراقب پیکربندی‌شده")

    def test_organization_profile_detail_uses_configured_public_tenant_with_no_hint(self):
        supplier, _ = self._create_organization_supplier(name="پروفایل سازمان پیکربندی‌شده")

        with override_settings(PUBLIC_SITE_TENANT_SLUG=self.tenant.slug):
            response = self.client.get(reverse("public_site:organization-profile", args=[supplier.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "پروفایل سازمان پیکربندی‌شده")

    def test_homepage_nav_links_carry_configured_public_tenant(self):
        with override_settings(PUBLIC_SITE_TENANT_SLUG=self.tenant.slug):
            response = self.client.get(reverse("public_site:home"))

        html = response.content.decode()
        caregiver_nav_hrefs = _hrefs_matching(html, "/find-a-caregiver/")
        organization_nav_hrefs = _hrefs_matching(html, "/find-an-organization/")
        self.assertTrue(caregiver_nav_hrefs)
        self.assertTrue(organization_nav_hrefs)
        for href in caregiver_nav_hrefs + organization_nav_hrefs:
            self.assertEqual(
                _tenant_param(href),
                self.tenant.slug,
                f"nav link {href!r} lost the configured tenant context",
            )

    def test_directory_page_nav_links_carry_configured_public_tenant(self):
        """The same shared nav chrome renders on every public_site page,
        not only the homepage — proves the context processor, not just
        the home() view, threads the resolved tenant through."""
        with override_settings(PUBLIC_SITE_TENANT_SLUG=self.tenant.slug):
            response = self.client.get(reverse("public_site:find-a-caregiver"))

        html = response.content.decode()
        organization_nav_hrefs = _hrefs_matching(html, "/find-an-organization/")
        self.assertTrue(organization_nav_hrefs)
        for href in organization_nav_hrefs:
            self.assertEqual(_tenant_param(href), self.tenant.slug)

    def test_homepage_featured_caregiver_card_link_resolves_without_manual_hint(self):
        self._create_caregiver_supplier(display_name="مراقب کارت خانه پیکربندی‌شده")

        with override_settings(PUBLIC_SITE_TENANT_SLUG=self.tenant.slug):
            response = self.client.get(reverse("public_site:home"))
            html = response.content.decode()
            card_hrefs = _caregiver_card_hrefs(html)
            self.assertTrue(card_hrefs, "no featured caregiver card link rendered on the homepage")

            for href in card_hrefs:
                self.assertEqual(_tenant_param(href), self.tenant.slug)
                followed = self.client.get(href)
                self.assertEqual(followed.status_code, 200, f"following {href!r} did not resolve")

    def test_homepage_search_form_hidden_field_carries_configured_public_tenant(self):
        with override_settings(PUBLIC_SITE_TENANT_SLUG=self.tenant.slug):
            response = self.client.get(reverse("public_site:home"))

        self.assertContains(response, f'name="tenant" value="{self.tenant.slug}"')

    def test_caregiver_pagination_and_reset_carry_configured_public_tenant(self):
        for i in range(13):  # PAGE_SIZE=12 — forces a second page
            self._create_caregiver_supplier(display_name=f"مراقب صفحه‌بندی پیکربندی {i}")

        with override_settings(PUBLIC_SITE_TENANT_SLUG=self.tenant.slug):
            response = self.client.get(reverse("public_site:find-a-caregiver"))
            html = response.content.decode()
            pagination_hrefs = _hrefs_matching(html, "/find-a-caregiver/?")
            self.assertTrue(pagination_hrefs, "expected pagination links with PAGE_SIZE=12 and 13 results")
            for href in pagination_hrefs:
                self.assertEqual(_tenant_param(href), self.tenant.slug)
                # Rendered href carries HTML-entity-escaped "&amp;" between
                # params (tenant + page) — unescape before following, or
                # the test client sees a bogus "amp;page" param instead of
                # "page" and silently exercises page 1 instead of the
                # actual linked page.
                followed = self.client.get(html_lib.unescape(href))
                self.assertEqual(followed.status_code, 200)

            empty_response = self.client.get(reverse("public_site:find-a-caregiver"), {"city": "no-such-city"})
            reset_hrefs = _hrefs_matching(empty_response.content.decode(), "/find-a-caregiver/?")
            self.assertTrue(reset_hrefs)
            self.assertEqual(_tenant_param(reset_hrefs[0]), self.tenant.slug)

    def test_explicit_hint_overrides_configured_public_tenant(self):
        self._create_caregiver_supplier(display_name="مراقب سایه‌شده توسط هینت صریح")
        other_tenant = Tenant.objects.create(slug=f"other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        with override_settings(PUBLIC_SITE_TENANT_SLUG=self.tenant.slug):
            response = self.client.get(reverse("public_site:find-a-caregiver"), {"tenant": other_tenant.slug})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "مراقب سایه‌شده توسط هینت صریح")

    def test_unknown_explicit_hint_still_404s_even_with_configured_public_tenant(self):
        with override_settings(PUBLIC_SITE_TENANT_SLUG=self.tenant.slug):
            response = self.client.get(reverse("public_site:find-a-caregiver"), {"tenant": "no-such-tenant-slug"})

        self.assertEqual(response.status_code, 404)

    def test_misconfigured_public_tenant_slug_fails_loudly_not_silently(self):
        """A typo'd PUBLIC_SITE_TENANT_SLUG must never silently fall back
        to the platform default — that would quietly serve the wrong
        tenant's data to every visitor with no indication anything is
        wrong. It must fail visibly instead."""
        with override_settings(PUBLIC_SITE_TENANT_SLUG="no-such-tenant-slug"):
            with self.assertRaises(ImproperlyConfigured):
                self.client.get(reverse("public_site:home"))

    def test_unset_setting_still_uses_platform_default_unchanged(self):
        """PUBLIC_SITE_TENANT_SLUG is unset in the test settings module —
        this is the explicit regression guard for every pre-existing test
        in this file/suite, which all rely on exactly this behavior."""
        self._create_caregiver_supplier(display_name="نباید دیده شود بدون هینت یا پیکربندی")

        response = self.client.get(reverse("public_site:home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "نباید دیده شود بدون هینت یا پیکربندی")
        self.assertNotIn("?tenant=", response.content.decode())

    def test_configured_public_tenant_still_excludes_other_tenants_suppliers(self):
        """Isolation must hold through the configured-tenant path exactly
        as it does through the explicit-hint path: configuring
        PUBLIC_SITE_TENANT_SLUG to one tenant must never surface a
        different tenant's data."""
        self._create_caregiver_supplier(display_name="نباید نشت کند از تنانت دیگر")
        other_tenant = Tenant.objects.create(slug=f"other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        with override_settings(PUBLIC_SITE_TENANT_SLUG=other_tenant.slug):
            response = self.client.get(reverse("public_site:home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "نباید نشت کند از تنانت دیگر")


class DebugOnlyCanonicalDevTenantAutoResolutionTest(PublicSiteTestCase):
    """FR-019 corrective review: the canonical public URL
    (/find-a-caregiver/) must show seed_product_walkthrough's realistic
    demo caregivers with zero ?tenant= hint and zero manual
    PUBLIC_SITE_TENANT_SLUG configuration — relying on operator-facing
    documentation alone (the seed command printing setup instructions)
    was rejected as insufficient. This is resolve_public_tenant()'s new
    case 3: a settings.DEBUG-only, best-effort lookup of the exact,
    known apps.kernel.dev_tenant.CANONICAL_DEV_TENANT_SLUG tenant — the
    same literal slug seed_product_walkthrough seeds, imported from the
    one shared module both sides use, so they cannot silently drift
    apart. Never "the first active tenant," never raises when the dev
    tenant hasn't been seeded yet (silently falls through to the
    unchanged platform-default case 4), and structurally unreachable
    when settings.DEBUG is False (hardcoded in both
    config.settings.production and config.settings.testing).

    self.tenant (from PublicSiteTestCase.setUp) is renamed in-place to
    the exact canonical dev slug so every existing fixture helper
    (_create_caregiver_supplier, etc.) keeps working unchanged while
    still exercising the real slug resolve_public_tenant() looks for."""

    def setUp(self):
        super().setUp()
        self.tenant.slug = CANONICAL_DEV_TENANT_SLUG
        self.tenant.save(update_fields=["slug"])

    def test_bare_directory_url_shows_caregivers_with_zero_hint_and_zero_config(self):
        """The literal, primary acceptance requirement: no ?tenant=
        query parameter, no PUBLIC_SITE_TENANT_SLUG override."""
        self._create_caregiver_supplier(display_name="مراقب تنانت توسعه بدون پیکربندی")

        with override_settings(DEBUG=True, PUBLIC_SITE_TENANT_SLUG=None):
            response = self.client.get(reverse("public_site:find-a-caregiver"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "مراقب تنانت توسعه بدون پیکربندی")

    def test_homepage_also_resolves_with_zero_hint_and_zero_config(self):
        self._create_caregiver_supplier(display_name="مراقب برگزیده خانه بدون پیکربندی")

        with override_settings(DEBUG=True, PUBLIC_SITE_TENANT_SLUG=None):
            response = self.client.get(reverse("public_site:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "مراقب برگزیده خانه بدون پیکربندی")

    def test_caregiver_card_link_resolves_to_a_real_profile_with_zero_config(self):
        supplier, _ = self._create_caregiver_supplier(display_name="مراقب کارت بدون پیکربندی")

        with override_settings(DEBUG=True, PUBLIC_SITE_TENANT_SLUG=None):
            directory_response = self.client.get(reverse("public_site:find-a-caregiver"))
            profile_path = reverse("public_site:caregiver-profile", args=[supplier.id])
            self.assertContains(directory_response, profile_path)

            profile_response = self.client.get(profile_path)

        self.assertEqual(profile_response.status_code, 200)
        self.assertContains(profile_response, "مراقب کارت بدون پیکربندی")

    def test_inactive_when_debug_false(self):
        """Case 3 must be structurally unreachable when DEBUG=False —
        the same guarantee production.py and testing.py both already
        hardcode, never environment-driven."""
        self._create_caregiver_supplier(display_name="نباید دیده شود وقتی دیباگ خاموش است")

        with override_settings(DEBUG=False, PUBLIC_SITE_TENANT_SLUG=None):
            response = self.client.get(reverse("public_site:find-a-caregiver"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "نباید دیده شود وقتی دیباگ خاموش است")

    def test_explicit_hint_still_overrides_case_3(self):
        """Case 1 (explicit ?tenant=) still wins over the new case 3,
        unchanged priority order."""
        self._create_caregiver_supplier(display_name="مراقب سایه‌شده توسط هینت روی حالت سوم")
        other_tenant = Tenant.objects.create(slug=f"other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        with override_settings(DEBUG=True, PUBLIC_SITE_TENANT_SLUG=None):
            response = self.client.get(reverse("public_site:find-a-caregiver"), {"tenant": other_tenant.slug})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "مراقب سایه‌شده توسط هینت روی حالت سوم")

    def test_configured_public_site_tenant_slug_still_overrides_case_3(self):
        """Case 2 (settings.PUBLIC_SITE_TENANT_SLUG) still wins over the
        new case 3, unchanged priority order — a deployer's explicit
        choice is never silently replaced by the auto-detected dev
        tenant."""
        self._create_caregiver_supplier(display_name="مراقب سایه‌شده توسط تنظیمات روی حالت سوم")
        other_tenant = Tenant.objects.create(slug=f"other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        with override_settings(DEBUG=True, PUBLIC_SITE_TENANT_SLUG=other_tenant.slug):
            response = self.client.get(reverse("public_site:find-a-caregiver"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "مراقب سایه‌شده توسط تنظیمات روی حالت سوم")

    def test_unknown_explicit_hint_still_404s_even_with_debug_true_and_dev_tenant_present(self):
        """Case 1's strict validation is never bypassed by case 3's
        existence — an unknown hint must still 404, never silently fall
        through to the auto-detected dev tenant."""
        with override_settings(DEBUG=True, PUBLIC_SITE_TENANT_SLUG=None):
            response = self.client.get(reverse("public_site:find-a-caregiver"), {"tenant": "no-such-tenant-slug"})

        self.assertEqual(response.status_code, 404)

    def test_case_3_excludes_other_tenants_suppliers(self):
        """Isolation holds through the auto-detected case-3 path exactly
        as it does through every other resolution path."""
        self._create_caregiver_supplier(display_name="نباید نشت کند از تنانت دیگر روی حالت سوم")
        other_tenant = Tenant.objects.create(slug=f"other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        with override_settings(DEBUG=True, PUBLIC_SITE_TENANT_SLUG=None):
            response = self.client.get(reverse("public_site:find-a-caregiver"), {"tenant": other_tenant.slug})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "نباید نشت کند از تنانت دیگر روی حالت سوم")

    def test_falls_through_silently_when_no_dev_tenant_slug_exists(self):
        """The ordinary state for every test database and every
        deployment that hasn't run seed_product_walkthrough yet: no
        tenant with the canonical dev slug exists at all. Case 3 must
        never raise — it silently falls through to the unchanged
        platform-default case 4."""
        self.tenant.slug = f"not-the-dev-slug-{uuid.uuid4().hex[:8]}"
        self.tenant.save(update_fields=["slug"])
        self._create_caregiver_supplier(display_name="نباید دیده شود بدون تنانت توسعه")

        with override_settings(DEBUG=True, PUBLIC_SITE_TENANT_SLUG=None):
            response = self.client.get(reverse("public_site:find-a-caregiver"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "نباید دیده شود بدون تنانت توسعه")


class ProductionSettingsNeverAutoResolveDevTenantTest(TestCase):
    """FR-019 corrective review: proves, from the actual shipped source
    text (never by importing/executing config.settings.production,
    which requires a real SECRET_KEY environment variable this test
    environment may not have), that DEBUG is a hardcoded literal False
    in production — never environment-driven, so case 3 is structurally
    unreachable in production regardless of any local .env content."""

    def test_production_settings_hardcode_debug_false(self):
        spec = importlib.util.find_spec("config.settings.production")
        source = Path(spec.origin).read_text(encoding="utf-8")

        self.assertIn("DEBUG = False", source)
        self.assertNotIn("DEBUG = os.environ", source)

    def test_testing_settings_also_hardcode_debug_false(self):
        spec = importlib.util.find_spec("config.settings.testing")
        source = Path(spec.origin).read_text(encoding="utf-8")

        self.assertIn("DEBUG = False", source)
        self.assertNotIn("DEBUG = os.environ", source)
