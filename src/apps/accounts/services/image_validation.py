"""
Shared image-upload validation — extracted from ProfileMediaService
(Epic 06 Sprint 2) during Sprint 2.2 (Caregiver Gallery and Media
Portfolio) so CaregiverGalleryService can reuse the exact same validation
instead of duplicating it. Behavior is unchanged: MIME type is sniffed
from the file's own bytes via Pillow's own decode, never trusted from the
client-supplied Content-Type header — only JPEG/PNG/WEBP under the size
cap are accepted.
"""

import io

from django.core.files.uploadedfile import UploadedFile

from .errors import AccountsError

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


def validate_image(file: UploadedFile) -> None:
    if file.size > MAX_IMAGE_BYTES:
        raise AccountsError(f"Image exceeds the {MAX_IMAGE_BYTES // (1024 * 1024)}MB size limit.")

    from PIL import Image, UnidentifiedImageError

    file.seek(0)
    data = file.read()
    file.seek(0)
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
            image_format = image.format
    except (UnidentifiedImageError, OSError):
        raise AccountsError("The uploaded file is not a valid image.") from None

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise AccountsError(f"Unsupported image format: {image_format}. Use JPEG, PNG, or WEBP.")
