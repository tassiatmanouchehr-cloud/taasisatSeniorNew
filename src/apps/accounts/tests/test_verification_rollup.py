"""ProfileVerificationRollupService — Phase 1.2 Part B."""

import threading
import uuid
from datetime import timedelta

from django.apps import apps as django_apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.accounts.models.media import DocumentStatus, DocumentType
from apps.accounts.models.profiles import CaregiverProfile, OrganizationProfile, VerificationStatus
from apps.accounts.permission_keys import ACCOUNTS_DOCUMENT_REVIEW
from apps.accounts.services.document_service import DocumentService
from apps.accounts.services.verification_review_service import VerificationReviewService
from apps.accounts.services.verification_rollup_service import ProfileVerificationRollupService
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.tests.rbac_helpers import grant_permissions

PDF_BYTES = b"%PDF-1.4 fake test content"


class _RollupFixtureMixin:
    def _build_fixture(self):
        self.tenant = Tenant.objects.create(slug=f"rollup-{uuid.uuid4().hex[:8]}", name="Rollup Test Tenant")
        self.caregiver = self._create_caregiver(tenant=self.tenant)
        self.organization = self._create_organization(tenant=self.tenant)
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

    def _upload(self, *, document_type, caregiver=None, organization=None):
        file = SimpleUploadedFile(f"{document_type}.pdf", PDF_BYTES, content_type="application/pdf")
        if caregiver:
            return DocumentService.upload_caregiver_document(caregiver, document_type=document_type, file=file)
        return DocumentService.upload_organization_document(organization, document_type=document_type, file=file)

    def _review(self, document, action, reason=""):
        kwargs = {"document_id": document.id, "tenant_id": self.tenant.id, "reviewer": self.reviewer}
        if action == "approve":
            return VerificationReviewService.approve(**kwargs)
        if action == "reject":
            return VerificationReviewService.reject(reason=reason or "no", **kwargs)
        return VerificationReviewService.request_correction(reason=reason or "fix", **kwargs)


class NoDocumentsTest(_RollupFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_caregiver_with_no_documents_is_pending(self):
        result = ProfileVerificationRollupService.evaluate_caregiver(self.caregiver)
        self.assertEqual(result.verification_status, VerificationStatus.PENDING)
        self.assertFalse(result.needs_correction)
        self.assertIn(DocumentType.IDENTITY, result.blocking_document_types)


class AllApprovedTest(_RollupFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_caregiver_verified_when_all_required_approved(self):
        for doc_type in (DocumentType.IDENTITY, DocumentType.BACKGROUND_CHECK):
            doc = self._upload(document_type=doc_type, caregiver=self.caregiver)
            self._review(doc, "approve")
        result = ProfileVerificationRollupService.evaluate_caregiver(self.caregiver)
        self.assertEqual(result.verification_status, VerificationStatus.VERIFIED)
        self.assertEqual(result.blocking_document_types, ())

    def test_organization_verified_when_all_required_approved(self):
        for doc_type in (DocumentType.REGISTRATION, DocumentType.OPERATING_LICENSE):
            doc = self._upload(document_type=doc_type, organization=self.organization)
            self._review(doc, "approve")
        result = ProfileVerificationRollupService.evaluate_organization(self.organization)
        self.assertEqual(result.verification_status, VerificationStatus.VERIFIED)

    def test_optional_document_status_does_not_block_verification(self):
        for doc_type in (DocumentType.IDENTITY, DocumentType.BACKGROUND_CHECK):
            doc = self._upload(document_type=doc_type, caregiver=self.caregiver)
            self._review(doc, "approve")
        optional_doc = self._upload(document_type=DocumentType.QUALIFICATION, caregiver=self.caregiver)
        self._review(optional_doc, "reject", reason="not clear")
        result = ProfileVerificationRollupService.evaluate_caregiver(self.caregiver)
        self.assertEqual(result.verification_status, VerificationStatus.VERIFIED)


class PartialStateTest(_RollupFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_one_pending_required_document_keeps_profile_pending(self):
        approved = self._upload(document_type=DocumentType.IDENTITY, caregiver=self.caregiver)
        self._review(approved, "approve")
        self._upload(document_type=DocumentType.BACKGROUND_CHECK, caregiver=self.caregiver)  # left PENDING
        result = ProfileVerificationRollupService.evaluate_caregiver(self.caregiver)
        self.assertEqual(result.verification_status, VerificationStatus.PENDING)
        self.assertFalse(result.needs_correction)

    def test_one_rejected_required_document_rejects_profile(self):
        doc = self._upload(document_type=DocumentType.IDENTITY, caregiver=self.caregiver)
        self._review(doc, "reject", reason="blurry")
        self._upload(document_type=DocumentType.BACKGROUND_CHECK, caregiver=self.caregiver)
        result = ProfileVerificationRollupService.evaluate_caregiver(self.caregiver)
        self.assertEqual(result.verification_status, VerificationStatus.REJECTED)

    def test_one_correction_required_document_marks_needs_correction(self):
        doc = self._upload(document_type=DocumentType.IDENTITY, caregiver=self.caregiver)
        self._review(doc, "correction", reason="upload back side too")
        approved = self._upload(document_type=DocumentType.BACKGROUND_CHECK, caregiver=self.caregiver)
        self._review(approved, "approve")
        result = ProfileVerificationRollupService.evaluate_caregiver(self.caregiver)
        self.assertEqual(result.verification_status, VerificationStatus.PENDING)
        self.assertTrue(result.needs_correction)

    def test_rejected_takes_priority_over_correction_required(self):
        rejected = self._upload(document_type=DocumentType.IDENTITY, caregiver=self.caregiver)
        self._review(rejected, "reject", reason="bad")
        correction = self._upload(document_type=DocumentType.BACKGROUND_CHECK, caregiver=self.caregiver)
        self._review(correction, "correction", reason="fix")
        result = ProfileVerificationRollupService.evaluate_caregiver(self.caregiver)
        self.assertEqual(result.verification_status, VerificationStatus.REJECTED)


class ExpiryTest(_RollupFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_expired_required_document_blocks_verified(self):
        doc = self._upload(document_type=DocumentType.IDENTITY, caregiver=self.caregiver)
        self._review(doc, "approve")
        doc.refresh_from_db()
        doc.expiry_date = timezone.now().date() - timedelta(days=1)
        doc.save(update_fields=["expiry_date"])

        approved = self._upload(document_type=DocumentType.BACKGROUND_CHECK, caregiver=self.caregiver)
        self._review(approved, "approve")

        result = ProfileVerificationRollupService.evaluate_caregiver(self.caregiver)
        self.assertEqual(result.verification_status, VerificationStatus.PENDING)
        self.assertIn(DocumentType.IDENTITY, result.blocking_document_types)


class SyncPersistenceTest(_RollupFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_sync_persists_verification_status_to_profile(self):
        for doc_type in (DocumentType.IDENTITY, DocumentType.BACKGROUND_CHECK):
            doc = self._upload(document_type=doc_type, caregiver=self.caregiver)
            self._review(doc, "approve")
        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.verification_status, VerificationStatus.VERIFIED)

    def test_review_action_triggers_sync_automatically(self):
        """VerificationReviewService itself calls sync_* — proving the
        roll-up is wired into the service layer, not left to a view."""
        doc = self._upload(document_type=DocumentType.IDENTITY, caregiver=self.caregiver)
        self._review(doc, "reject", reason="bad scan")
        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.verification_status, VerificationStatus.REJECTED)

    def test_sync_is_idempotent_no_op_when_already_correct(self):
        for doc_type in (DocumentType.IDENTITY, DocumentType.BACKGROUND_CHECK):
            doc = self._upload(document_type=doc_type, caregiver=self.caregiver)
            self._review(doc, "approve")
        self.caregiver.refresh_from_db()
        first_updated_at = self.caregiver.updated_at

        result = ProfileVerificationRollupService.sync_caregiver(self.caregiver)
        self.caregiver.refresh_from_db()

        self.assertEqual(result.verification_status, VerificationStatus.VERIFIED)
        self.assertEqual(self.caregiver.updated_at, first_updated_at)  # no write happened


class RollupConcurrencyTest(_RollupFixtureMixin, TransactionTestCase):
    """Two different required documents of the SAME caregiver reviewed
    concurrently by two different reviewer threads — proves sync_caregiver's
    row lock keeps the final rolled-up status consistent with whichever
    review actually committed last, never a stale intermediate read."""

    available_apps = [app_config.name for app_config in django_apps.get_app_configs()]

    def setUp(self):
        self._build_fixture()
        self.doc_a = self._upload(document_type=DocumentType.IDENTITY, caregiver=self.caregiver)
        self.doc_b = self._upload(document_type=DocumentType.BACKGROUND_CHECK, caregiver=self.caregiver)

    def test_concurrent_approvals_of_different_documents_leave_consistent_rollup(self):
        barrier = threading.Barrier(2)
        errors = []

        def _approve(document_id):
            try:
                barrier.wait(timeout=10)
                VerificationReviewService.approve(document_id=document_id, tenant_id=self.tenant.id, reviewer=self.reviewer)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
            finally:
                connection.close()

        threads = [
            threading.Thread(target=_approve, args=(self.doc_a.id,)),
            threading.Thread(target=_approve, args=(self.doc_b.id,)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertEqual(errors, [])
        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.verification_status, VerificationStatus.VERIFIED)
