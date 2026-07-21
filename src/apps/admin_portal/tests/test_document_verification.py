"""Manual document verification — Phase 1.1. View-layer authorization and
security tests; business-rule tests live in
apps.accounts.tests.test_verification_review."""

import uuid

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models.media import DocumentStatus, DocumentType
from apps.accounts.models.profiles import CaregiverProfile, OrganizationProfile
from apps.accounts.permission_keys import ACCOUNTS_DOCUMENT_REVIEW
from apps.accounts.services.document_service import DocumentService
from apps.kernel.models import Person, UserAccount

from .helpers import AdminPortalTestCase

PDF_BYTES = b"%PDF-1.4 fake test content"


class DocumentVerificationTestCase(AdminPortalTestCase):
    def setUp(self):
        super().setUp()
        self.caregiver = self._create_caregiver(tenant=self.tenant)
        self.document = DocumentService.upload_caregiver_document(
            self.caregiver,
            document_type=DocumentType.IDENTITY,
            file=SimpleUploadedFile("id.pdf", PDF_BYTES, content_type="application/pdf"),
        )

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
            name=name,
            code=f"ORG-{uuid.uuid4().hex[:6].upper()}",
            admin_user=admin_user,
            tenant=tenant,
        )


class QueueAndDetailAccessTest(DocumentVerificationTestCase):
    def test_unauthenticated_denied_queue(self):
        response = self.client.get("/admin-portal/verification/documents/")
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_denied_detail(self):
        response = self.client.get(f"/admin-portal/verification/documents/{self.document.id}/")
        self.assertEqual(response.status_code, 403)

    def test_ordinary_actor_without_permission_denied(self):
        self.client.force_login(self.actor)
        response = self.client.get("/admin-portal/verification/documents/")
        self.assertEqual(response.status_code, 403)

    def test_authorized_reviewer_sees_pending_document_in_queue(self):
        self._grant(self.actor, self.tenant, [ACCOUNTS_DOCUMENT_REVIEW])
        self.client.force_login(self.actor)

        response = self.client.get("/admin-portal/verification/documents/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.caregiver.display_name)

    def test_authorized_reviewer_can_open_detail_page(self):
        self._grant(self.actor, self.tenant, [ACCOUNTS_DOCUMENT_REVIEW])
        self.client.force_login(self.actor)

        response = self.client.get(f"/admin-portal/verification/documents/{self.document.id}/")
        self.assertEqual(response.status_code, 200)

    def test_cross_tenant_document_returns_404(self):
        other_actor = self._create_actor(tenant=self.other_tenant)
        self._grant(other_actor, self.other_tenant, [ACCOUNTS_DOCUMENT_REVIEW])
        self.client.force_login(other_actor)

        response = self.client.get(f"/admin-portal/verification/documents/{self.document.id}/")
        self.assertEqual(response.status_code, 404)


class PrivateFileAccessTest(DocumentVerificationTestCase):
    def test_unauthenticated_cannot_fetch_file(self):
        response = self.client.get(f"/admin-portal/verification/documents/{self.document.id}/file/")
        self.assertEqual(response.status_code, 403)

    def test_actor_without_permission_cannot_fetch_file(self):
        self.client.force_login(self.actor)
        response = self.client.get(f"/admin-portal/verification/documents/{self.document.id}/file/")
        self.assertEqual(response.status_code, 403)

    def test_authorized_reviewer_can_fetch_file(self):
        self._grant(self.actor, self.tenant, [ACCOUNTS_DOCUMENT_REVIEW])
        self.client.force_login(self.actor)

        response = self.client.get(f"/admin-portal/verification/documents/{self.document.id}/file/")
        self.assertEqual(response.status_code, 200)

    def test_cross_tenant_reviewer_cannot_fetch_file(self):
        other_actor = self._create_actor(tenant=self.other_tenant)
        self._grant(other_actor, self.other_tenant, [ACCOUNTS_DOCUMENT_REVIEW])
        self.client.force_login(other_actor)

        response = self.client.get(f"/admin-portal/verification/documents/{self.document.id}/file/")
        self.assertEqual(response.status_code, 404)


class ReviewActionTest(DocumentVerificationTestCase):
    def test_unauthenticated_cannot_post_review(self):
        response = self.client.post(
            f"/admin-portal/verification/documents/{self.document.id}/review/",
            {"action": "approve", "reason": ""},
        )
        self.assertEqual(response.status_code, 403)

    def test_authorized_reviewer_can_approve_end_to_end(self):
        self._grant(self.actor, self.tenant, [ACCOUNTS_DOCUMENT_REVIEW])
        self.client.force_login(self.actor)

        response = self.client.post(
            f"/admin-portal/verification/documents/{self.document.id}/review/",
            {"action": "approve", "reason": ""},
        )
        self.assertEqual(response.status_code, 302)
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, DocumentStatus.VERIFIED)

    def test_authorized_reviewer_reject_without_reason_does_not_change_status(self):
        self._grant(self.actor, self.tenant, [ACCOUNTS_DOCUMENT_REVIEW])
        self.client.force_login(self.actor)

        self.client.post(
            f"/admin-portal/verification/documents/{self.document.id}/review/",
            {"action": "reject", "reason": ""},
        )
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, DocumentStatus.PENDING)

    def test_authorized_reviewer_can_request_correction_with_reason(self):
        self._grant(self.actor, self.tenant, [ACCOUNTS_DOCUMENT_REVIEW])
        self.client.force_login(self.actor)

        self.client.post(
            f"/admin-portal/verification/documents/{self.document.id}/review/",
            {"action": "request_correction", "reason": "Please resubmit a clearer scan"},
        )
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, DocumentStatus.CORRECTION_REQUIRED)
        self.assertEqual(self.document.rejection_reason, "Please resubmit a clearer scan")

    def test_caregiver_cannot_self_review_own_document(self):
        self._grant(self.caregiver.user, self.tenant, [ACCOUNTS_DOCUMENT_REVIEW])
        self.client.force_login(self.caregiver.user)

        self.client.post(
            f"/admin-portal/verification/documents/{self.document.id}/review/",
            {"action": "approve", "reason": ""},
        )
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, DocumentStatus.PENDING)  # refused, not silently applied

    def test_organization_document_cross_tenant_review_denied(self):
        organization = self._create_organization(tenant=self.other_tenant)
        document = DocumentService.upload_organization_document(
            organization,
            document_type=DocumentType.REGISTRATION,
            file=SimpleUploadedFile("reg.pdf", PDF_BYTES, content_type="application/pdf"),
        )
        self._grant(self.actor, self.tenant, [ACCOUNTS_DOCUMENT_REVIEW])
        self.client.force_login(self.actor)

        response = self.client.post(
            f"/admin-portal/verification/documents/{document.id}/review/",
            {"action": "approve", "reason": ""},
        )
        self.assertEqual(response.status_code, 404)
        document.refresh_from_db()
        self.assertEqual(document.status, DocumentStatus.PENDING)
