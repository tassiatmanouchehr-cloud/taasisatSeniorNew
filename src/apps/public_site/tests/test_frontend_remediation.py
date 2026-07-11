"""Frontend remediation follow-up (post Epic 06 Sprint 2 product walkthrough).

Covers: Hero layering/content contract, public Header/mobile-nav login and
registration exposure, and the removal of dangling font-file references.
"""

from pathlib import Path

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

UI_ROOT = Path(__file__).resolve().parents[3] / "ui"


class HomeHeroContractTest(TestCase):
    """Defect 1 regression guard: the decorative Hero background must span
    the section's actual content height (no fixed h-72 that can end
    mid-content), and must not fight the dark theme's own primary-*
    inversion with a dark: override."""

    def test_home_page_returns_200(self):
        response = self.client.get(reverse("public_site:home"))
        self.assertEqual(response.status_code, 200)

    def test_hero_heading_present_and_in_foreground_container(self):
        response = self.client.get(reverse("public_site:home"))
        self.assertContains(response, "<h1")
        # The <h1> tag itself (not the SEO meta description, which also
        # contains this phrase) must be inside the "relative" (foreground)
        # wrapper, not accidentally left under the "absolute" decorative
        # layer.
        content = response.content.decode()
        hero_relative_idx = content.find('class="relative mx-auto max-w-7xl')
        heading_tag_idx = content.find("<h1")
        self.assertGreater(hero_relative_idx, -1)
        self.assertGreater(heading_tag_idx, hero_relative_idx)
        self.assertIn("مراقبت مطمئن برای سالمند", content[heading_tag_idx : heading_tag_idx + 300])

    def test_decorative_hero_background_spans_full_section_not_fixed_height(self):
        hero_source = (UI_ROOT / "components" / "public" / "hero.html").read_text()
        self.assertIn('class="absolute inset-0 bg-primary-50"', hero_source)
        self.assertNotIn("h-72 bg-primary-50", hero_source)

    def test_decorative_hero_background_does_not_fight_dark_theme_inversion(self):
        """dark.css already inverts the whole primary-* scale, so a
        dark:bg-primary-950 override on this div previously resolved to a
        *pale* color in dark mode (near-white), sitting behind near-white
        heading text. bg-primary-50 alone is correct in both themes.
        Checks the actual div's class attribute, not just absence of the
        substring anywhere in the file (which would also match this
        docstring/an explanatory code comment)."""
        hero_source = (UI_ROOT / "components" / "public" / "hero.html").read_text()
        self.assertIn('class="absolute inset-0 bg-primary-50" aria-hidden="true"', hero_source)

    def test_home_page_hero_has_login_and_register_ctas(self):
        response = self.client.get(reverse("public_site:home"))
        self.assertContains(response, reverse("accounts:login"))
        self.assertContains(response, reverse("accounts:register"))


class PublicHeaderAccountActionsTest(TestCase):
    """Defect 2: desktop Header and mobile navigation must both expose a
    real login route and a real registration entry point that leads to a
    caregiver/organization choice, without removing the existing
    'start request' action."""

    def test_desktop_header_exposes_login_link(self):
        response = self.client.get(reverse("public_site:home"))
        self.assertContains(response, reverse("accounts:login"))
        self.assertContains(response, "ورود")

    def test_desktop_header_exposes_register_link(self):
        response = self.client.get(reverse("public_site:home"))
        self.assertContains(response, reverse("accounts:register"))
        self.assertContains(response, "ثبت‌نام")

    def test_mobile_nav_panel_exposes_login_and_register(self):
        """The mobile drawer is server-rendered in the same response (Alpine
        only toggles visibility client-side), so this asserts on the same
        page load as the desktop check."""
        response = self.client.get(reverse("public_site:home"))
        self.assertContains(response, "ورود به حساب")
        self.assertContains(response, "ثبت‌نام (خانواده، مراقب یا سازمان)")

    def test_start_request_cta_still_present(self):
        response = self.client.get(reverse("public_site:home"))
        self.assertContains(response, "شروع درخواست")

    def test_register_entry_leads_to_caregiver_and_organization_choice(self):
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("accounts:register-caregiver"))
        self.assertContains(response, reverse("accounts:register-company"))
        self.assertContains(response, reverse("accounts:register-customer"))

    def test_all_new_header_routes_resolve_without_404(self):
        for name in (
            "accounts:login",
            "accounts:register",
            "accounts:register-customer",
            "accounts:register-caregiver",
            "accounts:register-company",
        ):
            with self.subTest(route=name):
                response = self.client.get(reverse(name))
                self.assertNotEqual(response.status_code, 404)


class MissingFontAssetsTest(SimpleTestCase):
    """Defect 3: the browser must no longer request nonexistent font files,
    and no proprietary/unlicensed binary was added to satisfy this."""

    def test_no_unresolved_font_face_src_for_iransansx_or_vazirmatn(self):
        """Checks for an actual CSS url() reference, not just the bare
        path string — the file may still mention the path in an
        explanatory comment describing how to add the font back later."""
        typography_source = (UI_ROOT / "css" / "typography.css").read_text()
        self.assertNotIn("url('../fonts/iransansx/IRANSansX-Variable.woff2')", typography_source)
        self.assertNotIn("url('../fonts/vazirmatn/Vazirmatn-Variable.woff2')", typography_source)

    def test_no_font_binaries_were_added(self):
        fonts_dir = UI_ROOT / "fonts"
        binary_extensions = {".woff2", ".woff", ".ttf", ".otf"}
        found = [p for p in fonts_dir.rglob("*") if p.suffix.lower() in binary_extensions]
        self.assertEqual(found, [], f"Unexpected font binaries committed: {found}")


class MissingFontAssetsHttpTest(TestCase):
    """HTTP-level companion to MissingFontAssetsTest — needs DB access for
    the home view's tenant resolution, so it can't be a SimpleTestCase."""

    def test_home_page_never_requests_the_missing_font_files(self):
        response = self.client.get(reverse("public_site:home"))
        content = response.content.decode()
        self.assertNotIn("iransansx/IRANSansX-Variable.woff2", content)
        self.assertNotIn("vazirmatn/Vazirmatn-Variable.woff2", content)
