"""
EscrowIntegrationService — Financial Core PR-B.

The bridge apps.payments.services.settlement_orchestration_service calls
(via a local import, mirroring the established apps.booking ->
apps.commission integration pattern from PR-A) once a pre-service
PaymentIntent has genuinely reached SUCCEEDED. Two responsibilities, both
required before any Escrow hold may exist:

1. Complete the EXACT PaymentDeadline this PaymentIntent was created for
   (identified by intent.metadata["payment_deadline_id"], never merely
   "whichever deadline is currently PENDING for this order" — a
   reassignment after expiry creates a fresh PaymentDeadline for the same
   order, and a late callback for the OLD intent must never complete the
   NEW cycle's deadline).
2. Hold the captured amount in Escrow, linked to the frozen
   CommissionSnapshot for this exact assignment cycle.

A callback arriving after its own deadline already left PENDING (expired,
cancelled by a newer cycle, or already completed by an earlier, identical
callback) is handled explicitly, never silently: an idempotent replay
returns the existing Escrow; a genuinely stale cycle raises loudly (caught
and retried by the same best-effort/retry-job wrapper
apps.payments.services.payment_callback_service.PaymentCallbackService
._trigger_settlement() already uses for any settlement failure) rather
than reopening or reviving anything.
"""

import logging

from django.db import transaction

from apps.commission.models.deadline import PaymentDeadline, PaymentDeadlineStatus
from apps.commission.models.snapshot import CommissionSnapshot
from apps.finance.models import EscrowRecord, FinancialDocument
from apps.finance.services import EscrowService
from apps.kernel.events.base import PAYMENT_HELD_IN_ESCROW, DomainEvent
from apps.kernel.events.publisher import publish as publish_domain_event
from apps.kernel.models.audit import AuditClassification
from apps.kernel.services.audit_service import AuditService

from .errors import PreServicePaymentError

logger = logging.getLogger(__name__)

SOURCE_MODULE = "M05"


class EscrowIntegrationService:
    @classmethod
    @transaction.atomic
    def handle_preservice_payment_succeeded(cls, *, intent, payment_transaction) -> EscrowRecord:
        deadline_id = intent.metadata.get("payment_deadline_id")
        invoice_id = intent.metadata.get("invoice_id")
        if not deadline_id or not invoice_id:
            raise PreServicePaymentError(
                f"PaymentIntent {intent.id} is tagged financial_core_flow=preservice but is missing "
                "payment_deadline_id/invoice_id metadata; cannot hold Escrow.",
            )

        hold_idempotency_key = f"preservice-hold:{intent.id}"
        existing_escrow = EscrowRecord.objects.filter(
            tenant_id=intent.tenant_id,
            idempotency_key=hold_idempotency_key,
        ).first()
        if existing_escrow is not None:
            return existing_escrow

        deadline = PaymentDeadline.objects.select_for_update().get(id=deadline_id, tenant_id=intent.tenant_id)

        if deadline.status == PaymentDeadlineStatus.PENDING:
            from .deadline_service import PaymentDeadlineService

            PaymentDeadlineService.mark_completed(order_id=deadline.order_id)
        elif deadline.status != PaymentDeadlineStatus.COMPLETED:
            AuditService.log(
                tenant_id=intent.tenant_id,
                action="commission.escrow.hold_rejected_stale_cycle",
                resource_type="PaymentDeadline",
                module_id=SOURCE_MODULE,
                resource_id=deadline.id,
                audit_class=AuditClassification.FINANCIAL,
                reason=(
                    f"PaymentIntent {intent.id} succeeded but its PaymentDeadline is '{deadline.status}' "
                    "(not PENDING/COMPLETED) — a newer assignment cycle has since superseded it. No Escrow "
                    "was created; this payment requires manual review (a refund, most likely)."
                ),
                after={"intent_id": str(intent.id), "deadline_status": deadline.status},
            )
            raise PreServicePaymentError(
                f"PaymentDeadline {deadline.id} is '{deadline.status}', not PENDING/COMPLETED — "
                f"PaymentIntent {intent.id} belongs to a superseded assignment cycle and cannot be held "
                "in Escrow. Requires manual review.",
            )

        order = deadline.order
        invoice = FinancialDocument.objects.get(id=invoice_id, tenant_id=intent.tenant_id)
        commission_snapshot = (
            CommissionSnapshot.objects.filter(tenant_id=intent.tenant_id, order=order).order_by("-created_at").first()
        )

        escrow = EscrowService.hold_for_order(
            order=order,
            source_document=invoice,
            payment_transaction=payment_transaction,
            commission_snapshot=commission_snapshot,
            payer_party=intent.payer_party,
            amount_irr=int(intent.amount),
            idempotency_key=hold_idempotency_key,
        )

        if order.customer_profile_id:
            domain_event = DomainEvent(
                event_type=PAYMENT_HELD_IN_ESCROW,
                tenant_id=order.tenant_id,
                aggregate_type="Order",
                aggregate_id=order.id,
                payload={
                    "recipient_id": str(order.customer_profile.person_id),
                    "amount_irr": escrow.original_amount_irr,
                },
            )
            transaction.on_commit(lambda: publish_domain_event(domain_event))

        return escrow
