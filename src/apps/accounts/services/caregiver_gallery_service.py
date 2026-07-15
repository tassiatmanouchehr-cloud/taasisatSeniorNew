"""
CaregiverGalleryService — Sprint 2.2 (Caregiver Professional Profile:
Gallery and Media Portfolio).

Owner-authorized read-write for a caregiver's own gallery/portfolio
photos, mirroring `CaregiverSkillService`/`CaregiverExperienceService`'s
established ownership shape (`caregiver_professional_profile_service.py`):
no RBAC permission key — ownership via `request.user.caregiver_profile`
is the authorization boundary, a fixed, explicit, field-whitelisted API,
and every mutation filters by `caregiver=caregiver` together with the
target row's own id, never a bare `.get(id=...)` followed by a separate
ownership check.

Upload and reorder both row-lock the owning `CaregiverProfile`
(`select_for_update()`) for the duration of the mutation — heavier than
`CaregiverSkillService`'s unique-constraint-backstop pattern, because
neither "at most MAX_GALLERY_ITEMS_PER_CAREGIVER rows" nor "these N rows
now have these N distinct positions" is expressible as a single DB
constraint the way "no duplicate skill name" is. This mirrors
`DocumentService.resubmit()`'s row-locking — the existing precedent in
this app for a mutation that genuinely needs an explicit lock, rather
than skill/experience's lighter, constraint-backed pattern.

Deletion is a hard delete that always removes the stored file
(`image.delete(save=False)`), the same convention
`ProfileMediaService._replace()` uses for avatar/cover replacement — see
`apps.accounts.models.gallery` for why no soft-delete/archive field
exists on this model. `is_visible` is the only visibility lever short of
permanent deletion.
"""

from django.db import transaction

from ..models.gallery import CaregiverGalleryItem
from ..models.profiles import CaregiverProfile
from .errors import AccountsError
from .image_validation import validate_image

MAX_GALLERY_ITEMS_PER_CAREGIVER = 12
"""Explicit, hardcoded cap — no product requirement or existing repo
convention (e.g. `RequiredDocumentPolicy`'s `ConfigResolver`) calls for
this being tenant-configurable, matching
`CaregiverSkillService.MAX_SKILL_NAME_LENGTH`'s own explicit-constant
style."""

MAX_TEXT_FIELD_LENGTH = 255


class CaregiverGalleryService:
    """Read-write: a caregiver's own gallery items only."""

    @classmethod
    def list_items(cls, caregiver):
        return CaregiverGalleryItem.objects.filter(caregiver=caregiver)

    @classmethod
    @transaction.atomic
    def add_item(cls, caregiver, *, image, caption: str = "", alt_text: str = "") -> CaregiverGalleryItem:
        cleaned_caption = cls._clean_text(caption, label="Caption")
        cleaned_alt = cls._clean_text(alt_text, label="Alt text")
        validate_image(image)

        # Row-locks the owning profile so two concurrent uploads from the
        # same caregiver cannot both observe count < MAX and both
        # succeed — the gallery limit has no unique-constraint backstop
        # the way uq_caregiver_skill_name gives add_skill().
        locked_caregiver = CaregiverProfile.objects.select_for_update().get(id=caregiver.id)
        current_count = CaregiverGalleryItem.objects.filter(caregiver=locked_caregiver).count()
        if current_count >= MAX_GALLERY_ITEMS_PER_CAREGIVER:
            raise AccountsError(f"Gallery limit reached ({MAX_GALLERY_ITEMS_PER_CAREGIVER} photos maximum).")

        return CaregiverGalleryItem.objects.create(
            caregiver=locked_caregiver,
            image=image,
            caption=cleaned_caption,
            alt_text=cleaned_alt,
            display_order=current_count,
        )

    @classmethod
    def update_item(
        cls, caregiver, *, item_id, caption: str = "", alt_text: str = "", is_visible: bool = True,
    ) -> CaregiverGalleryItem:
        cleaned_caption = cls._clean_text(caption, label="Caption")
        cleaned_alt = cls._clean_text(alt_text, label="Alt text")
        try:
            item = CaregiverGalleryItem.objects.get(id=item_id, caregiver=caregiver)
        except CaregiverGalleryItem.DoesNotExist:
            raise AccountsError("Gallery item not found.") from None

        item.caption = cleaned_caption
        item.alt_text = cleaned_alt
        item.is_visible = is_visible
        item.save(update_fields=["caption", "alt_text", "is_visible", "updated_at"])
        return item

    @classmethod
    @transaction.atomic
    def reorder(cls, caregiver, *, ordered_item_ids) -> None:
        """`ordered_item_ids` must be exactly this caregiver's own item ids,
        each exactly once, in the desired display order — anything else
        (a foreign id, a missing id, a duplicate) refuses the whole
        operation rather than applying a partial reorder."""
        locked_caregiver = CaregiverProfile.objects.select_for_update().get(id=caregiver.id)
        items = list(CaregiverGalleryItem.objects.select_for_update().filter(caregiver=locked_caregiver))
        items_by_id = {str(item.id): item for item in items}

        requested_ids = [str(item_id) for item_id in ordered_item_ids]
        if len(requested_ids) != len(items) or set(requested_ids) != set(items_by_id):
            raise AccountsError("Reorder must include exactly this caregiver's own gallery items.")

        for index, item_id in enumerate(requested_ids):
            item = items_by_id[item_id]
            if item.display_order != index:
                item.display_order = index
                item.save(update_fields=["display_order", "updated_at"])

    @classmethod
    @transaction.atomic
    def remove_item(cls, caregiver, *, item_id) -> None:
        locked_caregiver = CaregiverProfile.objects.select_for_update().get(id=caregiver.id)
        try:
            item = CaregiverGalleryItem.objects.select_for_update().get(id=item_id, caregiver=locked_caregiver)
        except CaregiverGalleryItem.DoesNotExist:
            raise AccountsError("Gallery item not found.") from None
        if item.image:
            item.image.delete(save=False)
        item.delete()

    @staticmethod
    def _clean_text(value: str, *, label: str) -> str:
        cleaned = (value or "").strip()
        if len(cleaned) > MAX_TEXT_FIELD_LENGTH:
            raise AccountsError(f"{label} exceeds {MAX_TEXT_FIELD_LENGTH} characters.")
        return cleaned
