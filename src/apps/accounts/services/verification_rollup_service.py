"""ProfileVerificationRollupService — Phase 1.2 (Verification Completion
and Activation Rules).

Derives a caregiver's/organization's summary `verification_status`
(`apps.accounts.models.profiles.VerificationStatus` — UNVERIFIED/PENDING/
VERIFIED/REJECTED, the field that already existed before Phase 1.1) from
the state of its currently-required `VerificationDocument` rows (Part A's
`RequiredDocumentPolicy`). Reuses that existing 4-value enum as-is — no
second source of truth, no new field, no migration.

`VerificationStatus` has no fifth value for "correction required", and it
does not need one: procedurally, a document sent back for correction is
in the same "not yet resolved, action needed, not a hard rejection" tier
as one still awaiting first review — both are represented as profile-
level PENDING. `evaluate_*()` still surfaces the distinction as its own
`needs_correction` flag on the returned `VerificationRollupResult`, so
nothing about "which required document actually needs correction vs. is
merely awaiting first review" is lost — it just isn't smuggled into the
4-value enum the rest of the platform already reads.

State derivation (in priority order, first match wins):
  - any required document REJECTED                                -> REJECTED
  - any required document CORRECTION_REQUIRED (none REJECTED)     -> PENDING, needs_correction=True
  - any required document missing/PENDING/effectively-expired     -> PENDING
    (none REJECTED/CORRECTION_REQUIRED)
  - every required document VERIFIED and not expired              -> VERIFIED

Optional document status never affects this computation.

`evaluate_*()` is a pure read (no writes, safe to call any number of
times). `sync_*()` additionally persists the result to the profile's
`verification_status` field — idempotent (a no-op write when the value
already matches) and safe under concurrent calls for the SAME profile
(row-locked via `select_for_update()`), which matters because two
different documents belonging to the same profile can be reviewed
concurrently by two different reviewers. `sync_*()` is the method
`VerificationReviewService`/`DocumentService.resubmit()` call — never
place this in a view, admin action, or signal (repository convention:
business rules live in the service layer only).
"""

from dataclasses import dataclass

from django.db import transaction

from ..models.media import DocumentStatus, VerificationDocument
from ..models.profiles import CaregiverProfile, OrganizationProfile, VerificationStatus
from .verification_policy import RequiredDocumentPolicy


@dataclass(frozen=True)
class VerificationRollupResult:
    verification_status: str
    needs_correction: bool
    blocking_document_types: tuple[str, ...]
    reasons: tuple[str, ...]


class ProfileVerificationRollupService:
    @classmethod
    def evaluate_caregiver(cls, caregiver: CaregiverProfile) -> VerificationRollupResult:
        required_types = RequiredDocumentPolicy.required_caregiver_document_types(
            tenant_id=caregiver.user.tenant_id,
        )
        documents = VerificationDocument.objects.filter(caregiver=caregiver)
        return cls._evaluate(required_types, documents)

    @classmethod
    def evaluate_organization(cls, organization: OrganizationProfile) -> VerificationRollupResult:
        required_types = RequiredDocumentPolicy.required_organization_document_types(
            tenant_id=organization.tenant_id,
        )
        documents = VerificationDocument.objects.filter(organization=organization)
        return cls._evaluate(required_types, documents)

    @classmethod
    @transaction.atomic
    def sync_caregiver(cls, caregiver: CaregiverProfile) -> VerificationRollupResult:
        locked = CaregiverProfile.objects.select_for_update().get(id=caregiver.id)
        result = cls.evaluate_caregiver(locked)
        if locked.verification_status != result.verification_status:
            locked.verification_status = result.verification_status
            locked.save(update_fields=["verification_status", "updated_at"])
        return result

    @classmethod
    @transaction.atomic
    def sync_organization(cls, organization: OrganizationProfile) -> VerificationRollupResult:
        locked = OrganizationProfile.objects.select_for_update().get(id=organization.id)
        result = cls.evaluate_organization(locked)
        if locked.verification_status != result.verification_status:
            locked.verification_status = result.verification_status
            locked.save(update_fields=["verification_status", "updated_at"])
        return result

    @staticmethod
    def _evaluate(required_types, documents) -> VerificationRollupResult:
        # Newest row per type wins — a profile should have at most one
        # live row per type (DocumentService.resubmit() mutates in place),
        # but nothing in the schema enforces that, so this stays
        # deliberately defensive rather than assuming it.
        latest_by_type = {}
        for document in documents.order_by("-created_at"):
            latest_by_type.setdefault(document.document_type, document)

        rejected, correction, pending_or_missing, expired = [], [], [], []
        for required_type in required_types:
            document = latest_by_type.get(required_type)
            if document is None:
                pending_or_missing.append(required_type)
            elif document.status == DocumentStatus.REJECTED:
                rejected.append(required_type)
            elif document.status == DocumentStatus.CORRECTION_REQUIRED:
                correction.append(required_type)
            elif document.status == DocumentStatus.PENDING:
                pending_or_missing.append(required_type)
            elif document.status == DocumentStatus.VERIFIED:
                if RequiredDocumentPolicy.is_effectively_expired(document):
                    expired.append(required_type)

        if rejected:
            return VerificationRollupResult(
                verification_status=VerificationStatus.REJECTED,
                needs_correction=False,
                blocking_document_types=tuple(rejected),
                reasons=tuple(f"rejected:{t}" for t in rejected),
            )
        if correction:
            return VerificationRollupResult(
                verification_status=VerificationStatus.PENDING,
                needs_correction=True,
                blocking_document_types=tuple(correction),
                reasons=tuple(f"correction_required:{t}" for t in correction),
            )
        if pending_or_missing or expired:
            reasons = tuple(f"pending_or_missing:{t}" for t in pending_or_missing) + tuple(
                f"expired:{t}" for t in expired
            )
            return VerificationRollupResult(
                verification_status=VerificationStatus.PENDING,
                needs_correction=False,
                blocking_document_types=tuple(pending_or_missing) + tuple(expired),
                reasons=reasons,
            )
        return VerificationRollupResult(
            verification_status=VerificationStatus.VERIFIED,
            needs_correction=False,
            blocking_document_types=(),
            reasons=(),
        )
