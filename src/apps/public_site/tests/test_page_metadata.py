"""Tests for FR-018 (Public Site Coherence Remediation) page-metadata
fixes: PSA-001 (page-title brand suffix), PSA-002 (favicon), and the
related Open Graph/social-link polish items.

Root cause traced during the audit: ui/layouts/base.html's title_suffix
block was hard-coded to the generic word "پلتفرم" ("Platform") instead
of the actual brand "سالمندیار", and ui/components/public/seo_meta.html
appended a *second* " | سالمندیار" on top of every caller's page_title
(every public template already embeds the brand in its own page_title
argument), producing a doubled brand in og:title/twitter:title on every
single public page."""

from urllib.parse import urlparse

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from .helpers import PublicSiteTestCase


class PageTitleBrandingTest(TestCase):
    def _title(self, response):
        html = response.content.decode()
        start = html.index("<title>") + len("<title>")
        end = html.index("</title>")
        return html[start:end]

    def test_homepage_title_uses_brand(self):
        response = self.client.get(reverse("public_site:home"))
        title = self._title(response)

        self.assertTrue(title.endswith("سالمندیار"), title)
        self.assertNotIn("پلتفرم", title)

    def test_caregiver_directory_title_uses_brand(self):
        response = self.client.get(reverse("public_site:find-a-caregiver"))
        title = self._title(response)

        self.assertTrue(title.endswith("سالمندیار"), title)
        self.assertNotIn("پلتفرم", title)

    def test_organization_directory_title_uses_brand(self):
        response = self.client.get(reverse("public_site:organization-directory"))
        title = self._title(response)

        self.assertTrue(title.endswith("سالمندیار"), title)
        self.assertNotIn("پلتفرم", title)

    def test_contact_page_title_uses_brand(self):
        response = self.client.get(reverse("public_site:contact"))
        title = self._title(response)

        self.assertTrue(title.endswith("سالمندیار"), title)
        self.assertNotIn("پلتفرم", title)


class CaregiverProfileTitleTest(PublicSiteTestCase):
    def test_caregiver_profile_title_uses_brand_exactly_once(self):
        supplier, _ = self._create_caregiver_supplier(display_name="مینا رستمی متادیتا")

        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]),
            {"tenant": self.tenant.slug},
        )
        html = response.content.decode()
        title = html[html.index("<title>") + 7 : html.index("</title>")]

        self.assertEqual(title, "مینا رستمی متادیتا | سالمندیار")
        self.assertEqual(title.count("سالمندیار"), 1)


class OpenGraphMetadataTest(TestCase):
    def test_og_title_and_twitter_title_are_not_duplicated(self):
        response = self.client.get(reverse("public_site:home"))
        html = response.content.decode()

        og_title_start = html.index('property="og:title" content="') + len('property="og:title" content="')
        og_title = html[og_title_start : html.index('"', og_title_start)]
        self.assertEqual(og_title.count("سالمندیار"), 1, og_title)

        twitter_title_start = html.index('name="twitter:title" content="') + len('name="twitter:title" content="')
        twitter_title = html[twitter_title_start : html.index('"', twitter_title_start)]
        self.assertEqual(twitter_title.count("سالمندیار"), 1, twitter_title)

    def test_og_url_is_absolute(self):
        response = self.client.get(reverse("public_site:home"))
        html = response.content.decode()

        og_url_start = html.index('property="og:url" content="') + len('property="og:url" content="')
        og_url = html[og_url_start : html.index('"', og_url_start)]
        parsed = urlparse(og_url)

        self.assertTrue(parsed.scheme, og_url)
        self.assertTrue(parsed.netloc, og_url)

    def test_canonical_and_og_url_agree(self):
        response = self.client.get(reverse("public_site:home"))
        html = response.content.decode()

        canonical_start = html.index('rel="canonical" href="') + len('rel="canonical" href="')
        canonical_url = html[canonical_start : html.index('"', canonical_start)]

        og_url_start = html.index('property="og:url" content="') + len('property="og:url" content="')
        og_url = html[og_url_start : html.index('"', og_url_start)]

        self.assertEqual(canonical_url, og_url)


class FaviconTest(TestCase):
    def test_homepage_declares_favicon_link(self):
        response = self.client.get(reverse("public_site:home"))
        self.assertContains(response, '<link rel="icon"')
        self.assertContains(response, "/static/favicon.svg")

    def test_favicon_resolves_via_static_handling(self):
        """The test client doesn't go through runserver's DEBUG-only
        static-file WSGI wrapper (confirmed by direct request: an
        otherwise-real static asset like output.css also 404s under
        self.client in this test environment), so this asserts what
        actually matters — django.contrib.staticfiles' own resolution
        machinery (STATICFILES_DIRS/finders, the same mechanism
        `{% static %}`/runserver ultimately both rely on) locates the
        file — rather than a live HTTP round-trip through a serving path
        this environment doesn't exercise in tests."""
        resolved_path = finders.find("favicon.svg")
        self.assertIsNotNone(resolved_path, "favicon.svg was not found by any STATICFILES_DIRS finder")


class NoPlaceholderInteractiveLinksTest(TestCase):
    def test_homepage_has_no_href_hash_anchor(self):
        response = self.client.get(reverse("public_site:home"))
        self.assertNotContains(response, 'href="#"')

    def test_no_internal_build_comment_shipped(self):
        response = self.client.get(reverse("public_site:home"))
        self.assertNotContains(response, "npm run build")
