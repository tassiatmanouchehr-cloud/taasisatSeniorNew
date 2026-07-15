"""DocumentService.resubmit() — Phase 1.2 Part C (Correction and
Resubmission Lifecycle)."""

import threading
import uuid

from django.apps import apps as django_apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, TransactionTestCase

from apps.accounts.models.media import DocumentStatus, DocumentType
from apps.accounts.models.profiles import CaregiverProfile, OrganizationProfile
from apps.accounts.permission_keys import ACCOUNTS_DOCUMENT_REVIEW
from apps.accounts.services.document_service import DocumentService
from apps.accounts.services.errors import AccountsError
from apps.accounts.services.verification_review_service import VerificationReviewService
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.audit import AuditLog
from apps.kernel.tests.rbac_helpers import grant_permissions

PDF_BYTES = b"%PDF-1.4 fake test content"


class _ResubmissionFixtureMixin:
    def _build_fixture(self):
        self.tenant = Tenant.objects.create(slug=f"resubmit-{uuid.uuid4().hex[:8]}", name="Resubmission Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"resubmit-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")
        self.caregiver = self._create_caregiver(tenant=self.tenant)
        self.other_caregiver = self._create_caregiver(tenant=self.tenant, full_name="Other Caregiver")
        self.reviewer = self._create_user(tenant=self.tenant, full_name="Reviewer")
        grant_permissions(self.tenant, self.reviewer, [ACCOUNTS_DOCUMENT_REVIEW])

    def _create_caregiver(self, *, tenant, full_name="Test Caregiver") -> CaregiverProfile:
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=full_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return CaregiverProfile.objects.create(user=user, person=person, phone=phone, display_name=full_name)

    def _create_organization(self, *, tenant, name="Test Org") -> OrganizationProfile:
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=f"{name} Admin")
        admin_user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return OrganizationProfile.objects.create(
            name=name, code=f"ORG-{uuid.uuid4().hex[:6].upper()}", admin_user=admin_user, tenant=tenant,
        )

    def _create_user(self, *, tenant, full_name="Test User") -> UserAccount:
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=full_name)
        return UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)

    def _upload(self, caregiver=None, organization=None, document_type=DocumentType.IDENTITY):
        file = SimpleUploadedFile("id.pdf", PDF_BYTES, content_type="application/pdf")
        if caregiver:
            return DocumentService.upload_caregiver_document(caregiver, document_type=document_type, file=file)
        return DocumentService.upload_organization_document(organization, document_type=document_type, file=file)

    def _new_file(self, name="id2.pdf"):
        return SimpleUploadedFile(name, PDF_BYTES, content_type="application/pdf")


class ResubmissionFromCorrectionRequiredTest(_ResubmissionFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_correction_required_returns_to_pending_on_owner_resubmit(self):
        document = self._upload(caregiver=self.caregiver)
        VerificationReviewService.request_correction(
            document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="upload back side",
        )
        document.refresh_from_db()
        self.assertEqual(document.status, DocumentStatus.CORRECTION_REQUIRED)

        DocumentService.resubmit(document, actor=self.caregiver.user, file=self._new_file())
        document.refresh_from_db()
        self.assertEqual(document.status, DocumentStatus.PENDING)
        self.assertEqual(document.rejection_reason, "")  # live field cleared, not the same as erasing history

    def test_rejected_document_can_also_be_resubmitted(self):
        document = self._upload(caregiver=self.caregiver)
        VerificationReviewService.reject(
            document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="bad scan",
        )
        DocumentService.resubmit(document, actor=self.caregiver.user, file=self._new_file())
        document.refresh_from_db()
        self.assertEqual(document.status, DocumentStatus.PENDING)


class ApprovedDocumentProtectionTest(_ResubmissionFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_verified_document_cannot_be_silently_replaced(self):
        document = self._upload(caregiver=self.caregiver)
        VerificationReviewService.approve(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer)
        with self.assertRaises(AccountsError):
            DocumentService.resubmit(document, actor=self.caregiver.user, file=self._new_file())
        document.refresh_from_db()
        self.assertEqual(document.status, DocumentStatus.VERIFIED)


class OwnershipAndTenantIsolationTest(_ResubmissionFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_only_owner_may_resubmit(self):
        document = self._upload(caregiver=self.caregiver)
        with self.assertRaises(AccountsError):
            DocumentService.resubmit(document, actor=self.other_caregiver.user, file=self._new_file())
        document.refresh_from_db()
        self.assertEqual(document.status, DocumentStatus.PENDING)  # unchanged, not silently accepted

    def test_reviewer_cannot_resubmit_on_owners_behalf(self):
        document = self._upload(caregiver=self.caregiver)
        with self.assertRaises(AccountsError):
            DocumentService.resubmit(document, actor=self.reviewer, file=self._new_file())

    def test_cross_tenant_actor_cannot_resubmit(self):
        document = self._upload(caregiver=self.caregiver)
        cross_tenant_user = self._create_user(tenant=self.other_tenant, full_name="Cross Tenant User")
        with self.assertRaises(AccountsError):
            DocumentService.resubmit(document, actor=cross_tenant_user, file=self._new_file())

    def test_organization_document_resubmission_scoped_to_admin_user(self):
        organization = self._create_organization(tenant=self.tenant)
        document = self._upload(organization=organization, document_type=DocumentType.REGISTRATION)
        VerificationReviewService.request_correction(
            document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="fix",
        )
        DocumentService.resubmit(document, actor=organization.admin_user, file=self._new_file())
        document.refresh_from_db()
        self.assertEqual(document.status, DocumentStatus.PENDING)


class AuditHistoryPreservedTest(_ResubmissionFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_original_review_reason_survives_in_audit_log_after_resubmission(self):
        document = self._upload(caregiver=self.caregiver)
        VerificationReviewService.request_correction(
            document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="upload back side",
        )
        DocumentService.resubmit(document, actor=self.caregiver.user, file=self._new_file())

        correction_entry = AuditLog.objects.get(
            tenant_id=self.tenant.id, resource_id=document.id, action="accounts.document.correction_required",
        )
        self.assertEqual(correction_entry.reason, "upload back side")  # never overwritten by resubmission

    def test_resubmission_itself_is_audited(self):
        document = self._upload(caregiver=self.caregiver)
        VerificationReviewService.request_correction(
            document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="fix",
        )
        DocumentService.resubmit(document, actor=self.caregiver.user, file=self._new_file())

        resubmit_entry = AuditLog.objects.filter(
            tenant_id=self.tenant.id, resource_id=document.id, action="accounts.document.resubmitted",
        ).latest("occurred_at")
        self.assertEqual(resubmit_entry.before_snapshot, {"status": "correction_required"})
        self.assertEqual(resubmit_entry.after_snapshot, {"status": "pending"})


class ResubmissionConcurrencyTest(_ResubmissionFixtureMixin, TransactionTestCase):
    available_apps = [app_config.name for app_config in django_apps.get_app_configs()]

    def setUp(self):
        self._build_fixture()

    def test_concurrent_resubmissions_are_serialized_not_corrupted(self):
        document = self._upload(caregiver=self.caregiver)
        VerificationReviewService.reject(
            document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="bad",
        )
        barrier = threading.Barrier(2)
        errors = []

        def _resubmit(filename):
            try:
                barrier.wait(timeout=10)
                DocumentService.resubmit(document, actor=self.caregiver.user, file=self._new_file(filename))
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
            finally:
                connection.close()

        threads = [
            threading.Thread(target=_resubmit, args=("a.pdf",)),
            threading.Thread(target=_resubmit, args=("b.pdf",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertEqual(errors, [])
        document.refresh_from_db()
        # Both resubmissions succeed (serialized by the row lock, not
        # rejected) — the final state is deterministic (whichever
        # committed last) and uncorrupted: exactly one stored file, still
        # PENDING, no orphaned exception from the old-file delete race.
        self.assertEqual(document.status, DocumentStatus.PENDING)
        self.assertTrue(document.file.name.endswith(".pdf"))
