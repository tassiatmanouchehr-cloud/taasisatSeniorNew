"""VerificationReviewService — Phase 1.1 (Manual Document Verification).

The platform-admin verification workflow `apps.accounts.models.media`'s
own module docstring named as future/out-of-scope for Epic 06 Sprint 2:
authorized platform staff reviewing an uploaded `VerificationDocument`
(caregiver or organization) and setting it to VERIFIED, REJECTED, or
CORRECTION_REQUIRED. Upload/replace remain `DocumentService`'s job
unchanged — this service only ever moves a document OUT of PENDING.

`VerificationDocument` carries no direct tenant field (see that model's
own docstring for why: it has exactly one of a caregiver or an
organization owner). Tenant is always re-derived from that owner
(`caregiver.user.tenant_id` / `organization.tenant_id`) and compared
against the caller-supplied `tenant_id` on every operation — a
document belonging to another tenant is reported as not found, not as a
distinct "wrong tenant" error, so cross-tenant review attempts cannot
even confirm the document exists.

Every review method: row-locks the document, re-derives and checks
tenant scope, enforces the `accounts.document.review` permission,
refuses self-review, applies the PENDING -> {VERIFIED, REJECTED,
CORRECTION_REQUIRED} transition (idempotent no-op if already in the
requested state, a domain error for any other non-PENDING state), and
records an AuditLog entry — the same shape
`apps.accounts.services.organization_staff.OrganizationStaffService
.approve_membership()` already established for platform-authorized
profile-state changes. Phase 1.2 (Verification Completion and Activation
Rules) added one more step at the end of every review: syncing the
owning profile's `verification_status` via
`apps.accounts.services.verification_rollup_service
.ProfileVerificationRollupService`, in the same transaction.
"""

from django.db import transaction
from django.utils import timezone

from apps.kernel.permissions.keys import ACCOUNTS_DOCUMENT_REVIEW
from apps.kernel.services.audit_service import AuditService
from apps.kernel.services.permission_service import PermissionService

from .document_ownership import owner_user_id_for_document, tenant_id_for_document
from .errors import AccountsError

MODULE_ID = "M08"


class VerificationReviewError(AccountsError):
    """Raised for illegal review transitions/inputs — a controlled domain
    error, never a bare exception or a silent overwrite."""


class VerificationReviewService:
    """Platform-staff-only. No method here is reachable from the
    caregiver/organization portals — see `DocumentService`'s own
    docstring for that boundary."""

    @classmethod
    def list_pending_for_tenant(cls, *, tenant_id):
        """The review queue: every PENDING document owned by a caregiver
        or organization in this tenant."""
        from django.db.models import Q

        from ..models.media import DocumentStatus, VerificationDocument

        return (
            VerificationDocument.objects.select_related("caregiver", "organization")
            .filter(
                Q(caregiver__user__tenant_id=tenant_id) | Q(organization__tenant_id=tenant_id),
                status=DocumentStatus.PENDING,
            )
            .order_by("created_at")
        )

    @classmethod
    def get_document_for_tenant(cls, *, tenant_id, document_id):
        """Tenant-scoped, ownership-safe lookup. Raises AccountsError —
        indistinguishable whether the document doesn't exist at all or
        belongs to a different tenant."""
        from django.db.models import Q

        from ..models.media import VerificationDocument

        try:
            return VerificationDocument.objects.select_related(
                "caregiver__user",
                "organization__admin_user",
            ).get(
                Q(caregiver__user__tenant_id=tenant_id) | Q(organization__tenant_id=tenant_id),
                id=document_id,
            )
        except VerificationDocument.DoesNotExist:
            raise AccountsError("Document not found.") from None

    @classmethod
    @transaction.atomic
    def approve(cls, *, document_id, tenant_id, reviewer):
        from ..models.media import DocumentStatus

        return cls._apply_review(
            document_id=document_id,
            tenant_id=tenant_id,
            reviewer=reviewer,
            target_status=DocumentStatus.VERIFIED,
            reason="",
        )

    @classmethod
    @transaction.atomic
    def reject(cls, *, document_id, tenant_id, reviewer, reason: str):
        from ..models.media import DocumentStatus

        if not reason or not reason.strip():
            raise VerificationReviewError("A reason is required to reject a document.")
        return cls._apply_review(
            document_id=document_id,
            tenant_id=tenant_id,
            reviewer=reviewer,
            target_status=DocumentStatus.REJECTED,
            reason=reason.strip(),
        )

    @classmethod
    @transaction.atomic
    def request_correction(cls, *, document_id, tenant_id, reviewer, reason: str):
        from ..models.media import DocumentStatus

        if not reason or not reason.strip():
            raise VerificationReviewError("A reason is required to request a correction.")
        return cls._apply_review(
            document_id=document_id,
            tenant_id=tenant_id,
            reviewer=reviewer,
            target_status=DocumentStatus.CORRECTION_REQUIRED,
            reason=reason.strip(),
        )

    @classmethod
    def _apply_review(cls, *, document_id, tenant_id, reviewer, target_status, reason: str):
        from ..models.media import DocumentStatus, VerificationDocument

        try:
            document = VerificationDocument.objects.select_for_update().get(id=document_id)
        except VerificationDocument.DoesNotExist:
            raise AccountsError("Document not found.") from None

        # Re-derive tenant from the owner and compare to the caller's own
        # tenant_id BEFORE the permission check — a reviewer genuinely
        # authorized in their own tenant would otherwise pass
        # PermissionService.require() and only then discover the document
        # belongs elsewhere, leaking its existence.
        document_tenant_id = cls._tenant_id_for(document)
        if document_tenant_id != tenant_id:
            raise AccountsError("Document not found.")

        PermissionService.require(reviewer, ACCOUNTS_DOCUMENT_REVIEW, tenant_id=tenant_id)

        owner_user_id = cls._owner_user_id(document)
        if reviewer is not None and getattr(reviewer, "id", None) == owner_user_id:
            raise VerificationReviewError("A document owner cannot review their own document.")

        if document.status == target_status:
            return document  # idempotent no-op: already in the requested outcome

        if document.status != DocumentStatus.PENDING:
            raise VerificationReviewError(
                f"Cannot review a document in '{document.status}' status; only a PENDING document can be reviewed."
            )

        previous_status = document.status
        document.status = target_status
        document.reviewed_by = reviewer
        document.reviewed_at = timezone.now()
        document.rejection_reason = reason
        document.save(update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason", "updated_at"])

        AuditService.log(
            tenant_id=tenant_id,
            action=f"accounts.document.{target_status}",
            resource_type="VerificationDocument",
            resource_id=document.id,
            module_id=MODULE_ID,
            actor_id=getattr(reviewer, "person_id", None),
            actor_type="user" if reviewer else "system",
            before={"status": previous_status},
            after={"status": target_status},
            reason=reason,
            metadata={"owner_user_id": str(owner_user_id)},
        )

        # Keep the profile-level verification summary current — Phase 1.2
        # (Verification Completion and Activation Rules). Runs inside this
        # same transaction so the document's new status and the profile's
        # rolled-up verification_status are never observed out of sync.
        from .verification_rollup_service import ProfileVerificationRollupService

        if document.caregiver_id:
            ProfileVerificationRollupService.sync_caregiver(document.caregiver)
        else:
            ProfileVerificationRollupService.sync_organization(document.organization)

        return document

    @staticmethod
    def _tenant_id_for(document):
        return tenant_id_for_document(document)

    @staticmethod
    def _owner_user_id(document):
        return owner_user_id_for_document(document)
