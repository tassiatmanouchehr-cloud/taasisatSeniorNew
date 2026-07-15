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
"""

from django.core.files.uploadedfile import UploadedFile

from .image_validation import ALLOWED_IMAGE_FORMATS, MAX_IMAGE_BYTES, validate_image as _validate_image

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
    def set_organization_logo(cls, organization, file: UploadedFile):
        _validate_image(file)
        cls._replace(organization, "logo", file)
        return organization

    @classmethod
    def remove_organization_logo(cls, organization):
        cls._replace(organization, "logo", None)
        return organization

    @classmethod
    def set_organization_cover(cls, organization, file: UploadedFile):
        _validate_image(file)
        cls._replace(organization, "cover_image", file)
        return organization

    @classmethod
    def remove_organization_cover(cls, organization):
        cls._replace(organization, "cover_image", None)
        return organization

    # ------------------------------------------------------------------

    @staticmethod
    def _replace(instance, field_name: str, file) -> None:
        """Deletes the old stored file (if any) before pointing the field
        at the new one (or None) — never leaves an orphaned file behind
        on replacement/removal."""
        field = getattr(instance, field_name)
        if field:
            field.delete(save=False)
        setattr(instance, field_name, file)
        instance.save(update_fields=[field_name, "updated_at"])
