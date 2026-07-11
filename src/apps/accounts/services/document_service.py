"""
DocumentService — Epic 06 Sprint 2 (Shared Portal UI Core, Provider
Profile, Organization Profile).

Provider-/organization-facing document management for
`apps.accounts.models.media.VerificationDocument`. Every upload this
service creates starts at `DocumentStatus.PENDING` — there is no method
here, and deliberately never will be one reachable from
apps.provider_portal/apps.organization_portal, that sets a document to
VERIFIED or REJECTED. That transition is reserved for a future
platform-admin verification workflow (out of this Sprint's scope; see
`docs/architecture/GAP_ANALYSIS.md`/this Sprint's own final report for
the explicit "cannot implement" note) — a caregiver or organization admin
literally cannot call their way into self-verifying through this service,
by construction, not just by convention.

Validation mirrors `profile_media_service.py`'s own discipline: hard size
cap, and a real content sniff (not the client-supplied `content_type`
header) — PDF via a magic-byte check, images via Pillow, exactly like
avatar/cover uploads.
"""

from .errors import AccountsError

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_DOCUMENT_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}

_PDF_MAGIC = b"%PDF-"


def _validate_document(file) -> None:
    if file.size > MAX_DOCUMENT_BYTES:
        raise AccountsError(f"Document exceeds the {MAX_DOCUMENT_BYTES // (1024 * 1024)}MB size limit.")

    file.seek(0)
    head = file.read(1024)
    file.seek(0)

    if head.startswith(_PDF_MAGIC):
        return

    import io

    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(head + file.read())) as image:
            file.seek(0)
            image.verify()
            image_format = image.format
    except (UnidentifiedImageError, OSError):
        raise AccountsError("The uploaded file must be a PDF, JPEG, or PNG.") from None

    if image_format not in {"JPEG", "PNG"}:
        raise AccountsError("The uploaded file must be a PDF, JPEG, or PNG.")


class DocumentService:
    """Read-write, provider-/organization-facing only. Upload and replace
    are the only mutating operations exposed — never approve/reject/
    verify (see module docstring)."""

    @classmethod
    def upload_caregiver_document(cls, caregiver, *, document_type, file):
        from apps.accounts.models.media import DocumentStatus, VerificationDocument

        _validate_document(file)
        return VerificationDocument.objects.create(
            caregiver=caregiver,
            document_type=document_type,
            file=file,
            status=DocumentStatus.PENDING,
        )

    @classmethod
    def upload_organization_document(cls, organization, *, document_type, file):
        from apps.accounts.models.media import DocumentStatus, VerificationDocument

        _validate_document(file)
        return VerificationDocument.objects.create(
            organization=organization,
            document_type=document_type,
            file=file,
            status=DocumentStatus.PENDING,
        )

    @classmethod
    def replace_document(cls, document, *, file):
        """Replaces a document's file in place, resetting it to PENDING
        (a replaced document must be re-reviewed) — never touches
        document_type/caregiver/organization."""
        from apps.accounts.models.media import DocumentStatus

        _validate_document(file)
        old_file = document.file
        document.file = file
        document.status = DocumentStatus.PENDING
        document.reviewed_by = None
        document.reviewed_at = None
        document.rejection_reason = ""
        document.save(update_fields=["file", "status", "reviewed_by", "reviewed_at", "rejection_reason", "updated_at"])
        if old_file:
            old_file.delete(save=False)
        return document

    @classmethod
    def list_for_caregiver(cls, caregiver):
        return caregiver.documents.order_by("document_type", "-created_at")

    @classmethod
    def list_for_organization(cls, organization):
        return organization.documents.order_by("document_type", "-created_at")

    @classmethod
    def get_owned_document(cls, document_id, *, caregiver=None, organization=None):
        """Ownership-safe lookup — raises AccountsError if the document
        doesn't exist or doesn't belong to the given caregiver/organization.
        Exactly one of caregiver/organization must be passed."""
        from apps.accounts.models.media import VerificationDocument

        filters = {"id": document_id}
        if caregiver is not None:
            filters["caregiver"] = caregiver
        if organization is not None:
            filters["organization"] = organization
        try:
            return VerificationDocument.objects.get(**filters)
        except VerificationDocument.DoesNotExist:
            raise AccountsError("Document not found.") from None
