from decimal import Decimal

from apps.finance.services import FinancialPartyService
from apps.payments.models import PaymentAttempt, PaymentIntent
from apps.payments.services import PaymentIntentService

from .helpers import PaymentsTestCase


class PaymentTenantIsolationTest(PaymentsTestCase):
    def setUp(self):
        super().setUp()

        self.other_customer = self._create_customer(tenant=self.other_tenant, display_name="Other Customer")
        self.other_party = FinancialPartyService.resolve_party_for_customer(self.other_customer)
        self.other_intent = PaymentIntentService.create_intent(
            payer_party=self.other_party, amount=Decimal("2000"), idempotency_key="other-tenant-intent",
        )

        self.attempt = PaymentIntentService.start_attempt(intent_id=self.intent.id)
        self.other_attempt = PaymentIntentService.start_attempt(intent_id=self.other_intent.id)

    def test_for_tenant_scopes_intents(self):
        tenant_intents = PaymentIntent.objects.for_tenant(self.tenant.id)
        other_tenant_intents = PaymentIntent.objects.for_tenant(self.other_tenant.id)

        self.assertIn(self.intent, tenant_intents)
        self.assertNotIn(self.other_intent, tenant_intents)
        self.assertIn(self.other_intent, other_tenant_intents)
        self.assertNotIn(self.intent, other_tenant_intents)

    def test_for_tenant_scopes_attempts(self):
        tenant_attempts = PaymentAttempt.objects.for_tenant(self.tenant.id)
        other_tenant_attempts = PaymentAttempt.objects.for_tenant(self.other_tenant.id)

        self.assertTrue(all(a.tenant_id == self.tenant.id for a in tenant_attempts))
        self.assertTrue(all(a.tenant_id == self.other_tenant.id for a in other_tenant_attempts))

    def test_idempotency_key_is_scoped_per_tenant(self):
        # Same idempotency_key string, different tenants -> two distinct intents.
        first = PaymentIntentService.create_intent(
            payer_party=self.party, amount=Decimal("100"), idempotency_key="shared-key",
        )
        second = PaymentIntentService.create_intent(
            payer_party=self.other_party, amount=Decimal("100"), idempotency_key="shared-key",
        )

        self.assertNotEqual(first.id, second.id)
        self.assertEqual(PaymentIntent.objects.filter(idempotency_key="shared-key").count(), 2)
