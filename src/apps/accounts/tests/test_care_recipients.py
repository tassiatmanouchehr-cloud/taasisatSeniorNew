"""
Tests for Care Recipient management — Customer Experience Phase 1.

"Care Recipient" is the product name for ElderProfile (see ADR-008 and
the model's own docstring) — these tests cover the new fields and the
new CareRecipientService, not a new model.
"""

import uuid

from django.test import TestCase

from apps.accounts.models.profiles import CaregiverGenderPreference, CareRecipientRelationship, ElderProfile
from apps.accounts.services.care_recipients import CareRecipientService
from apps.accounts.services.errors import AccountsError
from apps.kernel.models import Person, Tenant, UserAccount


class CareRecipientTestCase(TestCase):
    def setUp(self):
        from apps.accounts.models.profiles import CustomerProfile

        self.tenant = Tenant.objects.create(slug=f"t-{uuid.uuid4().hex[:8]}", name="T")
        person = Person.objects.create(tenant=self.tenant, full_name="Maryam Ahmadi")
        user = UserAccount.objects.create_user(email="maryam@example.com", person=person, tenant=self.tenant)
        self.customer = CustomerProfile.objects.create(
            user=user, person=person, phone="09121111111", display_name="Maryam Ahmadi",
        )

        other_person = Person.objects.create(tenant=self.tenant, full_name="Sara Karimi")
        other_user = UserAccount.objects.create_user(email="sara@example.com", person=other_person, tenant=self.tenant)
        self.other_customer = CustomerProfile.objects.create(
            user=other_user, person=other_person, phone="09122222222", display_name="Sara Karimi",
        )


class CreateCareRecipientTest(CareRecipientTestCase):
    def test_create_stores_all_documented_fields(self):
        recipient = CareRecipientService.create(
            customer_profile=self.customer,
            full_name="Hassan Ahmadi",
            gender="male",
            relationship=CareRecipientRelationship.FATHER,
            phone="09123334444",
            address="Tehran, Valiasr St.",
            emergency_contact_name="Ali Ahmadi",
            emergency_contact_phone="09125556666",
            medical_notes="Diabetes",
            disabilities="Partial hearing loss",
            allergies="Penicillin",
            preferred_caregiver_gender=CaregiverGenderPreference.FEMALE,
            preferred_language="فارسی",
            communication_notes="Speaks slowly, hard of hearing",
        )
        self.assertEqual(recipient.full_name, "Hassan Ahmadi")
        self.assertEqual(recipient.relationship, CareRecipientRelationship.FATHER)
        self.assertEqual(recipient.emergency_contact_name, "Ali Ahmadi")
        self.assertEqual(recipient.preferred_caregiver_gender, CaregiverGenderPreference.FEMALE)
        self.assertEqual(recipient.customer_profile, self.customer)

    def test_create_requires_full_name(self):
        with self.assertRaises(AccountsError):
            CareRecipientService.create(customer_profile=self.customer, full_name="")

    def test_create_rejects_unknown_field(self):
        with self.assertRaises(AccountsError):
            CareRecipientService.create(customer_profile=self.customer, full_name="X", not_a_real_field="y")

    def test_first_care_recipient_is_primary(self):
        recipient = CareRecipientService.create(customer_profile=self.customer, full_name="First One")
        self.assertTrue(recipient.is_primary)

    def test_second_care_recipient_is_not_primary(self):
        CareRecipientService.create(customer_profile=self.customer, full_name="First One")
        second = CareRecipientService.create(customer_profile=self.customer, full_name="Second One")
        self.assertFalse(second.is_primary)


class MultipleCareRecipientsTest(CareRecipientTestCase):
    def test_customer_may_manage_multiple_care_recipients(self):
        CareRecipientService.create(customer_profile=self.customer, full_name="Father", relationship="father")
        CareRecipientService.create(customer_profile=self.customer, full_name="Mother", relationship="mother")
        CareRecipientService.create(customer_profile=self.customer, full_name="Grandmother", relationship="grandparent")

        recipients = CareRecipientService.list_for_customer(self.customer)
        self.assertEqual(recipients.count(), 3)

    def test_list_only_returns_this_customers_recipients(self):
        CareRecipientService.create(customer_profile=self.customer, full_name="Mine")
        CareRecipientService.create(customer_profile=self.other_customer, full_name="Not Mine")

        recipients = CareRecipientService.list_for_customer(self.customer)
        self.assertEqual(recipients.count(), 1)
        self.assertEqual(recipients.first().full_name, "Mine")


class CareRecipientOwnershipTest(CareRecipientTestCase):
    def test_get_for_customer_returns_own_recipient(self):
        recipient = CareRecipientService.create(customer_profile=self.customer, full_name="Mine")
        fetched = CareRecipientService.get_for_customer(self.customer, recipient.id)
        self.assertEqual(fetched.id, recipient.id)

    def test_get_for_customer_denies_another_customers_recipient(self):
        recipient = CareRecipientService.create(customer_profile=self.other_customer, full_name="Not Mine")
        with self.assertRaises(AccountsError):
            CareRecipientService.get_for_customer(self.customer, recipient.id)

    def test_get_for_customer_raises_for_nonexistent_id(self):
        with self.assertRaises(AccountsError):
            CareRecipientService.get_for_customer(self.customer, uuid.uuid4())


class UpdateCareRecipientTest(CareRecipientTestCase):
    def test_update_changes_fields(self):
        recipient = CareRecipientService.create(customer_profile=self.customer, full_name="Original")
        updated = CareRecipientService.update(recipient, medical_notes="Updated notes", allergies="Peanuts")
        updated.refresh_from_db()
        self.assertEqual(updated.medical_notes, "Updated notes")
        self.assertEqual(updated.allergies, "Peanuts")

    def test_update_rejects_unknown_field(self):
        recipient = CareRecipientService.create(customer_profile=self.customer, full_name="Original")
        with self.assertRaises(AccountsError):
            CareRecipientService.update(recipient, not_a_real_field="y")


class ArchiveCareRecipientTest(CareRecipientTestCase):
    def test_archive_sets_status_archived(self):
        from apps.accounts.models.profiles import ProfileStatus

        recipient = CareRecipientService.create(customer_profile=self.customer, full_name="Old One")
        CareRecipientService.archive(recipient)
        recipient.refresh_from_db()
        self.assertEqual(recipient.status, ProfileStatus.ARCHIVED)

    def test_archived_recipient_excluded_from_default_list(self):
        recipient = CareRecipientService.create(customer_profile=self.customer, full_name="Old One")
        CareRecipientService.create(customer_profile=self.customer, full_name="Active One")
        CareRecipientService.archive(recipient)

        recipients = CareRecipientService.list_for_customer(self.customer)
        self.assertEqual(recipients.count(), 1)
        self.assertEqual(recipients.first().full_name, "Active One")

    def test_archived_recipient_included_when_requested(self):
        recipient = CareRecipientService.create(customer_profile=self.customer, full_name="Old One")
        CareRecipientService.archive(recipient)

        recipients = CareRecipientService.list_for_customer(self.customer, include_archived=True)
        self.assertEqual(recipients.count(), 1)

    def test_archived_recipient_still_reachable_by_id(self):
        recipient = CareRecipientService.create(customer_profile=self.customer, full_name="Old One")
        CareRecipientService.archive(recipient)
        fetched = CareRecipientService.get_for_customer(self.customer, recipient.id)
        self.assertEqual(fetched.id, recipient.id)

    def test_cannot_archive_another_customers_recipient_via_get_for_customer(self):
        """archive() itself takes a resolved model instance, not an id — the
        ownership boundary is get_for_customer(), which callers (the portal
        view) must call first. This proves that boundary rejects a
        cross-customer id before archive() would ever be reached."""
        recipient = CareRecipientService.create(customer_profile=self.other_customer, full_name="Not Mine")
        with self.assertRaises(AccountsError):
            CareRecipientService.get_for_customer(self.customer, recipient.id)

    def test_cannot_archive_another_tenants_recipient_via_get_for_customer(self):
        other_tenant = Tenant.objects.create(slug=f"t-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")
        other_tenant_person = Person.objects.create(tenant=other_tenant, full_name="Reza Rahimi")
        other_tenant_user = UserAccount.objects.create_user(
            email="reza@example.com", person=other_tenant_person, tenant=other_tenant,
        )
        from apps.accounts.models.profiles import CustomerProfile

        other_tenant_customer = CustomerProfile.objects.create(
            user=other_tenant_user, person=other_tenant_person, phone="09123338888", display_name="Reza Rahimi",
        )
        recipient = CareRecipientService.create(customer_profile=other_tenant_customer, full_name="Not Mine Either")

        with self.assertRaises(AccountsError):
            CareRecipientService.get_for_customer(self.customer, recipient.id)

        # The recipient itself is untouched — still active, still belongs to the other tenant's customer.
        from apps.accounts.models.profiles import ProfileStatus

        recipient.refresh_from_db()
        self.assertEqual(recipient.status, ProfileStatus.ACTIVE)
        self.assertEqual(recipient.customer_profile_id, other_tenant_customer.id)


class CareRecipientEventPublishingTest(CareRecipientTestCase):
    def test_create_publishes_and_audits(self):
        from apps.kernel.models.audit import AuditLog

        with self.captureOnCommitCallbacks(execute=True):
            recipient = CareRecipientService.create(customer_profile=self.customer, full_name="Audited One")

        entry = AuditLog.objects.get(action="domain_event.CareRecipientCreated", resource_id=recipient.id)
        self.assertEqual(entry.resource_type, "ElderProfile")
        self.assertEqual(entry.actor_id, self.customer.person_id)

    def test_update_publishes_and_audits(self):
        from apps.kernel.models.audit import AuditLog

        recipient = CareRecipientService.create(customer_profile=self.customer, full_name="Audited One")
        with self.captureOnCommitCallbacks(execute=True):
            CareRecipientService.update(recipient, medical_notes="Updated")

        self.assertTrue(
            AuditLog.objects.filter(action="domain_event.CareRecipientUpdated", resource_id=recipient.id).exists()
        )

    def test_archive_publishes_and_audits(self):
        from apps.kernel.models.audit import AuditLog

        recipient = CareRecipientService.create(customer_profile=self.customer, full_name="Audited One")
        with self.captureOnCommitCallbacks(execute=True):
            CareRecipientService.archive(recipient)

        entry = AuditLog.objects.get(action="domain_event.CareRecipientArchived", resource_id=recipient.id)
        self.assertEqual(entry.resource_type, "ElderProfile")
        self.assertEqual(entry.actor_id, self.customer.person_id)

    def test_archive_does_not_publish_before_commit(self):
        """The event is queued via transaction.on_commit — outside a
        captureOnCommitCallbacks(execute=True) block, TestCase's own
        wrapping transaction never commits, so no AuditLog should appear."""
        from apps.kernel.models.audit import AuditLog

        recipient = CareRecipientService.create(customer_profile=self.customer, full_name="Audited One")
        CareRecipientService.archive(recipient)

        self.assertFalse(
            AuditLog.objects.filter(action="domain_event.CareRecipientArchived", resource_id=recipient.id).exists()
        )


class CareRecipientNotAUserAccountTest(CareRecipientTestCase):
    """Care recipients are data owned by the customer, never authenticated accounts."""

    def test_elder_profile_has_no_user_account_field(self):
        field_names = {f.name for f in ElderProfile._meta.get_fields()}
        self.assertNotIn("user", field_names)

    def test_order_references_care_recipient_directly(self):
        from apps.orders.models import Order

        field = Order._meta.get_field("elder_profile")
        self.assertEqual(field.related_model, ElderProfile)
