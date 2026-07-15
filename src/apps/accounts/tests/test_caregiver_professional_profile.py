"""CaregiverSkillService / CaregiverExperienceService / PublicCredentialSelector
— Phase 2.1 (Caregiver Professional Profile Foundation)."""

import datetime
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.accounts.models.media import DocumentType
from apps.accounts.models.profiles import CaregiverProfile
from apps.accounts.services.caregiver_professional_profile_service import (
    CaregiverExperienceService,
    CaregiverSkillService,
)
from apps.accounts.services.document_service import DocumentService
from apps.accounts.services.errors import AccountsError
from apps.accounts.services.public_credential_selector import PublicCredentialSelector
from apps.accounts.services.verification_review_service import VerificationReviewService
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.tests.rbac_helpers import grant_permissions

PDF_BYTES = b"%PDF-1.4 fake test content"


class _FixtureMixin:
    def _build_fixture(self):
        self.tenant = Tenant.objects.create(slug=f"prof-{uuid.uuid4().hex[:8]}", name="Professional Profile Tenant")
        self.caregiver = self._create_caregiver(tenant=self.tenant)
        self.other_caregiver = self._create_caregiver(tenant=self.tenant, full_name="Other Caregiver")

    def _create_caregiver(self, *, tenant, full_name="Test Caregiver") -> CaregiverProfile:
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=full_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return CaregiverProfile.objects.create(user=user, person=person, phone=phone, display_name=full_name)

    def _create_reviewer(self):
        from apps.accounts.permission_keys import ACCOUNTS_DOCUMENT_REVIEW

        person = Person.objects.create(tenant=self.tenant, full_name="Reviewer")
        reviewer = UserAccount.objects.create_user(phone="09121230099", person=person, tenant=self.tenant)
        grant_permissions(self.tenant, reviewer, [ACCOUNTS_DOCUMENT_REVIEW])
        return reviewer


class CaregiverSkillServiceTest(_FixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_add_skill(self):
        skill = CaregiverSkillService.add_skill(self.caregiver, name="مراقبت از سالمندان")
        self.assertEqual(skill.caregiver_id, self.caregiver.id)
        self.assertEqual(list(CaregiverSkillService.list_skills(self.caregiver)), [skill])

    def test_blank_skill_name_refused(self):
        with self.assertRaises(AccountsError):
            CaregiverSkillService.add_skill(self.caregiver, name="   ")

    def test_overlong_skill_name_refused(self):
        with self.assertRaises(AccountsError):
            CaregiverSkillService.add_skill(self.caregiver, name="x" * 101)

    def test_duplicate_skill_refused_case_insensitive(self):
        CaregiverSkillService.add_skill(self.caregiver, name="Nursing")
        with self.assertRaises(AccountsError):
            CaregiverSkillService.add_skill(self.caregiver, name="nursing")

    def test_same_skill_name_allowed_for_different_caregivers(self):
        CaregiverSkillService.add_skill(self.caregiver, name="Nursing")
        skill = CaregiverSkillService.add_skill(self.other_caregiver, name="Nursing")
        self.assertEqual(skill.caregiver_id, self.other_caregiver.id)

    def test_remove_skill(self):
        skill = CaregiverSkillService.add_skill(self.caregiver, name="Nursing")
        CaregiverSkillService.remove_skill(self.caregiver, skill_id=skill.id)
        self.assertEqual(list(CaregiverSkillService.list_skills(self.caregiver)), [])

    def test_cannot_remove_another_caregivers_skill(self):
        skill = CaregiverSkillService.add_skill(self.other_caregiver, name="Nursing")
        with self.assertRaises(AccountsError):
            CaregiverSkillService.remove_skill(self.caregiver, skill_id=skill.id)
        self.assertEqual(list(CaregiverSkillService.list_skills(self.other_caregiver)), [skill])

    def test_remove_nonexistent_skill_refused(self):
        with self.assertRaises(AccountsError):
            CaregiverSkillService.remove_skill(self.caregiver, skill_id=uuid.uuid4())


class CaregiverExperienceServiceTest(_FixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_create_experience(self):
        entry = CaregiverExperienceService.create(
            self.caregiver, title="Home Care Nurse", organization_name="Care Co",
            start_date=datetime.date(2020, 1, 1), end_date=datetime.date(2022, 1, 1),
        )
        self.assertEqual(entry.caregiver_id, self.caregiver.id)
        self.assertFalse(entry.is_current)

    def test_current_experience_does_not_require_end_date(self):
        entry = CaregiverExperienceService.create(
            self.caregiver, title="Home Care Nurse", start_date=datetime.date(2020, 1, 1), is_current=True,
        )
        self.assertIsNone(entry.end_date)

    def test_end_date_before_start_date_refused(self):
        with self.assertRaises(AccountsError):
            CaregiverExperienceService.create(
                self.caregiver, title="X", start_date=datetime.date(2022, 1, 1), end_date=datetime.date(2020, 1, 1),
            )

    def test_blank_title_refused(self):
        with self.assertRaises(AccountsError):
            CaregiverExperienceService.create(self.caregiver, title="  ", start_date=datetime.date(2020, 1, 1))

    def test_missing_start_date_refused(self):
        with self.assertRaises(AccountsError):
            CaregiverExperienceService.create(self.caregiver, title="X", start_date=None)

    def test_update_experience(self):
        entry = CaregiverExperienceService.create(
            self.caregiver, title="Old Title", start_date=datetime.date(2020, 1, 1),
        )
        updated = CaregiverExperienceService.update(
            self.caregiver, experience_id=entry.id, title="New Title", start_date=datetime.date(2020, 1, 1),
        )
        self.assertEqual(updated.title, "New Title")

    def test_cannot_update_another_caregivers_experience(self):
        entry = CaregiverExperienceService.create(
            self.other_caregiver, title="X", start_date=datetime.date(2020, 1, 1),
        )
        with self.assertRaises(AccountsError):
            CaregiverExperienceService.update(
                self.caregiver, experience_id=entry.id, title="Hacked", start_date=datetime.date(2020, 1, 1),
            )

    def test_delete_experience(self):
        entry = CaregiverExperienceService.create(self.caregiver, title="X", start_date=datetime.date(2020, 1, 1))
        CaregiverExperienceService.delete(self.caregiver, experience_id=entry.id)
        self.assertEqual(list(CaregiverExperienceService.list_experiences(self.caregiver)), [])

    def test_cannot_delete_another_caregivers_experience(self):
        entry = CaregiverExperienceService.create(
            self.other_caregiver, title="X", start_date=datetime.date(2020, 1, 1),
        )
        with self.assertRaises(AccountsError):
            CaregiverExperienceService.delete(self.caregiver, experience_id=entry.id)
        self.assertEqual(len(list(CaregiverExperienceService.list_experiences(self.other_caregiver))), 1)


class PublicCredentialSelectorTest(_FixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()
        self.reviewer = self._create_reviewer()

    def _upload(self, document_type):
        file = SimpleUploadedFile(f"{document_type}.pdf", PDF_BYTES, content_type="application/pdf")
        return DocumentService.upload_caregiver_document(self.caregiver, document_type=document_type, file=file)

    def test_approved_document_appears(self):
        doc = self._upload(DocumentType.IDENTITY)
        VerificationReviewService.approve(document_id=doc.id, tenant_id=self.tenant.id, reviewer=self.reviewer)
        summaries = PublicCredentialSelector.for_caregiver(self.caregiver)
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0].document_type, DocumentType.IDENTITY)

    def test_pending_document_does_not_appear(self):
        self._upload(DocumentType.IDENTITY)
        self.assertEqual(PublicCredentialSelector.for_caregiver(self.caregiver), ())

    def test_rejected_document_does_not_appear(self):
        doc = self._upload(DocumentType.IDENTITY)
        VerificationReviewService.reject(
            document_id=doc.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="bad scan",
        )
        self.assertEqual(PublicCredentialSelector.for_caregiver(self.caregiver), ())

    def test_correction_required_document_does_not_appear(self):
        doc = self._upload(DocumentType.IDENTITY)
        VerificationReviewService.request_correction(
            document_id=doc.id, tenant_id=self.tenant.id, reviewer=self.reviewer, reason="fix",
        )
        self.assertEqual(PublicCredentialSelector.for_caregiver(self.caregiver), ())

    def test_expired_document_does_not_appear(self):
        doc = self._upload(DocumentType.IDENTITY)
        VerificationReviewService.approve(document_id=doc.id, tenant_id=self.tenant.id, reviewer=self.reviewer)
        doc.refresh_from_db()
        doc.expiry_date = datetime.date.today() - datetime.timedelta(days=1)
        doc.save(update_fields=["expiry_date"])
        self.assertEqual(PublicCredentialSelector.for_caregiver(self.caregiver), ())

    def test_selector_never_exposes_file_field(self):
        doc = self._upload(DocumentType.IDENTITY)
        VerificationReviewService.approve(document_id=doc.id, tenant_id=self.tenant.id, reviewer=self.reviewer)
        summary = PublicCredentialSelector.for_caregiver(self.caregiver)[0]
        self.assertFalse(hasattr(summary, "file"))
        self.assertFalse(hasattr(summary, "rejection_reason"))
        self.assertFalse(hasattr(summary, "reviewed_by"))

    def test_another_caregivers_documents_never_appear(self):
        doc = self._upload(DocumentType.IDENTITY)
        VerificationReviewService.approve(document_id=doc.id, tenant_id=self.tenant.id, reviewer=self.reviewer)
        self.assertEqual(PublicCredentialSelector.for_caregiver(self.other_caregiver), ())
