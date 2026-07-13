"""
DisputeService — Financial Core PR-B.

Opens a customer-raised dispute against an exact amount of a HELD/
PARTIALLY_RELEASED Escrow, optionally broken into DisputeLine allocations.
Only the customer who owns the order may open a dispute against it — the
same ownership-is-the-security-boundary model
apps.commission.services.objection_service uses for customer approval.
"""

import uuid

from django.db import transaction
from django.db.models import Sum

from apps.finance.models import EscrowRecord
from apps.kernel.events.base import DISPUTE_OPENED, DomainEvent
from apps.kernel.events.publisher import publish as publish_domain_event
from apps.kernel.models.audit import AuditClassification
from apps.kernel.services.audit_service import AuditService

from ..models.dispute import OPEN_DISPUTE_STATUSES, Dispute, DisputeLine, DisputeStatus
from ..models.objection import ObjectionPeriod, ObjectionPeriodStatus
from .authorization import assert_actor_is_order_customer
from .configuration import CommissionConfiguration
from .errors import DisputeError

SOURCE_MODULE = "M05"


class DisputeService:
    @classmethod
    @transaction.atomic
    def open(
        cls,
        *,
        order,
        customer_party,
        disputed_amount_irr: int,
        reason_code: str,
        description: str = "",
        lines=None,
        supplier_party=None,
        actor=None,
        idempotency_key: str | None = None,
        correlation_id=None,
    ) -> Dispute:
        if not CommissionConfiguration.get_dispute_release_enabled(tenant_id=order.tenant_id):
            raise DisputeError(f"Dispute/release is not enabled for tenant {order.tenant_id}.")
        assert_actor_is_order_customer(actor, order, error_cls=DisputeError)

        idempotency_key = idempotency_key or f"dispute-open:{order.id}:{uuid.uuid4()}"
        existing = Dispute.objects.filter(tenant_id=order.tenant_id, idempotency_key=idempotency_key).first()
        if existing is not None:
            return existing

        if disputed_amount_irr <= 0:
            raise DisputeError("disputed_amount_irr must be positive.")

        escrow = (
            EscrowRecord.objects.select_for_update()
            .filter(tenant_id=order.tenant_id, order=order)
            .order_by("-created_at")
            .first()
        )
        if escrow is None:
            raise DisputeError(f"Order {order.id} has no Escrow to dispute against.")
        if disputed_amount_irr > escrow.remaining_amount_irr:
            raise DisputeError(
                f"Cannot dispute {disputed_amount_irr}: only {escrow.remaining_amount_irr} of escrow "
                f"{escrow.id} is currently disputable (undisputed and un-released).",
            )

        if lines:
            lines_total = sum(line["disputed_amount_irr"] for line in lines)
            if lines_total != disputed_amount_irr:
                raise DisputeError(
                    f"Dispute lines must sum to disputed_amount_irr ({disputed_amount_irr}); got {lines_total}.",
                )
            for line in lines:
                if line["disputed_amount_irr"] <= 0:
                    raise DisputeError("Each dispute line amount must be positive.")
                if line["invoice_item"].document_id != escrow.source_document_id:
                    raise DisputeError("A dispute line's invoice_item must belong to this Escrow's own invoice.")
                if line["invoice_item"].tenant_id != order.tenant_id:
                    raise DisputeError("A dispute line's invoice_item must belong to the same tenant.")

        dispute = Dispute.objects.create(
            tenant_id=order.tenant_id,
            order=order,
            invoice=escrow.source_document,
            escrow=escrow,
            customer_party=customer_party,
            supplier_party=supplier_party,
            disputed_amount_irr=disputed_amount_irr,
            reason_code=reason_code,
            description=description,
            status=DisputeStatus.OPEN,
            opened_by=actor,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )

        if lines:
            DisputeLine.objects.bulk_create(
                [
                    DisputeLine(
                        tenant_id=order.tenant_id,
                        dispute=dispute,
                        invoice_item=line["invoice_item"],
                        disputed_amount_irr=line["disputed_amount_irr"],
                        reason=line.get("reason", ""),
                        evidence_reference=line.get("evidence_reference", ""),
                    )
                    for line in lines
                ]
            )

        from apps.finance.services import EscrowService

        EscrowService.block_for_dispute(
            escrow_id=escrow.id,
            amount_irr=disputed_amount_irr,
            dispute_id=dispute.id,
            actor=actor,
            reason=f"Dispute opened: {reason_code}",
            idempotency_key=f"dispute-block:{dispute.id}",
        )

        objection = ObjectionPeriod.objects.select_for_update().filter(tenant_id=order.tenant_id, escrow=escrow).first()
        if objection is not None and objection.status == ObjectionPeriodStatus.OPEN:
            objection.status = ObjectionPeriodStatus.DISPUTED
            objection.save(update_fields=["status", "updated_at"])

        AuditService.log(
            tenant_id=order.tenant_id,
            action="commission.dispute.open",
            resource_type="Dispute",
            module_id=SOURCE_MODULE,
            actor_id=getattr(actor, "person_id", None),
            resource_id=dispute.id,
            reason=description,
            audit_class=AuditClassification.FINANCIAL,
            after={
                "order_id": str(order.id),
                "disputed_amount_irr": disputed_amount_irr,
                "reason_code": reason_code,
                "status": dispute.status,
            },
        )

        if order.customer_profile_id:
            domain_event = DomainEvent(
                event_type=DISPUTE_OPENED,
                tenant_id=order.tenant_id,
                aggregate_type="Order",
                aggregate_id=order.id,
                actor_id=getattr(actor, "person_id", None),
                payload={
                    "recipient_id": str(order.customer_profile.person_id),
                    "disputed_amount_irr": disputed_amount_irr,
                },
            )
            transaction.on_commit(lambda: publish_domain_event(domain_event))

        return dispute

    @classmethod
    def open_disputed_total_for_escrow(cls, *, escrow) -> int:
        return (
            Dispute.objects.filter(
                tenant_id=escrow.tenant_id, escrow=escrow, status__in=OPEN_DISPUTE_STATUSES
            ).aggregate(total=Sum("disputed_amount_irr"))["total"]
            or 0
        )
