"""CaregiverGalleryService — Sprint 2.2 (Caregiver Professional Profile:
Gallery and Media Portfolio)."""

import io
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from apps.accounts.models.gallery import CaregiverGalleryItem
from apps.accounts.models.profiles import CaregiverProfile
from apps.accounts.services.caregiver_gallery_service import (
    MAX_GALLERY_ITEMS_PER_CAREGIVER,
    CaregiverGalleryService,
)
from apps.accounts.services.errors import AccountsError
from apps.kernel.models import Person, Tenant, UserAccount


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (1, 1), color=(255, 0, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


_PNG_BYTES = _png_bytes()
NON_IMAGE_BYTES = b"not an image at all"


def _image_file(name="photo.png") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, _PNG_BYTES, content_type="image/png")


class _FixtureMixin:
    def _build_fixture(self):
        self.tenant = Tenant.objects.create(slug=f"gallery-{uuid.uuid4().hex[:8]}", name="Gallery Tenant")
        self.caregiver = self._create_caregiver(tenant=self.tenant)
        self.other_caregiver = self._create_caregiver(tenant=self.tenant, full_name="Other Caregiver")

    def _create_caregiver(self, *, tenant, full_name="Test Caregiver") -> CaregiverProfile:
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=full_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return CaregiverProfile.objects.create(user=user, person=person, phone=phone, display_name=full_name)


class CaregiverGalleryServiceUploadTest(_FixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_add_item(self):
        item = CaregiverGalleryService.add_item(self.caregiver, image=_image_file(), caption="در حال کار")
        self.assertEqual(item.caregiver_id, self.caregiver.id)
        self.assertEqual(item.caption, "در حال کار")
        self.assertEqual(item.display_order, 0)
        self.assertTrue(item.is_visible)

    def test_second_item_gets_next_display_order(self):
        CaregiverGalleryService.add_item(self.caregiver, image=_image_file())
        second = CaregiverGalleryService.add_item(self.caregiver, image=_image_file())
        self.assertEqual(second.display_order, 1)

    def test_non_image_file_rejected(self):
        bad_file = SimpleUploadedFile("fake.png", NON_IMAGE_BYTES, content_type="image/png")
        with self.assertRaises(AccountsError):
            CaregiverGalleryService.add_item(self.caregiver, image=bad_file)
        self.assertEqual(CaregiverGalleryItem.objects.filter(caregiver=self.caregiver).count(), 0)

    def test_corrupted_image_rejected(self):
        truncated = SimpleUploadedFile("broken.png", _PNG_BYTES[:8], content_type="image/png")
        with self.assertRaises(AccountsError):
            CaregiverGalleryService.add_item(self.caregiver, image=truncated)

    def test_oversized_image_rejected(self):
        from apps.accounts.services.image_validation import MAX_IMAGE_BYTES

        big = SimpleUploadedFile("big.png", _PNG_BYTES, content_type="image/png")
        big.size = MAX_IMAGE_BYTES + 1
        with self.assertRaises(AccountsError):
            CaregiverGalleryService.add_item(self.caregiver, image=big)

    def test_caption_too_long_refused(self):
        with self.assertRaises(AccountsError):
            CaregiverGalleryService.add_item(self.caregiver, image=_image_file(), caption="x" * 256)

    def test_alt_text_too_long_refused(self):
        with self.assertRaises(AccountsError):
            CaregiverGalleryService.add_item(self.caregiver, image=_image_file(), alt_text="x" * 256)

    def test_gallery_limit_enforced(self):
        for _ in range(MAX_GALLERY_ITEMS_PER_CAREGIVER):
            CaregiverGalleryService.add_item(self.caregiver, image=_image_file())
        with self.assertRaises(AccountsError):
            CaregiverGalleryService.add_item(self.caregiver, image=_image_file())
        self.assertEqual(
            CaregiverGalleryItem.objects.filter(caregiver=self.caregiver).count(),
            MAX_GALLERY_ITEMS_PER_CAREGIVER,
        )

    def test_gallery_limit_is_per_caregiver(self):
        for _ in range(MAX_GALLERY_ITEMS_PER_CAREGIVER):
            CaregiverGalleryService.add_item(self.caregiver, image=_image_file())
        # A different caregiver is unaffected by the first caregiver's cap.
        item = CaregiverGalleryService.add_item(self.other_caregiver, image=_image_file())
        self.assertEqual(item.caregiver_id, self.other_caregiver.id)


class CaregiverGalleryServiceUpdateTest(_FixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_update_item(self):
        item = CaregiverGalleryService.add_item(self.caregiver, image=_image_file())
        updated = CaregiverGalleryService.update_item(
            self.caregiver, item_id=item.id, caption="جدید", alt_text="توضیح", is_visible=False,
        )
        self.assertEqual(updated.caption, "جدید")
        self.assertEqual(updated.alt_text, "توضیح")
        self.assertFalse(updated.is_visible)

    def test_cannot_update_another_caregivers_item(self):
        item = CaregiverGalleryService.add_item(self.other_caregiver, image=_image_file())
        with self.assertRaises(AccountsError):
            CaregiverGalleryService.update_item(self.caregiver, item_id=item.id, caption="Hacked")
        item.refresh_from_db()
        self.assertEqual(item.caption, "")

    def test_update_nonexistent_item_refused(self):
        with self.assertRaises(AccountsError):
            CaregiverGalleryService.update_item(self.caregiver, item_id=uuid.uuid4(), caption="x")


class CaregiverGalleryServiceReorderTest(_FixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_reorder_applies_requested_order(self):
        first = CaregiverGalleryService.add_item(self.caregiver, image=_image_file())
        second = CaregiverGalleryService.add_item(self.caregiver, image=_image_file())
        third = CaregiverGalleryService.add_item(self.caregiver, image=_image_file())

        CaregiverGalleryService.reorder(self.caregiver, ordered_item_ids=[third.id, first.id, second.id])

        ordered = list(CaregiverGalleryService.list_items(self.caregiver))
        self.assertEqual([item.id for item in ordered], [third.id, first.id, second.id])

    def test_reorder_with_foreign_item_id_refused(self):
        own = CaregiverGalleryService.add_item(self.caregiver, image=_image_file())
        foreign = CaregiverGalleryService.add_item(self.other_caregiver, image=_image_file())

        with self.assertRaises(AccountsError):
            CaregiverGalleryService.reorder(self.caregiver, ordered_item_ids=[foreign.id, own.id])

        own.refresh_from_db()
        self.assertEqual(own.display_order, 0)  # unchanged — whole operation refused

    def test_reorder_with_missing_item_refused(self):
        first = CaregiverGalleryService.add_item(self.caregiver, image=_image_file())
        CaregiverGalleryService.add_item(self.caregiver, image=_image_file())

        with self.assertRaises(AccountsError):
            CaregiverGalleryService.reorder(self.caregiver, ordered_item_ids=[first.id])

    def test_reorder_cannot_touch_another_caregivers_items(self):
        other_item = CaregiverGalleryService.add_item(self.other_caregiver, image=_image_file())
        own_item = CaregiverGalleryService.add_item(self.caregiver, image=_image_file())

        with self.assertRaises(AccountsError):
            CaregiverGalleryService.reorder(self.caregiver, ordered_item_ids=[own_item.id, other_item.id])

        other_item.refresh_from_db()
        self.assertEqual(other_item.display_order, 0)


class CaregiverGalleryServiceRemoveTest(_FixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_remove_item_deletes_row_and_file(self):
        item = CaregiverGalleryService.add_item(self.caregiver, image=_image_file())
        file_name = item.image.name
        self.assertTrue(item.image.storage.exists(file_name))

        CaregiverGalleryService.remove_item(self.caregiver, item_id=item.id)

        self.assertEqual(CaregiverGalleryItem.objects.filter(id=item.id).count(), 0)
        self.assertFalse(item.image.storage.exists(file_name))

    def test_cannot_remove_another_caregivers_item(self):
        item = CaregiverGalleryService.add_item(self.other_caregiver, image=_image_file())
        with self.assertRaises(AccountsError):
            CaregiverGalleryService.remove_item(self.caregiver, item_id=item.id)
        self.assertEqual(CaregiverGalleryItem.objects.filter(id=item.id).count(), 1)

    def test_remove_nonexistent_item_refused(self):
        with self.assertRaises(AccountsError):
            CaregiverGalleryService.remove_item(self.caregiver, item_id=uuid.uuid4())

    def test_removing_gallery_item_does_not_touch_avatar_or_cover(self):
        from apps.accounts.services.profile_media_service import ProfileMediaService

        ProfileMediaService.set_caregiver_avatar(self.caregiver, _image_file("avatar.png"))
        self.caregiver.refresh_from_db()
        avatar_name = self.caregiver.avatar.name

        item = CaregiverGalleryService.add_item(self.caregiver, image=_image_file("gallery.png"))
        CaregiverGalleryService.remove_item(self.caregiver, item_id=item.id)

        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.avatar.name, avatar_name)
        self.assertTrue(self.caregiver.avatar.storage.exists(avatar_name))


class CaregiverGalleryServiceListTest(_FixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_list_items_only_returns_own_items(self):
        CaregiverGalleryService.add_item(self.caregiver, image=_image_file())
        CaregiverGalleryService.add_item(self.other_caregiver, image=_image_file())
        self.assertEqual(CaregiverGalleryService.list_items(self.caregiver).count(), 1)
