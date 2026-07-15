"""Shared owner/tenant resolution for `VerificationDocument` — Phase 1.2
(Verification Completion and Activation Rules).

Both `VerificationReviewService` (platform review) and
`DocumentService.resubmit()` (owner resubmission) need to answer the same
two questions about a document — "which tenant does it belong to" and
"who is its owner user" — extracted here once so the two call sites can
never diverge on the answer.
"""


def tenant_id_for_document(document):
    if document.caregiver_id:
        return document.caregiver.user.tenant_id
    return document.organization.tenant_id


def owner_user_id_for_document(document):
    if document.caregiver_id:
        return document.caregiver.user_id
    return document.organization.admin_user_id
