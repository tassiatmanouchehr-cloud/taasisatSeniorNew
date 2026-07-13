"""
PreServicePaymentService — Financial Core PR-B.

Connects an accepted assignment to the pre-service payment flow: accepted
assignment -> payment-required invoice -> PaymentIntent. Gated behind
CommissionConfiguration.get_preservice_payment_enabled() (default DISABLED
for every tenant) — called from
apps.booking.services.assignment_service.AssignmentService
._open_financial_core_for_assignment(), the same integration point PR-A
already uses for CommissionSnapshot/PaymentDeadline creation.

The PaymentIntent's idempotency_key is derived from the PaymentDeadline id
for this exact assignment cycle (not the order id alone) — Section 2's
explicit requirement: "new assignment cycle receives a new snapshot,
deadline, invoice/payment context, and PaymentIntent." A reassignment
after a payment-deadline expiry gets a fresh PaymentDeadline (PR-A's own
_cancel_open_deadlines() + create()), and therefore a fresh invoice and a
fresh PaymentIntent here too — the old PaymentIntent/invoice are simply
never referenced by the new cycle again; they are not deleted (financial
history is never rewritten).

The intent is tagged metadata["financial_core_flow"] = "preservice" so
apps.payments.services.settlement_orchestration_service can distinguish it
from a legacy/direct-settlement intent and route it to a real Escrow hold
instead (see that module's own PR-B changes).
"""

import logging

from django.db import transaction

from apps.finance.services import FinancialDocumentService, FinancialPartyService
from apps.payments.services import PaymentIntentService

from .configuration import CommissionConfiguration
from .errors import PreServicePaymentError

logger = logging.getLogger(__name__)

FINANCIAL_CORE_FLOW_PRESERVICE = "preservice"


class PreServicePaymentService:
    @classmethod
    def is_enabled(cls, *, tenant_id) -> bool:
        return CommissionConfiguration.get_preservice_payment_enabled(tenant_id=tenant_id)

    @classmethod
    @transaction.atomic
    def create_invoice_and_intent_for_order(cls, *, order, supplier, deadline, actor=None):
        """Returns (FinancialDocument, PaymentIntent). Idempotent per
        deadline: a repeated call for the same PaymentDeadline (e.g. a
        retried assign() in the same acceptance cycle) returns the same
        PaymentIntent via PaymentIntentService.create_intent()'s own
        idempotency_key contract, rather than creating a duplicate."""
        amount_irr = cls._resolve_amount_irr(order=order, supplier=supplier)

        invoice = FinancialDocumentService.create_preservice_invoice_for_order(
            order=order,
            items=[
                {
                    "item_type": "SERVICE",
                    "description": f"Pre-service payment for order {order.order_number}",
                    "quantity": 1,
                    "unit_price": str(amount_irr),
                }
            ],
            issued_by=getattr(actor, "person_id", None),
        )
        invoice = FinancialDocumentService.issue_document(document_id=invoice.id, changed_by=None)

        payer_party = FinancialPartyService.resolve_party_for_customer(order.customer_profile)

        intent = PaymentIntentService.create_intent(
            payer_party=payer_party,
            amount=amount_irr,
            idempotency_key=f"preservice:{deadline.id}",
            reference_type="Order",
            reference_id=order.id,
            metadata={
                "financial_core_flow": FINANCIAL_CORE_FLOW_PRESERVICE,
                "payment_deadline_id": str(deadline.id),
                "invoice_id": str(invoice.id),
                "supplier_id": str(supplier.id),
            },
        )

        return invoice, intent

    @classmethod
    @transaction.atomic
    def get_or_start_attempt_for_order(cls, *, order):
        """The pending PaymentAttempt for this order's current pre-service
        PaymentIntent — starts one if the intent is still CREATED. Used by
        the minimal customer-portal UI's Fake payment actions (Section 24);
        never touches an intent belonging to a superseded assignment cycle,
        since only a CREATED/PENDING intent for this exact order is ever
        matched here."""
        from apps.payments.models import PaymentAttempt, PaymentIntent, PaymentStatus

        intent = (
            PaymentIntent.objects.select_for_update()
            .filter(
                tenant_id=order.tenant_id,
                reference_type="Order",
                reference_id=order.id,
                status__in=(PaymentStatus.CREATED, PaymentStatus.PENDING),
            )
            .order_by("-created_at")
            .first()
        )
        if intent is None:
            raise PreServicePaymentError(f"No actionable PaymentIntent exists for order {order.id}.")

        if intent.status == PaymentStatus.CREATED:
            return PaymentIntentService.start_attempt(intent_id=intent.id)

        attempt = PaymentAttempt.objects.filter(intent=intent).order_by("-created_at").first()
        if attempt is None:
            raise PreServicePaymentError(f"PaymentIntent {intent.id} is PENDING but has no PaymentAttempt.")
        return attempt

    @classmethod
    def simulate_fake_payment_outcome(cls, *, order, outcome: str):
        """outcome: "SUCCEEDED" or "FAILED" — the two Fake provider callback
        buttons the minimal customer-portal UI offers (Section 24)."""
        import uuid

        from apps.payments.services import PaymentCallbackService

        attempt = cls.get_or_start_attempt_for_order(order=order)
        return PaymentCallbackService.process_callback(
            provider_reference=attempt.provider_reference,
            payload={
                "provider_reference": attempt.provider_reference,
                "provider_event_id": str(uuid.uuid4()),
                "status": outcome,
                "amount": str(attempt.intent.amount),
                "currency": attempt.intent.currency,
            },
        )

    # --- internal helpers -------------------------------------------------

    @classmethod
    def _resolve_amount_irr(cls, *, order, supplier) -> int:
        """Prefers an existing Quote already linked to this order (created
        earlier in the request/pricing flow); falls back to generating one
        via QuoteService against the order's service_category/supplier. No
        price is ever fabricated — QuoteService.generate_quote() itself
        raises PricingError if no base pricing rule is configured for the
        tenant/category, and that is allowed to propagate as a clear
        PreServicePaymentError rather than defaulting to some made-up
        amount."""
        from apps.pricing.models import Quote

        existing = Quote.objects.filter(tenant_id=order.tenant_id, order=order).order_by("-created_at").first()
        if existing is not None:
            return cls._to_irr(existing.total_amount)

        from apps.pricing.services.errors import PricingError
        from apps.pricing.services.quote_service import QuoteService

        try:
            quote = QuoteService.generate_quote(
                tenant_id=order.tenant_id,
                service_category=order.service_category,
                supplier=supplier,
                order=order,
                customer_profile=order.customer_profile,
            )
        except PricingError as exc:
            raise PreServicePaymentError(
                f"Cannot determine a pre-service payment amount for order {order.id}: {exc}",
            ) from exc

        return cls._to_irr(quote.total_amount)

    @staticmethod
    def _to_irr(decimal_amount) -> int:
        # IRR has no meaningful fractional subunit in this domain (matches
        # apps.commission.services.allocation_calculator.AllocationCalculator's
        # own "deterministic integer-IRR" convention) — truncates any stray
        # cents rather than rounding up past what the customer was quoted.
        return int(decimal_amount)
