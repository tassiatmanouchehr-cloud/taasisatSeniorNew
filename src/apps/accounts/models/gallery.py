"""
CaregiverGalleryItem — Sprint 2.2 (Caregiver Professional Profile:
Gallery and Media Portfolio).

A caregiver's own professional photo portfolio — a normalized child
table of the existing `CaregiverProfile` aggregate, following the exact
shape `CaregiverSkill`/`CaregiverExperience`
(`apps/accounts/models/professional_profile.py`) already established for
caregiver-owned list-type child records in this app: plain
`models.Model`, UUID PK, FK with `related_name`, no `TenantAwareModel`
base — tenant is derived transitively via `caregiver.user.tenant`, never
duplicated onto the child row.

Distinct in responsibility from `CaregiverProfile.avatar`/`.cover_image`
(Epic 06 Sprint 2): avatar is the primary identity image, cover is the
profile header image, a gallery item is one entry in a *list* of
portfolio photos. This model never touches the `avatar`/`cover_image`
fields, and `CaregiverGalleryService` never reuses `ProfileMediaService`'s
single-field `_replace()` — a gallery is additive (many rows), not a
replace-in-place single field.

Image storage follows `ProfileMediaService`'s established convention
(`caregiver_gallery_path` in `media_paths.py`, same Pillow-verified
JPEG/PNG/WEBP validation via `apps.accounts.services.image_validation`,
5MB cap) — see `CaregiverGalleryService`.

Deletion is a hard delete — no soft-delete/archive field. This app has no
`ArchivableModel`/`is_deleted` convention on any caregiver-owned child row
(`VerificationDocument`, `CaregiverSkill`, `CaregiverExperience` all
hard-delete), and `ProfileMediaService._replace()` already deletes the
physical file on avatar/cover replacement — the same convention is
followed here rather than introducing a new soft-delete concept for this
one model. `is_visible` (identical shape to `CaregiverSkill.is_visible`/
`CaregiverExperience.is_visible`) is the one and only visibility lever a
caregiver has short of permanent deletion — hiding an item never deletes
its file, it only removes the item from the public selector.
"""

import uuid

from django.db import models

from .media_paths import caregiver_gallery_path


class CaregiverGalleryItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    caregiver = models.ForeignKey(
        "accounts.CaregiverProfile",
        on_delete=models.CASCADE,
        related_name="gallery_items",
    )
    image = models.ImageField(upload_to=caregiver_gallery_path)
    caption = models.CharField(max_length=255, blank=True)
    alt_text = models.CharField(max_length=255, blank=True)
    display_order = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_caregiver_gallery_item"
        indexes = [
            models.Index(fields=["caregiver", "display_order"]),
        ]
        ordering = ["display_order", "created_at"]

    def __str__(self):
        return f"{self.caregiver_id}: gallery item {self.id}"
