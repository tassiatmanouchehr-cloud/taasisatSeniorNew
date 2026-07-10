"""
Reporting-integration test — Architecture Review remediation (Epic 03
Sprint 1).

The original PR claimed apps.provider_portal.earnings_view would
automatically reflect a real settlement's wallet credit, based on code
inspection (both read the same FinancialPartyService.
resolve_party_for_supplier() -> WalletService party) rather than an actual
end-to-end test. This drives a full settlement through
PaymentCallbackService.process_callback() -> SettlementOrchestrationService
using the same apps.provider_portal fixtures/identity-resolution path
(resolve_supplier_for_user) every other provider_portal test uses, then
asserts the rendered earnings page reflects the settled balance.
"""

import uuid

from apps.execution.services.session_service import ExecutionService
from apps.finance.services import FinancialDocumentService, FinancialPartyService
from apps.payments.services import PaymentCallbackService, PaymentIntentService

from .helpers import ProviderPortalTestCase


class SettlementEarningsIntegrationTest(ProviderPortalTestCase):
    def test_earnings_view_reflects_a_real_settlement(self):
        supplier_assignment = self.assign_order_to_supplier()

        session = ExecutionService.create_session(supplier_assignment=supplier_assignment)
        ExecutionService.start_session(session_id=session.id)
        ExecutionService.complete_session(session_id=session.id)
        closed_session = ExecutionService.close_session(session_id=session.id)

        document = FinancialDocumentService.create_invoice_from_execution(
            execution_session_id=closed_session.id,
            items=[
                {"item_type": "SERVICE", "description": "Home care visit", "quantity": 1, "unit_price": "750000"},
            ],
        )

        payer_party = FinancialPartyService.resolve_party_for_customer(self.customer)
        intent = PaymentIntentService.create_intent(
            payer_party=payer_party, amount=document.total_amount,
            idempotency_key=f"intent-{uuid.uuid4().hex[:12]}",
            reference_type="Order", reference_id=self.order.id,
        )
        attempt = PaymentIntentService.start_attempt(intent_id=intent.id)
        payload = {
            "provider_reference": attempt.provider_reference,
            "provider_event_id": f"evt-{uuid.uuid4().hex[:12]}",
            "status": "SUCCEEDED", "amount": str(intent.amount), "currency": intent.currency,
        }
        PaymentCallbackService.process_callback(provider_reference=attempt.provider_reference, payload=payload)

        self.login_as_provider()
        response = self.client.get("/provider/earnings/")

        self.assertEqual(response.status_code, 200)
        wallet = response.context["wallet"]
        self.assertIsNotNone(wallet, "earnings_view must show the real wallet credited by settlement")
        self.assertEqual(wallet.balance, document.total_amount)
