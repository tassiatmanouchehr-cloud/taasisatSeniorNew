"""ActivationEligibilityService — Phase 1.2 Part D."""

import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.accounts.models.media import DocumentType
from apps.accounts.models.profiles import CaregiverProfile, OrganizationProfile, ProfileStatus
from apps.accounts.permission_keys import ACCOUNTS_DOCUMENT_REVIEW
from apps.accounts.services.activation_eligibility_service import ActivationEligibilityService
from apps.accounts.services.document_service import DocumentService
from apps.accounts.services.verification_review_service import VerificationReviewService
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.tests.rbac_helpers import grant_permissions

PDF_BYTES = b"%PDF-1.4 fake test content"


class _EligibilityFixtureMixin:
    def _build_fixture(self):
        self.tenant = Tenant.objects.create(slug=f"activ-{uuid.uuid4().hex[:8]}", name="Activation Test Tenant")
        self.caregiver = self._create_caregiver(tenant=self.tenant)
        self.organization = self._create_organization(tenant=self.tenant)
        self.reviewer = self._create_user(tenant=self.tenant, full_name="Reviewer")
        grant_permissions(self.tenant, self.reviewer, [ACCOUNTS_DOCUMENT_REVIEW])

    def _create_caregiver(self, *, tenant, full_name="Test Caregiver") -> CaregiverProfile:
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=full_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return CaregiverProfile.objects.create(
            user=user, person=person, phone=phone, display_name=full_name,
            city="tehran", specialty="elderly-care", bio="Experienced caregiver.",
            years_experience=5, service_radius_km=10,
        )

    def _create_organization(self, *, tenant, name="Test Org") -> OrganizationProfile:
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=f"{name} Admin")
        admin_user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return OrganizationProfile.objects.create(
            name=name, code=f"ORG-{uuid.uuid4().hex[:6].upper()}", admin_user=admin_user, tenant=tenant,
            city="tehran", phone="09120000000", address="Some address",
            description="A senior-care company.", company_type="home_care",
        )

    def _create_user(self, *, tenant, full_name="Test User") -> UserAccount:
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=full_name)
        return UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)

    def _approve_required_caregiver_documents(self):
        for doc_type in (DocumentType.IDENTITY, DocumentType.BACKGROUND_CHECK):
            file = SimpleUploadedFile(f"{doc_type}.pdf", PDF_BYTES, content_type="application/pdf")
            doc = DocumentService.upload_caregiver_document(self.caregiver, document_type=doc_type, file=file)
            VerificationReviewService.approve(document_id=doc.id, tenant_id=self.tenant.id, reviewer=self.reviewer)

    def _approve_required_organization_documents(self):
        for doc_type in (DocumentType.REGISTRATION, DocumentType.OPERATING_LICENSE):
            file = SimpleUploadedFile(f"{doc_type}.pdf", PDF_BYTES, content_type="application/pdf")
            doc = DocumentService.upload_organization_document(self.organization, document_type=doc_type, file=file)
            VerificationReviewService.approve(document_id=doc.id, tenant_id=self.tenant.id, reviewer=self.reviewer)


class CaregiverEligibilityTest(_EligibilityFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_eligible_when_complete_profile_active_account_and_documents_verified(self):
        self._approve_required_caregiver_documents()
        result = ActivationEligibilityService.evaluate_caregiver(self.caregiver)
        self.assertTrue(result.eligible, result.reasons)
        self.assertEqual(result.reasons, ())

    def test_not_eligible_without_required_documents(self):
        result = ActivationEligibilityService.evaluate_caregiver(self.caregiver)
        self.assertFalse(result.eligible)
        self.assertTrue(any(r.startswith("documents_not_verified") for r in result.reasons))

    def test_not_eligible_when_profile_incomplete(self):
        self.caregiver.bio = ""
        self.caregiver.save(update_fields=["bio"])
        self._approve_required_caregiver_documents()
        result = ActivationEligibilityService.evaluate_caregiver(self.caregiver)
        self.assertFalse(result.eligible)
        self.assertTrue(any(r.startswith("profile_incomplete") for r in result.reasons))

    def test_not_eligible_when_profile_suspended(self):
        self._approve_required_caregiver_documents()
        self.caregiver.status = ProfileStatus.SUSPENDED
        self.caregiver.save(update_fields=["status"])
        result = ActivationEligibilityService.evaluate_caregiver(self.caregiver)
        self.assertFalse(result.eligible)
        self.assertIn("profile_status_not_active:suspended", result.reasons)

    def test_not_eligible_when_user_account_inactive(self):
        self._approve_required_caregiver_documents()
        self.caregiver.user.is_active = False
        self.caregiver.user.save(update_fields=["is_active"])
        result = ActivationEligibilityService.evaluate_caregiver(self.caregiver)
        self.assertFalse(result.eligible)
        self.assertIn("user_account_inactive", result.reasons)

    def test_not_eligible_when_documents_need_correction(self):
        file = SimpleUploadedFile("id.pdf", PDF_BYTES, content_type="application/pdf")
        doc = DocumentService.upload_caregiver_document(self.caregiver, document_type=DocumentType.IDENTITY, file=file)
        VerificationReviewService.request_correction(
            document_id=doc.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="fix",
        )
        result = ActivationEligibilityService.evaluate_caregiver(self.caregiver)
        self.assertFalse(result.eligible)
        self.assertIn("documents_need_correction", result.reasons)

    def test_evaluate_dispatches_by_profile_type(self):
        self._approve_required_caregiver_documents()
        via_evaluate = ActivationEligibilityService.evaluate(self.caregiver)
        via_typed = ActivationEligibilityService.evaluate_caregiver(self.caregiver)
        self.assertEqual(via_evaluate.eligible, via_typed.eligible)


class OrganizationEligibilityTest(_EligibilityFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_eligible_when_complete_profile_active_account_and_documents_verified(self):
        self._approve_required_organization_documents()
        result = ActivationEligibilityService.evaluate_organization(self.organization)
        self.assertTrue(result.eligible, result.reasons)

    def test_not_eligible_without_required_documents(self):
        result = ActivationEligibilityService.evaluate_organization(self.organization)
        self.assertFalse(result.eligible)
        self.assertTrue(any(r.startswith("documents_not_verified") for r in result.reasons))

    def test_not_eligible_when_admin_user_inactive(self):
        self._approve_required_organization_documents()
        self.organization.admin_user.is_active = False
        self.organization.admin_user.save(update_fields=["is_active"])
        result = ActivationEligibilityService.evaluate_organization(self.organization)
        self.assertFalse(result.eligible)
        self.assertIn("user_account_inactive", result.reasons)

    def test_evaluate_dispatches_by_profile_type(self):
        self._approve_required_organization_documents()
        via_evaluate = ActivationEligibilityService.evaluate(self.organization)
        via_typed = ActivationEligibilityService.evaluate_organization(self.organization)
        self.assertEqual(via_evaluate.eligible, via_typed.eligible)
