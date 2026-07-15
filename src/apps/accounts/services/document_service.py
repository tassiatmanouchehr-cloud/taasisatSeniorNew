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

Phase 1.2 (Verification Completion and Activation Rules) added
`resubmit()`: the owner-authorized entry point for the correction/
resubmission lifecycle (PENDING/REJECTED/CORRECTION_REQUIRED -> new file
-> PENDING again). `replace_document()` remains the lower-level file-swap
primitive `resubmit()` wraps — call it directly only from trusted,
already-ownership-scoped contexts (as the two existing portal views did
before this phase); anything reachable from a request should go through
`resubmit()`, which is the one that actually verifies the caller is the
document's owner and refuses to touch an already-VERIFIED document.
"""

from django.db import transaction

from .document_ownership import owner_user_id_for_document, tenant_id_for_document
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
    """Read-write, provider-/organization-facing only. Upload, replace,
    and resubmit are the only mutating operations exposed — never
    approve/reject/verify (see module docstring)."""

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
    @transaction.atomic
    def resubmit(cls, document, *, actor, file):
        """Owner-authorized resubmission — Phase 1.2 (Verification
        Completion and Activation Rules). Row-locks the document so two
        concurrent resubmissions of the same document serialize rather
        than racing on the old-file delete; refuses an actor who isn't
        the document's own owner user (cross-tenant/cross-owner denial —
        no separate tenant_id parameter is needed since ownership alone
        already implies tenant); refuses to touch an already-VERIFIED
        document (an owner can no longer silently discard a platform
        decision by re-uploading — `replace_document()` itself has no
        such guard, by design, since it is also the primitive
        `VerificationReviewService` never calls but that pre-Phase-1.2
        callers used directly). Records an audit entry and re-syncs the
        owning profile's rolled-up verification_status in the same
        transaction — a required document leaving REJECTED/
        CORRECTION_REQUIRED for PENDING must not leave a stale profile-
        level status behind."""
        from apps.accounts.models.media import DocumentStatus, VerificationDocument
        from apps.kernel.services.audit_service import AuditService

        from .verification_rollup_service import ProfileVerificationRollupService

        locked = VerificationDocument.objects.select_for_update().get(id=document.id)

        owner_user_id = owner_user_id_for_document(locked)
        if actor is None or getattr(actor, "id", None) != owner_user_id:
            raise AccountsError("Only the document owner may resubmit this document.")

        if locked.status == DocumentStatus.VERIFIED:
            raise AccountsError("An approved document cannot be replaced.")

        previous_status = locked.status
        updated = cls.replace_document(locked, file=file)

        AuditService.log(
            tenant_id=tenant_id_for_document(locked),
            action="accounts.document.resubmitted",
            resource_type="VerificationDocument",
            resource_id=locked.id,
            module_id="M08",
            actor_id=getattr(actor, "person_id", None),
            actor_type="user",
            before={"status": previous_status},
            after={"status": DocumentStatus.PENDING},
            metadata={"owner_user_id": str(owner_user_id)},
        )

        if locked.caregiver_id:
            ProfileVerificationRollupService.sync_caregiver(locked.caregiver)
        else:
            ProfileVerificationRollupService.sync_organization(locked.organization)

        return updated

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
