"""
PublicCredentialSelector — Phase 2.1 (Caregiver Professional Profile
Foundation).

Read-only. Derives the safe, public-facing credential summary for a
caregiver's public profile from `VerificationDocument` — never returns
the model itself to a caller, and never includes anything the model
docstring (`apps/accounts/models/media.py`) or this phase's own
governance marks private: no `file`, no document number (not modeled at
all — nothing to leak), no reviewer identity, no rejection/correction
reason, no internal audit data.

A document contributes to the public summary only if it is:
  - APPROVED (`DocumentStatus.VERIFIED`)
  - not effectively expired (`RequiredDocumentPolicy.is_effectively_expired()`,
    Phase 1.2's own existing expiry rule — reused, not reimplemented)
  - owned by the caregiver being queried (enforced by the queryset filter,
    never by trusting a caller-supplied ownership claim)
  - one of the document types this phase's own applicable-type universe
    already recognizes for caregivers (`CAREGIVER_APPLICABLE_DOCUMENT_TYPES`,
    Phase 1.2 — reused, not reinvented)

Deliberately does not surface "issuing organization" or a distinct
"public credential title" — `VerificationDocument` stores neither as
public metadata, and this phase's governance explicitly forbids
inventing a presentational field with no model to back it ("only if
stored as public metadata" / "only if safe and explicitly modeled").
The document type's own label is the only public "title".
"""

from dataclasses import dataclass

from ..models.media import DocumentStatus
from .verification_policy import CAREGIVER_APPLICABLE_DOCUMENT_TYPES, RequiredDocumentPolicy

PUBLIC_CREDENTIAL_LABELS = {
    "identity": "احراز هویت",
    "background_check": "بررسی سوءپیشینه",
    "qualification": "مدرک تخصصی",
    "training_certificate": "گواهی آموزشی",
    "license": "پروانه فعالیت",
}


@dataclass(frozen=True)
class PublicCredentialSummary:
    document_type: str
    label: str
    expiry_date: object  # date | None — shown only when the document has one


class PublicCredentialSelector:
    @classmethod
    def for_caregiver(cls, caregiver) -> tuple[PublicCredentialSummary, ...]:
        documents = caregiver.documents.filter(
            status=DocumentStatus.VERIFIED,
            document_type__in=CAREGIVER_APPLICABLE_DOCUMENT_TYPES,
        )
        summaries = []
        for document in documents:
            if RequiredDocumentPolicy.is_effectively_expired(document):
                continue
            summaries.append(
                PublicCredentialSummary(
                    document_type=document.document_type,
                    label=PUBLIC_CREDENTIAL_LABELS.get(document.document_type, document.document_type),
                    expiry_date=document.expiry_date,
                ),
            )
        return tuple(summaries)
