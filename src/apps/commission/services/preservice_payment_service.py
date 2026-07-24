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
        """Resolves the authoritative payment amount for this order/supplier.

        Phase 6.2A — Marketplace price authority:
        For marketplace-originated orders (any OrderOffer exists for the order),
        the accepted offer's price_amount IS the customer-agreed contract price.
        The pricing-engine Quote path is only used for non-marketplace orders.

        Marketplace origin detection:
        If any OrderOffer row exists for this order (regardless of status), the
        order went through the marketplace offer workflow. This is reliable because
        OrderOfferService.submit_offer() is the sole creator of OrderOffer rows.

        Fail-closed behavior:
        - Marketplace order without exactly one ACCEPTED offer → error
        - Supplier mismatch → error
        - Invalid price → error
        - Never silently falls back to Quote for a marketplace order
        """
        from apps.orders.models import OrderOffer, OrderOfferStatus

        # --- Marketplace origin detection ---
        # If any offer was ever submitted for this order, it is marketplace-originated.
        has_any_offers = OrderOffer.objects.filter(order=order).exists()

        if has_any_offers:
            # Marketplace path: lock and resolve the authoritative accepted offer.
            # select_for_update() ensures the offer cannot be concurrently modified
            # (defense-in-depth — ACCEPTED is terminal, but locking guarantees
            # read consistency within this transaction).
            accepted_offers = list(
                OrderOffer.objects.select_for_update().filter(
                    order=order,
                    tenant_id=order.tenant_id,
                    status=OrderOfferStatus.ACCEPTED,
                )
            )

            if len(accepted_offers) == 0:
                raise PreServicePaymentError(
                    f"Marketplace order {order.id} has offers but no ACCEPTED offer. "
                    "Cannot determine authoritative price for pre-service payment."
                )

            if len(accepted_offers) > 1:
                raise PreServicePaymentError(
                    f"Marketplace order {order.id} has {len(accepted_offers)} accepted offers; "
                    "expected exactly one. Cannot determine authoritative price."
                )

            offer = accepted_offers[0]

            # Validate supplier matches the assigned supplier
            if offer.supplier_id != supplier.id:
                raise PreServicePaymentError(
                    f"Accepted offer supplier ({offer.supplier_id}) does not match "
                    f"assigned supplier ({supplier.id}) for order {order.id}."
                )

            # Validate price
            if offer.price_amount is None or offer.price_amount <= 0:
                raise PreServicePaymentError(
                    f"Accepted offer for order {order.id} has invalid price: {offer.price_amount}."
                )

            return cls._to_irr(offer.price_amount)

        # --- Non-marketplace path (existing behavior) ---
        # No offers ever submitted: this is a non-marketplace order
        # (operator-assigned, manual, etc.). Use the pricing engine.
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

    @classmethod
    def _to_irr(cls, decimal_amount) -> int:
        """Convert a Decimal amount to integer IRR.

        IRR has no meaningful fractional subunit in this domain (matches
        AllocationCalculator's own integer-IRR convention). A fractional
        value indicates a pricing/offer data inconsistency and must be
        rejected rather than silently truncated or rounded.
        """
        from decimal import Decimal

        if not isinstance(decimal_amount, Decimal):
            decimal_amount = Decimal(str(decimal_amount))

        # Reject fractional IRR — the integer conversion must be exact
        if decimal_amount != decimal_amount.to_integral_value():
            raise PreServicePaymentError(
                f"Amount {decimal_amount} has a fractional component. "
                "IRR amounts must be whole numbers — cannot safely truncate or round."
            )

        return int(decimal_amount)
