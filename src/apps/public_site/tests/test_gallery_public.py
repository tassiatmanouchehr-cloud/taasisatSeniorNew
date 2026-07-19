"""Public caregiver gallery — Sprint 2.2 (Caregiver Professional Profile:
Gallery and Media Portfolio). Reuses the canonical public-visibility
policy (BG-022, apps.public_site.services.common.is_publicly_visible())
rather than introducing a second one — see profile_service.py's
_gallery()."""

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.accounts.services.caregiver_gallery_service import CaregiverGalleryService

from ..services.profile_service import CaregiverPublicProfileService
from .helpers import PublicSiteTestCase


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (1, 1), color=(0, 0, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


_PNG_BYTES = _png_bytes()


def _image_file(name="photo.png") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, _PNG_BYTES, content_type="image/png")


class PublicGalleryVisibilityTest(PublicSiteTestCase):
    def test_visible_item_appears_on_public_profile(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        CaregiverGalleryService.add_item(caregiver, image=_image_file(), caption="نمونه کار")
        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertEqual(len(profile.gallery), 1)
        self.assertEqual(profile.gallery[0].caption, "نمونه کار")

    def test_hidden_item_does_not_appear(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        item = CaregiverGalleryService.add_item(caregiver, image=_image_file())
        CaregiverGalleryService.update_item(caregiver, item_id=item.id, is_visible=False)
        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertEqual(profile.gallery, ())

    def test_removed_item_does_not_appear(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        item = CaregiverGalleryService.add_item(caregiver, image=_image_file())
        CaregiverGalleryService.remove_item(caregiver, item_id=item.id)
        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertEqual(profile.gallery, ())

    def test_draft_caregiver_profile_exposes_no_gallery(self):
        supplier, caregiver = self._create_caregiver_supplier(
            verification_status="verified", profile_status="draft",
        )
        CaregiverGalleryService.add_item(caregiver, image=_image_file())
        self.assertIsNone(CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))

    def test_suspended_caregiver_profile_exposes_no_gallery(self):
        supplier, caregiver = self._create_caregiver_supplier(
            verification_status="verified", profile_status="suspended",
        )
        CaregiverGalleryService.add_item(caregiver, image=_image_file())
        self.assertIsNone(CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))

    def test_unverified_caregiver_profile_exposes_no_gallery(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="unverified")
        CaregiverGalleryService.add_item(caregiver, image=_image_file())
        self.assertIsNone(CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id))

    def test_hidden_caregiver_profile_gallery_absent_from_html(self):
        supplier, caregiver = self._create_caregiver_supplier(
            verification_status="verified", profile_status="draft",
        )
        item = CaregiverGalleryService.add_item(caregiver, image=_image_file(), caption="خصوصی")
        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, "خصوصی", status_code=404)
        self.assertNotContains(response, item.image.name, status_code=404)

    def test_public_page_never_leaks_storage_path(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        CaregiverGalleryService.add_item(caregiver, image=_image_file())
        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        self.assertNotContains(response, "MEDIA_ROOT")
        # The served URL is the storage's public URL (media/...), never a
        # raw filesystem path — confirmed by the absence of the private/
        # verification-document convention, which this model never uses.
        self.assertNotContains(response, "private/")

    def test_caption_rendered_safely(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        CaregiverGalleryService.add_item(caregiver, image=_image_file(), caption="<script>alert(1)</script>")
        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")

    def test_another_caregivers_gallery_never_appears(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        _, other_caregiver = self._create_caregiver_supplier(
            display_name="مراقب دیگر", verification_status="verified",
        )
        CaregiverGalleryService.add_item(other_caregiver, image=_image_file(), caption="متعلق به دیگری")
        profile = CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)
        self.assertEqual(profile.gallery, ())


class PublicGalleryQueryCountTest(PublicSiteTestCase):
    def test_gallery_resolution_is_a_single_bounded_query(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        for i in range(5):
            CaregiverGalleryService.add_item(caregiver, image=_image_file(f"photo-{i}.png"))

        # 15, not 14: Sprint 2.4 added one fixed-cost query
        # (AvailabilityQueryService.get_distinct_active_days(), via
        # _schedule_summary()) — independent of gallery item count, so this
        # remains a single bounded query regardless of how many items exist.
        with self.assertNumQueries(15):
            CaregiverPublicProfileService.get_profile(supplier.id, tenant_id=self.tenant.id)


class PublicGalleryOrderingTest(PublicSiteTestCase):
    """Phase 6 (Public Caregiver Marketplace Remediation): gallery order
    must be deterministic end-to-end through the public profile page, not
    just guaranteed by the model's own Meta.ordering in isolation."""

    def test_gallery_items_render_in_display_order_on_the_public_page(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        third = CaregiverGalleryService.add_item(caregiver, image=_image_file("c.png"), caption="سوم")
        first = CaregiverGalleryService.add_item(caregiver, image=_image_file("a.png"), caption="اول")
        second = CaregiverGalleryService.add_item(caregiver, image=_image_file("b.png"), caption="دوم")
        CaregiverGalleryService.reorder(
            caregiver, ordered_item_ids=[first.id, second.id, third.id],
        )

        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )
        html = response.content.decode()

        self.assertLess(html.index("اول"), html.index("دوم"))
        self.assertLess(html.index("دوم"), html.index("سوم"))


class PublicGalleryPresentationTest(PublicSiteTestCase):
    """Phase 4 (Public Caregiver Marketplace Remediation): the gallery
    grid and its lightbox — accessible, Alpine.js-only (no new
    dependency), never a raw filesystem path, always meaningful alt
    text."""

    def test_gallery_grid_uses_responsive_column_classes(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        CaregiverGalleryService.add_item(caregiver, image=_image_file(), caption="نمونه")

        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )

        self.assertContains(response, "sm:grid-cols-2")
        self.assertContains(response, "lg:grid-cols-3")

    def test_gallery_thumbnail_is_keyboard_and_screen_reader_accessible(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        CaregiverGalleryService.add_item(caregiver, image=_image_file(), caption="قابل دسترس")

        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )

        self.assertContains(response, "<button")
        self.assertContains(response, 'aria-label="بزرگ‌نمایی تصویر گالری: قابل دسترس"')

    def test_lightbox_overlay_is_a_real_dialog_with_escape_and_close(self):
        supplier, caregiver = self._create_caregiver_supplier(verification_status="verified")
        CaregiverGalleryService.add_item(caregiver, image=_image_file())

        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )

        self.assertContains(response, 'role="dialog"')
        self.assertContains(response, 'aria-modal="true"')
        self.assertContains(response, "@keydown.escape.window")

    def test_no_gallery_section_rendered_when_caregiver_has_no_items(self):
        supplier, _caregiver = self._create_caregiver_supplier(verification_status="verified")

        response = self.client.get(
            reverse("public_site:caregiver-profile", args=[supplier.id]), {"tenant": self.tenant.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "گالری تصاویر")
