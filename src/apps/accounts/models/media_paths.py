"""
Deterministic, safe upload-path generators for profile media and
verification documents — Epic 06 Sprint 2 (Shared Portal UI Core, Provider
Profile, Organization Profile).

Used directly as Django `upload_to=` callables on `CaregiverProfile
.avatar`/`.cover_image`, `OrganizationProfile.logo`/`.cover_image`, and
`VerificationDocument.file` (apps/accounts/models/profiles.py,
apps/accounts/models/media.py). Must be plain, importable module-level
functions (not lambdas/closures) — Django serializes `upload_to` into
migration files by reference.

Every path is a fresh `uuid4()` filename under a fixed, type-scoped
directory — the original uploaded filename is never used for the stored
path (avoids path traversal, collisions, and leaking a user's local
filesystem naming). Only the validated extension (see
`profile_media_service.py`/`document_service.py`, which run before these
are ever called) is preserved.

`public/` vs `private/` is a deliberate, load-bearing split: `config/urls.py`
only ever registers Django's `static()` media-serving helper for
`MEDIA_ROOT/public` in development. Verification documents live under
`private/` and are never reachable via a raw `MEDIA_URL` path — the only
way to read one back is the authenticated, ownership-checked document
download view, which opens the file directly rather than trusting a
public path. This is what satisfies this Sprint's "no arbitrary file URL
submission" / "no exposure of filesystem paths" / "private authenticated
upload" requirements for documents while still allowing avatars/covers to
be served as plain public-safe URLs (required for public profile pages).
"""

import uuid


def _safe_extension(filename: str, *, default: str) -> str:
    if not filename or "." not in filename:
        return default
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext if ext.isalnum() and len(ext) <= 5 else default


def caregiver_avatar_path(instance, filename: str) -> str:
    return f"public/avatars/caregiver/{uuid.uuid4().hex}.{_safe_extension(filename, default='jpg')}"


def caregiver_cover_path(instance, filename: str) -> str:
    return f"public/covers/caregiver/{uuid.uuid4().hex}.{_safe_extension(filename, default='jpg')}"


def caregiver_gallery_path(instance, filename: str) -> str:
    return f"public/gallery/caregiver/{uuid.uuid4().hex}.{_safe_extension(filename, default='jpg')}"


def organization_logo_path(instance, filename: str) -> str:
    return f"public/logos/organization/{uuid.uuid4().hex}.{_safe_extension(filename, default='jpg')}"


def organization_cover_path(instance, filename: str) -> str:
    return f"public/covers/organization/{uuid.uuid4().hex}.{_safe_extension(filename, default='jpg')}"


def verification_document_path(instance, filename: str) -> str:
    return f"private/documents/{uuid.uuid4().hex}.{_safe_extension(filename, default='pdf')}"
