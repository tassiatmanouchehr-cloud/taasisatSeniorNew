"""
VerificationDocument — Epic 06 Sprint 2 (Shared Portal UI Core, Provider
Profile, Organization Profile).

Before this model, `CaregiverProfile.verification_status`/
`OrganizationProfile.verification_status` were pure status enums with no
evidence behind them — flipping either to VERIFIED required no uploaded
proof of any kind. This model is the minimal reusable evidence store this
Sprint's "smallest correct media foundation" scope calls for: one document
row per uploaded file, linked to exactly one of a caregiver or an
organization (never both, never neither — enforced by both a database
CHECK constraint and model-level validation), carrying its own
per-document status independent of the profile-level
`verification_status` summary field.

Deliberately NOT a polymorphic `linked_entity_id`/`linked_entity_type`
table (the pattern `apps.kernel.models.supplier.ServiceSupplier` uses for
its own, cross-app, necessarily-generic purpose) — both possible owners
here (`CaregiverProfile`, `OrganizationProfile`) already live in this
same app, so two plain nullable FKs plus a mutual-exclusion constraint is
simpler, is validated by the database itself (a polymorphic string-typed
link cannot be), and creates no cross-domain ownership ambiguity.

Upload only ever creates a PENDING-status row (see
`apps.accounts.services.document_service.DocumentService`) — nothing in
this Sprint ever sets VERIFIED/REJECTED; that remains reserved for a
future platform-admin verification workflow, which does not exist yet
(see this Sprint's own scope notes) and is explicitly not built here.
"""

import uuid

from django.conf import settings
from django.db import models

from .media_paths import verification_document_path


class DocumentType(models.TextChoices):
    IDENTITY = "identity", "Identity"
    BACKGROUND_CHECK = "background_check", "Background Check"
    QUALIFICATION = "qualification", "Qualification"
    TRAINING_CERTIFICATE = "training_certificate", "Training Certificate"
    LICENSE = "license", "License"
    REGISTRATION = "registration", "Registration"
    OPERATING_LICENSE = "operating_license", "Operating License"
    INSURANCE = "insurance", "Insurance"
    PROFESSIONAL_PERMIT = "professional_permit", "Professional Permit"


class DocumentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"


class VerificationDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    caregiver = models.ForeignKey(
        "accounts.CaregiverProfile",
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )
    organization = models.ForeignKey(
        "accounts.OrganizationProfile",
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    file = models.FileField(upload_to=verification_document_path)
    status = models.CharField(max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.PENDING)
    expiry_date = models.DateField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    """Staff-authored, internal-only — never rendered on any provider/
    organization-facing or public page (see this Sprint's explicit "never
    expose ... internal rejection reasons intended only for staff")."""
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_verification_document"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(caregiver__isnull=False, organization__isnull=True)
                    | models.Q(caregiver__isnull=True, organization__isnull=False)
                ),
                name="verification_document_exactly_one_owner",
            ),
        ]
        indexes = [
            models.Index(fields=["caregiver", "document_type"]),
            models.Index(fields=["organization", "document_type"]),
        ]

    def __str__(self):
        owner = self.caregiver_id or self.organization_id
        return f"{self.get_document_type_display()} ({self.status}) — owner={owner}"
