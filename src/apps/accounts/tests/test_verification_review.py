"""VerificationReviewService — Phase 1.1 (Manual Document Verification).

Uses PostgreSQL (project default test settings). Concurrency test mirrors
apps.booking.tests.test_concurrency's TransactionTestCase shape exactly.
"""

import threading
import uuid

from django.apps import apps as django_apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, TransactionTestCase

from apps.accounts.models.media import DocumentStatus, DocumentType, VerificationDocument
from apps.accounts.models.profiles import CaregiverProfile, OrganizationProfile
from apps.accounts.permission_keys import ACCOUNTS_DOCUMENT_REVIEW
from apps.accounts.services.document_service import DocumentService
from apps.accounts.services.errors import AccountsError
from apps.accounts.services.verification_review_service import (
    VerificationReviewError,
    VerificationReviewService,
)
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.tests.rbac_helpers import grant_permissions

PDF_BYTES = b"%PDF-1.4 fake test content"


class _VerificationFixtureMixin:
    def _build_fixture(self):
        self.tenant = Tenant.objects.create(slug=f"verify-{uuid.uuid4().hex[:8]}", name="Verification Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"verify-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        self.caregiver = self._create_caregiver(tenant=self.tenant)
        self.organization = self._create_organization(tenant=self.tenant)
        self.reviewer = self._create_user(tenant=self.tenant, full_name="Reviewer")
        self.customer_actor = self._create_user(tenant=self.tenant, full_name="Ordinary Customer")

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

    def _upload_caregiver_document(self, caregiver=None):
        caregiver = caregiver or self.caregiver
        return DocumentService.upload_caregiver_document(
            caregiver,
            document_type=DocumentType.IDENTITY,
            file=SimpleUploadedFile("id.pdf", PDF_BYTES, content_type="application/pdf"),
        )

    def _upload_organization_document(self, organization=None):
        organization = organization or self.organization
        return DocumentService.upload_organization_document(
            organization,
            document_type=DocumentType.REGISTRATION,
            file=SimpleUploadedFile("reg.pdf", PDF_BYTES, content_type="application/pdf"),
        )

    def _grant_review(self, user, tenant=None):
        grant_permissions(tenant or self.tenant, user, [ACCOUNTS_DOCUMENT_REVIEW])


class UploadInitialStateTest(_VerificationFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_caregiver_document_upload_enters_pending(self):
        document = self._upload_caregiver_document()
        self.assertEqual(document.status, DocumentStatus.PENDING)

    def test_organization_document_upload_enters_pending(self):
        document = self._upload_organization_document()
        self.assertEqual(document.status, DocumentStatus.PENDING)


class ApproveTest(_VerificationFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()
        self._grant_review(self.reviewer)

    def test_authorized_reviewer_can_approve_caregiver_document(self):
        document = self._upload_caregiver_document()
        result = VerificationReviewService.approve(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer)
        self.assertEqual(result.status, DocumentStatus.VERIFIED)
        self.assertEqual(result.reviewed_by_id, self.reviewer.id)
        self.assertIsNotNone(result.reviewed_at)

    def test_authorized_reviewer_can_approve_organization_document(self):
        document = self._upload_organization_document()
        result = VerificationReviewService.approve(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer)
        self.assertEqual(result.status, DocumentStatus.VERIFIED)


class RejectTest(_VerificationFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()
        self._grant_review(self.reviewer)

    def test_authorized_reviewer_can_reject_with_reason(self):
        document = self._upload_caregiver_document()
        result = VerificationReviewService.reject(
            document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="Blurry scan",
        )
        self.assertEqual(result.status, DocumentStatus.REJECTED)
        self.assertEqual(result.rejection_reason, "Blurry scan")

    def test_reject_requires_a_reason(self):
        document = self._upload_caregiver_document()
        with self.assertRaises(VerificationReviewError):
            VerificationReviewService.reject(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="")

    def test_reject_requires_a_non_whitespace_reason(self):
        document = self._upload_caregiver_document()
        with self.assertRaises(VerificationReviewError):
            VerificationReviewService.reject(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="   ")


class RequestCorrectionTest(_VerificationFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()
        self._grant_review(self.reviewer)

    def test_authorized_reviewer_can_request_correction(self):
        document = self._upload_caregiver_document()
        result = VerificationReviewService.request_correction(
            document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="Upload the back side too",
        )
        self.assertEqual(result.status, DocumentStatus.CORRECTION_REQUIRED)
        self.assertEqual(result.rejection_reason, "Upload the back side too")

    def test_request_correction_requires_a_reason(self):
        document = self._upload_caregiver_document()
        with self.assertRaises(VerificationReviewError):
            VerificationReviewService.request_correction(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="")

    def test_correction_required_returns_to_pending_on_resubmission(self):
        """CORRECTION_REQUIRED -> PENDING happens via the owner's existing
        upload/replace flow — no new code needed, only proof it still works."""
        document = self._upload_caregiver_document()
        VerificationReviewService.request_correction(
            document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="Fix lighting",
        )
        document.refresh_from_db()
        self.assertEqual(document.status, DocumentStatus.CORRECTION_REQUIRED)

        DocumentService.replace_document(
            document, file=SimpleUploadedFile("id2.pdf", PDF_BYTES, content_type="application/pdf"),
        )
        document.refresh_from_db()
        self.assertEqual(document.status, DocumentStatus.PENDING)
        self.assertEqual(document.rejection_reason, "")


class IllegalTransitionTest(_VerificationFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()
        self._grant_review(self.reviewer)

    def test_cannot_reject_an_already_approved_document(self):
        document = self._upload_caregiver_document()
        VerificationReviewService.approve(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer)
        with self.assertRaises(VerificationReviewError):
            VerificationReviewService.reject(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="changed my mind")
        document.refresh_from_db()
        self.assertEqual(document.status, DocumentStatus.VERIFIED)  # not silently overwritten

    def test_cannot_approve_an_already_rejected_document(self):
        document = self._upload_caregiver_document()
        VerificationReviewService.reject(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="bad scan")
        with self.assertRaises(VerificationReviewError):
            VerificationReviewService.approve(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer)


class IdempotencyTest(_VerificationFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()
        self._grant_review(self.reviewer)

    def test_repeated_approve_is_idempotent(self):
        document = self._upload_caregiver_document()
        first = VerificationReviewService.approve(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer)
        second = VerificationReviewService.approve(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer)
        self.assertEqual(first.status, DocumentStatus.VERIFIED)
        self.assertEqual(second.status, DocumentStatus.VERIFIED)

    def test_repeated_reject_with_same_outcome_is_idempotent(self):
        document = self._upload_caregiver_document()
        VerificationReviewService.reject(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="bad scan")
        # Second call with a different reason is still a no-op on an already-REJECTED document.
        result = VerificationReviewService.reject(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="different reason")
        self.assertEqual(result.status, DocumentStatus.REJECTED)
        self.assertEqual(result.rejection_reason, "bad scan")  # unchanged — no-op, not re-applied


class AuditRecordTest(_VerificationFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()
        self._grant_review(self.reviewer)

    def test_approve_creates_audit_log_entry(self):
        from apps.kernel.models.audit import AuditLog

        document = self._upload_caregiver_document()
        VerificationReviewService.approve(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer)

        entry = AuditLog.objects.filter(
            tenant_id=self.tenant.id, resource_type="VerificationDocument", resource_id=document.id,
        ).latest("occurred_at")
        self.assertEqual(entry.action, "accounts.document.verified")
        self.assertEqual(entry.before_snapshot, {"status": "pending"})
        self.assertEqual(entry.after_snapshot, {"status": "verified"})

    def test_reject_audit_log_records_reason(self):
        from apps.kernel.models.audit import AuditLog

        document = self._upload_caregiver_document()
        VerificationReviewService.reject(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="bad scan")

        entry = AuditLog.objects.filter(
            tenant_id=self.tenant.id, resource_type="VerificationDocument", resource_id=document.id,
        ).latest("occurred_at")
        self.assertEqual(entry.reason, "bad scan")


class CrossTenantAndSecurityTest(_VerificationFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()
        self._grant_review(self.reviewer)

    def test_cross_tenant_review_is_denied(self):
        document = self._upload_caregiver_document()
        other_reviewer = self._create_user(tenant=self.other_tenant, full_name="Other Tenant Reviewer")
        self._grant_review(other_reviewer, tenant=self.other_tenant)

        with self.assertRaises(AccountsError):
            VerificationReviewService.approve(document_id=document.id, tenant_id=self.other_tenant.id, reviewer=other_reviewer)
        document.refresh_from_db()
        self.assertEqual(document.status, DocumentStatus.PENDING)

    def test_get_document_for_tenant_denies_cross_tenant_lookup(self):
        document = self._upload_caregiver_document()
        with self.assertRaises(AccountsError):
            VerificationReviewService.get_document_for_tenant(tenant_id=self.other_tenant.id, document_id=document.id)

    def test_ordinary_customer_without_permission_is_denied(self):
        from apps.kernel.services.errors import PermissionDenied

        document = self._upload_caregiver_document()
        with self.assertRaises(PermissionDenied):
            VerificationReviewService.approve(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.customer_actor)
        document.refresh_from_db()
        self.assertEqual(document.status, DocumentStatus.PENDING)

    def test_caregiver_cannot_self_approve_even_if_granted_permission(self):
        """Defense in depth: even if a caregiver's own user account were
        granted accounts.document.review, self-review is still refused."""
        document = self._upload_caregiver_document()
        self._grant_review(self.caregiver.user)

        with self.assertRaises(VerificationReviewError):
            VerificationReviewService.approve(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.caregiver.user)
        document.refresh_from_db()
        self.assertEqual(document.status, DocumentStatus.PENDING)

    def test_organization_admin_cannot_self_approve_own_document(self):
        document = self._upload_organization_document()
        self._grant_review(self.organization.admin_user)

        with self.assertRaises(VerificationReviewError):
            VerificationReviewService.approve(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.organization.admin_user)

    def test_organization_user_without_permission_denied_from_unauthorized_review(self):
        from apps.kernel.services.errors import PermissionDenied

        document = self._upload_organization_document()
        other_org = self._create_organization(tenant=self.tenant, name="Other Org")
        with self.assertRaises(PermissionDenied):
            VerificationReviewService.approve(document_id=document.id, tenant_id=self.tenant.id, reviewer=other_org.admin_user)


class OwnerVisibilityTest(_VerificationFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()
        self._grant_review(self.reviewer)

    def test_owner_sees_status_and_correction_reason_via_existing_fields(self):
        document = self._upload_caregiver_document()
        VerificationReviewService.request_correction(
            document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="Please upload a clearer photo",
        )
        # The owner-facing surface (DocumentService.list_for_caregiver, rendered
        # by document_upload.html) reads these same model fields directly.
        owned = DocumentService.get_owned_document(document.id, caregiver=self.caregiver)
        self.assertEqual(owned.status, DocumentStatus.CORRECTION_REQUIRED)
        self.assertEqual(owned.rejection_reason, "Please upload a clearer photo")


class PrivateFileTest(_VerificationFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_document_file_stored_under_private_path_not_public_media_url(self):
        document = self._upload_caregiver_document()
        self.assertIn("private/", document.file.name)
        self.assertNotIn("public/", document.file.name)


class VerificationReviewConcurrencyTest(_VerificationFixtureMixin, TransactionTestCase):
    """Mirrors apps.booking.tests.test_concurrency: TransactionTestCase,
    threading.Barrier, separate connections, available_apps=all installed
    apps so the post-test flush can TRUNCATE with cascade."""

    available_apps = [app_config.name for app_config in django_apps.get_app_configs()]

    def setUp(self):
        self._build_fixture()
        self._grant_review(self.reviewer)

    def test_concurrent_conflicting_reviews_result_in_exactly_one_success(self):
        document = self._upload_caregiver_document()
        barrier = threading.Barrier(2)
        errors = []
        successes = []

        def _attempt(target):
            try:
                barrier.wait(timeout=10)
                if target == "approve":
                    VerificationReviewService.approve(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer)
                else:
                    VerificationReviewService.reject(document_id=document.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="concurrent reject")
                successes.append(target)
            except VerificationReviewError:
                errors.append(target)
            finally:
                connection.close()

        threads = [
            threading.Thread(target=_attempt, args=("approve",)),
            threading.Thread(target=_attempt, args=("reject",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertEqual(len(successes), 1, f"expected exactly one success, got {successes}")
        self.assertEqual(len(errors), 1, f"expected exactly one controlled error, got {errors}")
        document.refresh_from_db()
        self.assertIn(document.status, (DocumentStatus.VERIFIED, DocumentStatus.REJECTED))
