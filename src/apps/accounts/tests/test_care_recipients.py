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


class CareRecipientNotAUserAccountTest(CareRecipientTestCase):
    """Care recipients are data owned by the customer, never authenticated accounts."""

    def test_elder_profile_has_no_user_account_field(self):
        field_names = {f.name for f in ElderProfile._meta.get_fields()}
        self.assertNotIn("user", field_names)

    def test_order_references_care_recipient_directly(self):
        from apps.orders.models import Order

        field = Order._meta.get_field("elder_profile")
        self.assertEqual(field.related_model, ElderProfile)
