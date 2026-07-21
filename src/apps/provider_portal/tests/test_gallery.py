"""Gallery management — Sprint 2.2 (Caregiver Professional Profile:
Gallery and Media Portfolio). Service-layer tests live in
apps.accounts.tests.test_caregiver_gallery."""

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.accounts.models.profiles import CaregiverProfile
from apps.accounts.services.caregiver_gallery_service import CaregiverGalleryService

from .helpers import ProviderPortalTestCase


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (1, 1), color=(0, 255, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


_PNG_BYTES = _png_bytes()


def _image_file(name="photo.png") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, _PNG_BYTES, content_type="image/png")


class GalleryUploadTest(ProviderPortalTestCase):
    def test_owner_can_upload_gallery_photo(self):
        self.login_as_provider()
        response = self.client.post(
            reverse("provider_portal:profile-gallery"),
            {"image": _image_file(), "caption": "در حال کار"},
        )
        self.assertEqual(response.status_code, 302)
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        self.assertEqual(caregiver.gallery_items.count(), 1)
        self.assertEqual(caregiver.gallery_items.first().caption, "در حال کار")

    def test_unauthenticated_cannot_upload(self):
        response = self.client.post(reverse("provider_portal:profile-gallery"), {"image": _image_file()})
        self.assertEqual(response.status_code, 403)

    def test_customer_cannot_upload(self):
        self.client.force_login(self.customer.user)
        response = self.client.post(reverse("provider_portal:profile-gallery"), {"image": _image_file()})
        self.assertEqual(response.status_code, 403)

    def test_non_image_file_shows_form_error(self):
        self.login_as_provider()
        bad_file = SimpleUploadedFile("bad.png", b"not an image", content_type="image/png")
        response = self.client.post(reverse("provider_portal:profile-gallery"), {"image": bad_file})
        self.assertEqual(response.status_code, 200)
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        self.assertEqual(caregiver.gallery_items.count(), 0)

    def test_gallery_limit_shows_error(self):
        self.login_as_provider()
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        from apps.accounts.services.caregiver_gallery_service import MAX_GALLERY_ITEMS_PER_CAREGIVER

        for _ in range(MAX_GALLERY_ITEMS_PER_CAREGIVER):
            CaregiverGalleryService.add_item(caregiver, image=_image_file())
        response = self.client.post(reverse("provider_portal:profile-gallery"), {"image": _image_file()})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "حداکثر تعداد تصاویر مجاز")
        self.assertEqual(caregiver.gallery_items.count(), MAX_GALLERY_ITEMS_PER_CAREGIVER)


class GalleryEditTest(ProviderPortalTestCase):
    def test_owner_can_edit_own_item(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        item = CaregiverGalleryService.add_item(caregiver, image=_image_file())
        self.login_as_provider()
        response = self.client.post(
            reverse("provider_portal:profile-gallery-item-edit", kwargs={"item_id": item.id}),
            {"caption": "جدید", "alt_text": "توضیح", "is_visible": ""},
        )
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.caption, "جدید")
        self.assertFalse(item.is_visible)

    def test_another_caregiver_cannot_edit(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        item = CaregiverGalleryService.add_item(caregiver, image=_image_file())
        self.client.force_login(self.other_provider_user)
        response = self.client.post(
            reverse("provider_portal:profile-gallery-item-edit", kwargs={"item_id": item.id}),
            {"caption": "Hacked"},
        )
        self.assertEqual(response.status_code, 404)
        item.refresh_from_db()
        self.assertEqual(item.caption, "")

    def test_cross_tenant_cannot_edit(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        item = CaregiverGalleryService.add_item(caregiver, image=_image_file())
        self.client.force_login(self.other_tenant_provider_user)
        response = self.client.post(
            reverse("provider_portal:profile-gallery-item-edit", kwargs={"item_id": item.id}),
            {"caption": "Hacked"},
        )
        self.assertEqual(response.status_code, 404)
        item.refresh_from_db()
        self.assertEqual(item.caption, "")


class GalleryRemoveTest(ProviderPortalTestCase):
    def test_owner_can_remove_own_item(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        item = CaregiverGalleryService.add_item(caregiver, image=_image_file())
        self.login_as_provider()
        response = self.client.post(
            reverse("provider_portal:profile-gallery-item-remove", kwargs={"item_id": item.id}),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(caregiver.gallery_items.count(), 0)

    def test_another_caregiver_cannot_remove(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        item = CaregiverGalleryService.add_item(caregiver, image=_image_file())
        self.client.force_login(self.other_provider_user)
        self.client.post(reverse("provider_portal:profile-gallery-item-remove", kwargs={"item_id": item.id}))
        self.assertEqual(caregiver.gallery_items.count(), 1)


class GalleryReorderTest(ProviderPortalTestCase):
    def test_owner_can_move_item_up(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        first = CaregiverGalleryService.add_item(caregiver, image=_image_file())
        second = CaregiverGalleryService.add_item(caregiver, image=_image_file())
        self.login_as_provider()
        response = self.client.post(
            reverse("provider_portal:profile-gallery-item-move", kwargs={"item_id": second.id, "direction": "up"}),
        )
        self.assertEqual(response.status_code, 302)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(second.display_order, 0)
        self.assertEqual(first.display_order, 1)

    def test_another_caregiver_cannot_reorder_items_they_do_not_own(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        first = CaregiverGalleryService.add_item(caregiver, image=_image_file())
        second = CaregiverGalleryService.add_item(caregiver, image=_image_file())
        self.client.force_login(self.other_provider_user)
        self.client.post(
            reverse("provider_portal:profile-gallery-item-move", kwargs={"item_id": second.id, "direction": "up"}),
        )
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.display_order, 0)
        self.assertEqual(second.display_order, 1)


class ProfilePageGalleryPreviewTest(ProviderPortalTestCase):
    def test_profile_page_shows_gallery_count(self):
        caregiver = CaregiverProfile.objects.get(user=self.provider_user)
        CaregiverGalleryService.add_item(caregiver, image=_image_file())
        self.login_as_provider()
        response = self.client.get(reverse("provider_portal:profile"))
        self.assertContains(response, "1 / 12")
