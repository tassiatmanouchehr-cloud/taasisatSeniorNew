"""
Shared image-upload validation — extracted from ProfileMediaService
(Epic 06 Sprint 2) during Sprint 2.2 (Caregiver Gallery and Media
Portfolio) so CaregiverGalleryService can reuse the exact same validation
instead of duplicating it. Behavior is unchanged: MIME type is sniffed
from the file's own bytes via Pillow's own decode, never trusted from the
client-supplied Content-Type header — only JPEG/PNG/WEBP under the size
cap are accepted.

Remediation (PR #7 review, 2026-07-15): the upload byte-size cap
(`MAX_IMAGE_BYTES`) bounds the *compressed* file on disk, not the
*decoded* image in memory — a small, highly-compressed file can still
claim an enormous pixel grid ("decompression bomb"). `MAX_IMAGE_WIDTH`/
`MAX_IMAGE_HEIGHT`/`MAX_IMAGE_PIXELS` bound the decoded dimensions
directly, read from the image header (available immediately after
`Image.open()`, before any full pixel decode), deliberately well below
Pillow's own global `Image.MAX_IMAGE_PIXELS` bomb threshold so these
explicit, repository-owned constants are what actually bounds resource
usage in practice. Pillow's own `DecompressionBombError` (raised) and
`DecompressionBombWarning` (only warned by default — promoted to an
exception here via a scoped `warnings` filter so it can't silently pass
through) are both caught as defense-in-depth for any case these
constants don't catch first, and both map to the same controlled
`AccountsError` — never a raw exception, never a 500.
"""

import io
import warnings

from django.core.files.uploadedfile import UploadedFile

from .errors import AccountsError

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_IMAGE_WIDTH = 8000
MAX_IMAGE_HEIGHT = 8000
MAX_IMAGE_PIXELS = 25_000_000  # ~25 megapixels — comfortably above any real photo upload


def validate_image(file: UploadedFile) -> None:
    if file.size > MAX_IMAGE_BYTES:
        raise AccountsError(f"Image exceeds the {MAX_IMAGE_BYTES // (1024 * 1024)}MB size limit.")

    from PIL import Image, UnidentifiedImageError

    file.seek(0)
    data = file.read()
    file.seek(0)

    # Single decode pass: open once, read format+size (header-only, cheap),
    # then verify() for integrity — never re-opened, never decoded twice.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                image_format = image.format
                width, height = image.size
                image.verify()
    except Image.DecompressionBombError:
        raise AccountsError("The uploaded image exceeds safe decoded size limits.") from None
    except Image.DecompressionBombWarning:
        raise AccountsError("The uploaded image exceeds safe decoded size limits.") from None
    except (UnidentifiedImageError, OSError):
        raise AccountsError("The uploaded file is not a valid image.") from None

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise AccountsError(f"Unsupported image format: {image_format}. Use JPEG, PNG, or WEBP.")

    if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
        raise AccountsError(f"Image dimensions exceed the maximum allowed ({MAX_IMAGE_WIDTH}x{MAX_IMAGE_HEIGHT} px).")
    if width * height > MAX_IMAGE_PIXELS:
        raise AccountsError(f"Image exceeds the maximum allowed pixel count ({MAX_IMAGE_PIXELS} px).")

    file.seek(0)
