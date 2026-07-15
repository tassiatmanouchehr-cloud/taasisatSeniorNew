"""CaregiverGalleryService — Sprint 2.2 (Caregiver Professional Profile:
Gallery and Media Portfolio)."""

import io
import uuid
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError, transaction
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


def _sized_image_file(width: int, height: int, name="sized.png") -> SimpleUploadedFile:
    """A real, decodable PNG of the given dimensions — solid color, so
    even large-pixel-count fixtures stay small on disk / cheap to
    construct, well under MAX_IMAGE_BYTES."""
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color=(4, 5, 6)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


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
    """Physical file deletion is scheduled via transaction.on_commit()
    (PR #7 remediation) — django.test.TestCase's own wrapping transaction
    never truly commits, so on_commit callbacks must be captured and
    explicitly executed to observe the post-commit effect. See
    CaregiverGalleryServiceTransactionSafetyTest (TransactionTestCase,
    below) for the real commit/rollback-semantics proofs."""

    def setUp(self):
        self._build_fixture()

    def test_remove_item_deletes_row_and_schedules_file_deletion(self):
        item = CaregiverGalleryService.add_item(self.caregiver, image=_image_file())
        file_name = item.image.name
        self.assertTrue(item.image.storage.exists(file_name))

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            CaregiverGalleryService.remove_item(self.caregiver, item_id=item.id)

        self.assertEqual(len(callbacks), 1)  # exactly one physical-deletion callback scheduled
        self.assertEqual(CaregiverGalleryItem.objects.filter(id=item.id).count(), 0)
        self.assertFalse(item.image.storage.exists(file_name))

    def test_cannot_remove_another_caregivers_item(self):
        item = CaregiverGalleryService.add_item(self.other_caregiver, image=_image_file())
        with mock.patch.object(CaregiverGalleryService, "_delete_stored_file") as mock_delete:
            with self.assertRaises(AccountsError):
                CaregiverGalleryService.remove_item(self.caregiver, item_id=item.id)
        mock_delete.assert_not_called()  # unauthorized removal schedules no deletion
        self.assertEqual(CaregiverGalleryItem.objects.filter(id=item.id).count(), 1)
        self.assertTrue(item.image.storage.exists(item.image.name))

    def test_cross_tenant_removal_schedules_no_deletion(self):
        other_tenant = Tenant.objects.create(slug=f"gallery-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")
        cross_tenant_caregiver = self._create_caregiver(tenant=other_tenant, full_name="Cross Tenant Caregiver")
        item = CaregiverGalleryService.add_item(cross_tenant_caregiver, image=_image_file())

        with mock.patch.object(CaregiverGalleryService, "_delete_stored_file") as mock_delete:
            with self.assertRaises(AccountsError):
                CaregiverGalleryService.remove_item(self.caregiver, item_id=item.id)
        mock_delete.assert_not_called()
        self.assertEqual(CaregiverGalleryItem.objects.filter(id=item.id).count(), 1)
        self.assertTrue(item.image.storage.exists(item.image.name))

    def test_remove_nonexistent_item_refused(self):
        with self.assertRaises(AccountsError):
            CaregiverGalleryService.remove_item(self.caregiver, item_id=uuid.uuid4())

    def test_removing_gallery_item_does_not_touch_avatar_or_cover(self):
        from apps.accounts.services.profile_media_service import ProfileMediaService

        ProfileMediaService.set_caregiver_avatar(self.caregiver, _image_file("avatar.png"))
        self.caregiver.refresh_from_db()
        avatar_name = self.caregiver.avatar.name

        item = CaregiverGalleryService.add_item(self.caregiver, image=_image_file("gallery.png"))
        with self.captureOnCommitCallbacks(execute=True):
            CaregiverGalleryService.remove_item(self.caregiver, item_id=item.id)

        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.avatar.name, avatar_name)
        self.assertTrue(self.caregiver.avatar.storage.exists(avatar_name))


class CaregiverGalleryServiceTransactionSafetyTest(_FixtureMixin, TestCase):
    """Real transaction.on_commit()/rollback semantics (PR #7 remediation),
    using plain TestCase + captureOnCommitCallbacks rather than
    TransactionTestCase: Django's nested-atomic-block rollback handling
    discards any on_commit() callback registered inside the rolled-back
    block *before* that block's own __exit__ returns — a real,
    synchronous property of transaction.atomic()'s own bookkeeping, not
    something that depends on the outermost (per-test) transaction ever
    truly committing. captureOnCommitCallbacks(execute=True) therefore
    still correctly observes "was this callback discarded by the
    rollback, or does it still exist to run" even though nothing here
    ever reaches a real commit. (TransactionTestCase was deliberately
    avoided: this environment's Postgres/Django combination has a
    pre-existing, unrelated flush-teardown incompatibility with any
    TransactionTestCase that creates a UserAccount row — reproduced with
    a minimal fixture-only test, confirmed unrelated to this remediation,
    and out of this narrowly-scoped remediation's mandate to fix.)"""

    def setUp(self):
        self._build_fixture()

    def test_rollback_of_enclosing_transaction_prevents_physical_deletion(self):
        item = CaregiverGalleryService.add_item(self.caregiver, image=_image_file())
        file_name = item.image.name
        item_id = item.id

        class _Marker(Exception):
            pass

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with self.assertRaises(_Marker):
                with transaction.atomic():
                    CaregiverGalleryService.remove_item(self.caregiver, item_id=item_id)
                    raise _Marker("force the enclosing transaction to roll back")

        # The callback was registered, then discarded by the rollback —
        # it was never even captured, let alone executed.
        self.assertEqual(callbacks, [])
        # The row deletion (a savepoint nested inside the rolled-back
        # block) was undone along with everything else in that block.
        self.assertTrue(CaregiverGalleryItem.objects.filter(id=item_id).exists())
        self.assertTrue(CaregiverGalleryItem.objects.get(id=item_id).image.storage.exists(file_name))

    def test_db_deletion_failure_leaves_file_intact(self):
        item = CaregiverGalleryService.add_item(self.caregiver, image=_image_file())
        file_name = item.image.name

        with mock.patch.object(CaregiverGalleryItem, "delete", side_effect=DatabaseError("simulated failure")):
            with self.assertRaises(DatabaseError):
                CaregiverGalleryService.remove_item(self.caregiver, item_id=item.id)

        # item.delete() never actually succeeded, so the code never reached
        # the transaction.on_commit() scheduling line at all.
        self.assertTrue(CaregiverGalleryItem.objects.filter(id=item.id).exists())
        self.assertTrue(CaregiverGalleryItem.objects.get(id=item.id).image.storage.exists(file_name))

    def test_storage_deletion_failure_does_not_raise_or_restore_row(self):
        item = CaregiverGalleryService.add_item(self.caregiver, image=_image_file())
        item_id = item.id

        with mock.patch(
            "django.core.files.storage.FileSystemStorage.delete",
            side_effect=OSError("simulated storage failure"),
        ):
            with self.assertLogs("apps.accounts.services.caregiver_gallery_service", level="ERROR") as logs:
                with self.captureOnCommitCallbacks(execute=True):
                    CaregiverGalleryService.remove_item(self.caregiver, item_id=item_id)  # must not raise

        self.assertIn("Failed to delete orphaned gallery file", logs.output[0])
        # The row stays deleted — a storage failure never recreates it,
        # and the item is no longer resolvable (its public URL is dead).
        self.assertFalse(CaregiverGalleryItem.objects.filter(id=item_id).exists())


class CaregiverGalleryServiceImageSafetyTest(_FixtureMixin, TestCase):
    """apps.accounts.services.image_validation.validate_image() — decoded-
    image dimension/pixel-count limits and decompression-bomb handling
    (PR #7 remediation). Exercised through CaregiverGalleryService.add_item()
    since that's the real call site; the shared validator itself is also
    covered directly for avatar/cover in test_profile_media.py-equivalent
    coverage (see ProfileMediaServiceStillWorksTest below)."""

    def setUp(self):
        self._build_fixture()

    def test_excessive_width_rejected(self):
        from apps.accounts.services.image_validation import MAX_IMAGE_WIDTH

        oversized = _sized_image_file(MAX_IMAGE_WIDTH + 100, 10)
        with self.assertRaises(AccountsError):
            CaregiverGalleryService.add_item(self.caregiver, image=oversized)
        self.assertEqual(CaregiverGalleryItem.objects.filter(caregiver=self.caregiver).count(), 0)

    def test_excessive_height_rejected(self):
        from apps.accounts.services.image_validation import MAX_IMAGE_HEIGHT

        oversized = _sized_image_file(10, MAX_IMAGE_HEIGHT + 100)
        with self.assertRaises(AccountsError):
            CaregiverGalleryService.add_item(self.caregiver, image=oversized)

    def test_excessive_pixel_count_rejected(self):
        # 6000x6000 = 36M px: under the individual width/height caps (8000)
        # but over the 25M aggregate pixel cap — isolates the pixel-count
        # check specifically from the per-axis checks.
        oversized = _sized_image_file(6000, 6000)
        with self.assertRaises(AccountsError):
            CaregiverGalleryService.add_item(self.caregiver, image=oversized)

    def test_decompression_bomb_condition_becomes_controlled_error(self):
        # A genuinely modest 100x100 image (10,000 px), but with PIL's own
        # global bomb threshold patched down far below that — proves
        # Image.DecompressionBombError (raised by Pillow itself, not
        # simulated) is caught and mapped to the same controlled
        # AccountsError, never an unhandled 500.
        with mock.patch("PIL.Image.MAX_IMAGE_PIXELS", 10):
            with self.assertRaises(AccountsError):
                CaregiverGalleryService.add_item(self.caregiver, image=_sized_image_file(100, 100))
        self.assertEqual(CaregiverGalleryItem.objects.filter(caregiver=self.caregiver).count(), 0)

    def test_corrupted_image_still_rejected(self):
        truncated = SimpleUploadedFile("broken.png", _PNG_BYTES[:8], content_type="image/png")
        with self.assertRaises(AccountsError):
            CaregiverGalleryService.add_item(self.caregiver, image=truncated)

    def test_valid_jpeg_accepted(self):
        buffer = io.BytesIO()
        Image.new("RGB", (20, 20), color=(9, 9, 9)).save(buffer, format="JPEG")
        jpeg_file = SimpleUploadedFile("photo.jpg", buffer.getvalue(), content_type="image/jpeg")
        item = CaregiverGalleryService.add_item(self.caregiver, image=jpeg_file)
        self.assertTrue(item.image)

    def test_valid_png_accepted(self):
        item = CaregiverGalleryService.add_item(self.caregiver, image=_image_file())
        self.assertTrue(item.image)

    def test_valid_webp_accepted(self):
        buffer = io.BytesIO()
        Image.new("RGB", (20, 20), color=(7, 7, 7)).save(buffer, format="WEBP")
        webp_file = SimpleUploadedFile("photo.webp", buffer.getvalue(), content_type="image/webp")
        item = CaregiverGalleryService.add_item(self.caregiver, image=webp_file)
        self.assertTrue(item.image)

    def test_file_stream_usable_after_validation(self):
        from apps.accounts.services.image_validation import validate_image

        image_file = _image_file()
        validate_image(image_file)
        # The field assignment that follows validation (ImageField.save())
        # must be able to read the file from the start — a validator that
        # left the stream at EOF would silently store an empty/truncated
        # file.
        self.assertEqual(image_file.tell(), 0)
        remaining = image_file.read()
        self.assertEqual(remaining, _PNG_BYTES)


class ProfileMediaServiceStillWorksTest(_FixtureMixin, TestCase):
    """Avatar/cover validation must behave identically after image_validation
    extraction and the added dimension/pixel-count limits (PR #7 remediation)
    — same shared function, same behavior, just also bounded now."""

    def setUp(self):
        self._build_fixture()

    def test_avatar_upload_still_accepts_valid_image(self):
        from apps.accounts.services.profile_media_service import ProfileMediaService

        ProfileMediaService.set_caregiver_avatar(self.caregiver, _image_file("avatar.png"))
        self.caregiver.refresh_from_db()
        self.assertTrue(self.caregiver.avatar)

    def test_cover_upload_still_rejects_non_image(self):
        from apps.accounts.services.profile_media_service import ProfileMediaService

        bad_file = SimpleUploadedFile("fake.png", NON_IMAGE_BYTES, content_type="image/png")
        with self.assertRaises(AccountsError):
            ProfileMediaService.set_caregiver_cover(self.caregiver, bad_file)

    def test_avatar_upload_rejects_excessive_dimensions(self):
        from apps.accounts.services.image_validation import MAX_IMAGE_WIDTH
        from apps.accounts.services.profile_media_service import ProfileMediaService

        oversized = _sized_image_file(MAX_IMAGE_WIDTH + 100, 10)
        with self.assertRaises(AccountsError):
            ProfileMediaService.set_caregiver_avatar(self.caregiver, oversized)


class CaregiverGalleryServiceListTest(_FixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_list_items_only_returns_own_items(self):
        CaregiverGalleryService.add_item(self.caregiver, image=_image_file())
        CaregiverGalleryService.add_item(self.other_caregiver, image=_image_file())
        self.assertEqual(CaregiverGalleryService.list_items(self.caregiver).count(), 1)
