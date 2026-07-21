"""
ProfileMediaService — Epic 06 Sprint 2 (Shared Portal UI Core, Provider
Profile, Organization Profile).

The smallest correct profile-media foundation this Sprint's scope calls
for: avatar/cover for CaregiverProfile, logo/cover for OrganizationProfile.
Deliberately not a generic enterprise DAM — no versioning, no derivative
image sizes, no CDN integration, no background processing. One validated
file in, one replacement/removal operation, done.

Every write here goes through this one service — apps.provider_portal and
apps.organization_portal never touch `CaregiverProfile.avatar`/
`OrganizationProfile.logo` etc. directly, matching this codebase's
existing "route every mutation through an approved service" convention.

Validation is intentionally strict and server-side only (never trust a
client-reported content-type): MIME type is sniffed from the file's own
bytes via Pillow's own decode, not from `UploadedFile.content_type`
(a client-supplied, spoofable HTTP header) — an attacker renaming an
executable to `.jpg` and setting `Content-Type: image/jpeg` fails here
because Pillow's `Image.open().verify()` raises on non-image bytes. Only
JPEG/PNG/WEBP are accepted. Max size is enforced before ever touching
Pillow (a cheap, fast rejection for absurdly large uploads).

Phase 3 Sprint 3.2 (Company Professional Profile and Public Presence)
remediation, two fixes:

1. The four organization-side methods previously had no permission check
   at all — apps.organization_portal.views' logo/cover upload/remove
   views called them straight after `resolve_organization()`'s ownership
   resolution, unlike `OrganizationProfileUpdateService.update_profile()`
   /`update_service_categories()`, which already guard the same
   `ORGANIZATION_PROFILE_UPDATE` permission key (whose own description
   already claims to cover "public/contact fields, media, or
   documents"). Now require an `actor` kwarg and check that key,
   mirroring `OrganizationProfileUpdateService`'s exact
   `ownership_authorized_by` shape — `resolve_organization()` remains the
   real access boundary (an unrelated caller never reaches this service
   at all), this is the same explicit, audited permission-key hardening
   Sprint 3.1 already applied to the affiliation-mutation call sites.
   Caregiver-side methods are unchanged: ownership-authorized only,
   matching this codebase's unbroken rule that no CAREGIVER-role action
   is RBAC-gated.
2. `_replace()` used to delete the old physical file *before* saving the
   new field value — unsafe, since storage deletion is not transactional
   (the exact class of problem `CaregiverGalleryService.remove_item()`'s
   Sprint 2.2 remediation already fixed for gallery items). Fixed the
   same way: the DB row is updated first; the old file (if any) is only
   physically deleted via `transaction.on_commit()`, which Django
   discards entirely if the surrounding transaction rolls back.
"""

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from apps.kernel.permissions.keys import ORGANIZATION_PROFILE_UPDATE
from apps.kernel.services.permission_service import PermissionService

from .image_validation import ALLOWED_IMAGE_FORMATS, MAX_IMAGE_BYTES
from .image_validation import validate_image as _validate_image

# Re-exported for any existing importer of this module's own constants —
# the validation logic itself now lives in .image_validation (Sprint 2.2),
# shared with CaregiverGalleryService rather than duplicated.
__all__ = ["ALLOWED_IMAGE_FORMATS", "MAX_IMAGE_BYTES", "ProfileMediaService"]


class ProfileMediaService:
    """Read-write: sets/removes avatar/cover/logo images for a caregiver
    or organization profile. Never called from a template — only from
    apps.provider_portal/apps.organization_portal views, after the
    caller has already verified the actor owns the profile."""

    # -- Caregiver ------------------------------------------------------

    @classmethod
    def set_caregiver_avatar(cls, caregiver, file: UploadedFile):
        _validate_image(file)
        cls._replace(caregiver, "avatar", file)
        return caregiver

    @classmethod
    def remove_caregiver_avatar(cls, caregiver):
        cls._replace(caregiver, "avatar", None)
        return caregiver

    @classmethod
    def set_caregiver_cover(cls, caregiver, file: UploadedFile):
        _validate_image(file)
        cls._replace(caregiver, "cover_image", file)
        return caregiver

    @classmethod
    def remove_caregiver_cover(cls, caregiver):
        cls._replace(caregiver, "cover_image", None)
        return caregiver

    # -- Organization -----------------------------------------------------

    @classmethod
    def set_organization_logo(cls, organization, file: UploadedFile, *, actor):
        cls._require_organization_media_permission(organization, actor=actor)
        _validate_image(file)
        cls._replace(organization, "logo", file)
        return organization

    @classmethod
    def remove_organization_logo(cls, organization, *, actor):
        cls._require_organization_media_permission(organization, actor=actor)
        cls._replace(organization, "logo", None)
        return organization

    @classmethod
    def set_organization_cover(cls, organization, file: UploadedFile, *, actor):
        cls._require_organization_media_permission(organization, actor=actor)
        _validate_image(file)
        cls._replace(organization, "cover_image", file)
        return organization

    @classmethod
    def remove_organization_cover(cls, organization, *, actor):
        cls._require_organization_media_permission(organization, actor=actor)
        cls._replace(organization, "cover_image", None)
        return organization

    # ------------------------------------------------------------------

    @staticmethod
    def _require_organization_media_permission(organization, *, actor) -> None:
        PermissionService.require(
            None,
            ORGANIZATION_PROFILE_UPDATE,
            tenant_id=organization.tenant_id,
            ownership_authorized_by=actor,
            scope={"scope_type": "organization", "scope_id": str(organization.id)},
        )

    @staticmethod
    @transaction.atomic
    def _replace(instance, field_name: str, file) -> None:
        """Points the field at the new value (or None) first, then
        schedules physical deletion of the *old* file (if any) for after
        the transaction commits — never deletes a still-referenced file
        if the save is rolled back, and never leaves an orphaned file
        behind on a successful replacement/removal."""
        old_field = getattr(instance, field_name)
        old_name = old_field.name if old_field else None
        old_storage = old_field.storage if old_field else None

        setattr(instance, field_name, file)
        instance.save(update_fields=[field_name, "updated_at"])

        if old_name:
            transaction.on_commit(lambda: old_storage.delete(old_name))
