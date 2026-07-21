"""Shared fixtures for payments tests (not a test module itself)."""

import uuid
from decimal import Decimal

from django.test import TestCase

from apps.accounts.models.profiles import CustomerProfile
from apps.finance.services import FinancialPartyService
from apps.kernel.models import Person, Tenant, UserAccount
from apps.payments.services import PaymentIntentService


class PaymentsTestCase(TestCase):
    """Base test case: a tenant, a customer FinancialParty, and a PaymentIntent."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"payments-{uuid.uuid4().hex[:8]}", name="Payments Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"payments-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        self.customer_profile = self._create_customer(tenant=self.tenant)
        self.party = FinancialPartyService.resolve_party_for_customer(self.customer_profile)

        self.intent = PaymentIntentService.create_intent(
            payer_party=self.party,
            amount=Decimal("100000"),
            idempotency_key=f"intent-{uuid.uuid4().hex[:12]}",
        )

    def _create_customer(self, *, tenant, display_name="Test Customer", phone=None) -> CustomerProfile:
        phone = phone or f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=display_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return CustomerProfile.objects.create(
            user=user,
            person=person,
            phone=phone,
            display_name=display_name,
        )

    @staticmethod
    def _success_payload(attempt, *, provider_event_id=None, amount=None, currency=None, status="SUCCEEDED"):
        return {
            "provider_reference": attempt.provider_reference,
            "provider_event_id": provider_event_id or f"evt-{uuid.uuid4().hex[:12]}",
            "status": status,
            "amount": str(amount if amount is not None else attempt.intent.amount),
            "currency": currency or attempt.intent.currency,
        }
