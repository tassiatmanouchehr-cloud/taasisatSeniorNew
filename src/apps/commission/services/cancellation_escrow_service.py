"""
CancellationEscrowService — Financial Core PR-B (Section 17).

The minimum safe cancellation-before-release integration: called from
apps.booking.services.assignment_service.AssignmentService.cancel(). Only
the temporary explicit policy Section 17 asks for is implemented —
FULL_REFUND of whatever remains un-blocked/un-released in Escrow — never a
time-window/penalty/compensation rule (that full engine is reserved for
PR-E). A no-op when pre-service payment is disabled for the tenant, when
no Escrow exists (unpaid cancellation), or when nothing remains to refund.
"""

import logging

from django.db import transaction

from apps.finance.models import OPEN_ESCROW_STATUSES, EscrowRecord

from .configuration import CommissionConfiguration
from .errors import CommissionError

logger = logging.getLogger(__name__)

SOURCE_MODULE = "M05"


class CancellationEscrowService:
    @classmethod
    @transaction.atomic
    def handle_cancellation(cls, *, order, actor=None):
        """Returns the created RefundInstruction, or None (unpaid
        cancellation / nothing remaining / dispute-release not enabled —
        logged as REQUIRES_MANUAL_REVIEW in the last case, never silent)."""
        if not CommissionConfiguration.get_preservice_payment_enabled(tenant_id=order.tenant_id):
            return None

        escrow = (
            EscrowRecord.objects.select_for_update()
            .filter(tenant_id=order.tenant_id, order=order, status__in=OPEN_ESCROW_STATUSES)
            .order_by("-created_at")
            .first()
        )
        if escrow is None:
            return None  # Unpaid cancellation — no Escrow movement, per Section 17.

        if escrow.remaining_amount_irr <= 0:
            return None  # Nothing un-blocked/un-released remains to refund.

        if not CommissionConfiguration.get_dispute_release_enabled(tenant_id=order.tenant_id):
            from apps.kernel.models.audit import AuditClassification
            from apps.kernel.services.audit_service import AuditService

            AuditService.log(
                tenant_id=order.tenant_id,
                action="commission.cancellation.requires_manual_review",
                resource_type="EscrowRecord",
                module_id=SOURCE_MODULE,
                actor_id=getattr(actor, "person_id", None),
                resource_id=escrow.id,
                audit_class=AuditClassification.FINANCIAL,
                reason=(
                    "Order cancelled with a held Escrow balance remaining, but dispute/release is not "
                    "enabled for this tenant — a RefundInstruction could not be created automatically. "
                    "Requires manual review (temporary explicit policy per Section 17: REQUIRES_MANUAL_REVIEW)."
                ),
                after={"order_id": str(order.id), "remaining_amount_irr": escrow.remaining_amount_irr},
            )
            return None

        from .refund_instruction_service import RefundInstructionService

        try:
            from ..models.release_instruction import RefundInstructionSource

            return RefundInstructionService.create(
                escrow=escrow,
                order=order,
                invoice=escrow.source_document,
                amount_irr=escrow.remaining_amount_irr,
                source=RefundInstructionSource.CANCELLATION,
                reason=(
                    "Order cancelled before Escrow release — full refund of the remaining held amount "
                    "(temporary explicit policy; the full cancellation rule engine is reserved for PR-E)."
                ),
                actor=actor,
                idempotency_key=f"cancellation-refund:{order.id}:{escrow.id}",
            )
        except CommissionError:
            logger.exception("Cancellation-triggered refund instruction failed for order %s.", order.id)
            raise
