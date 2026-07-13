"""FinancialCoreQueryService — Financial Core PR-B (Section 24 support).

Read-only. The single place that turns Escrow/ObjectionPeriod/Dispute/
ReleaseInstruction/RefundInstruction rows into the frozen ViewModels every
portal's minimal PR-B UI consumes — no portal touches these models
directly (apps.commission owns them), mirroring how apps.orders.services
.queries/apps.booking.services.queries already serve apps.portal/
apps.provider_portal. Never mutates anything."""

from apps.finance.models import EscrowRecord
from apps.payments.models import PaymentIntent, PaymentStatus

from .configuration import CommissionConfiguration
from .viewmodels import (
    DisputeLineRow,
    DisputeRow,
    EscrowDetail,
    EscrowRow,
    FeatureGateStatus,
    OrderFinancialView,
    RefundInstructionRow,
    ReleaseInstructionRow,
)


class FinancialCoreQueryService:
    @classmethod
    def get_order_financial_view(cls, *, tenant_id, order) -> OrderFinancialView:
        preservice_enabled = CommissionConfiguration.get_preservice_payment_enabled(tenant_id=tenant_id)
        if not preservice_enabled:
            return OrderFinancialView(
                order_id=str(order.id),
                preservice_payment_enabled=False,
                escrow_exists=False,
            )

        escrow = EscrowRecord.objects.filter(tenant_id=tenant_id, order=order).order_by("-created_at").first()
        if escrow is None:
            pending_intent = (
                PaymentIntent.objects.filter(
                    tenant_id=tenant_id,
                    reference_type="Order",
                    reference_id=order.id,
                    status__in=(PaymentStatus.CREATED, PaymentStatus.PENDING),
                )
                .order_by("-created_at")
                .first()
            )
            return OrderFinancialView(
                order_id=str(order.id),
                preservice_payment_enabled=True,
                escrow_exists=False,
                pending_payment_intent_id=str(pending_intent.id) if pending_intent else "",
            )

        disputes = tuple(cls._dispute_row(d) for d in escrow.disputes.all().prefetch_related("lines"))
        releases = tuple(cls._release_row(r) for r in escrow.release_instructions.all())
        refunds = tuple(cls._refund_row(r) for r in escrow.refund_instructions.all())

        from ..models.objection import OPEN_OBJECTION_STATUSES, ObjectionPeriod, ObjectionPeriodStatus

        objection = ObjectionPeriod.objects.filter(tenant_id=tenant_id, escrow=escrow).order_by("-created_at").first()

        return OrderFinancialView(
            order_id=str(order.id),
            preservice_payment_enabled=True,
            escrow_exists=True,
            escrow_id=str(escrow.id),
            escrow_status=escrow.status,
            escrow_status_label=escrow.get_status_display(),
            original_amount_irr=escrow.original_amount_irr,
            held_amount_irr=escrow.held_amount_irr,
            releasable_amount_irr=escrow.releasable_amount_irr,
            blocked_amount_irr=escrow.blocked_amount_irr,
            released_amount_irr=escrow.released_amount_irr,
            refunded_amount_irr=escrow.refunded_amount_irr,
            remaining_amount_irr=escrow.remaining_amount_irr,
            objection_exists=objection is not None,
            objection_id=str(objection.id) if objection else "",
            objection_status=objection.status if objection else "",
            objection_status_label=objection.get_status_display() if objection else "",
            objection_deadline_label=(objection.objection_deadline.strftime("%Y-%m-%d %H:%M") if objection else ""),
            can_customer_approve=bool(objection and objection.status in OPEN_OBJECTION_STATUSES),
            can_customer_dispute=bool(
                objection and objection.status == ObjectionPeriodStatus.OPEN and escrow.remaining_amount_irr > 0,
            ),
            disputes=disputes,
            release_instructions=releases,
            refund_instructions=refunds,
        )

    @classmethod
    def list_escrows_for_tenant(cls, *, tenant_id) -> tuple[EscrowRow, ...]:
        return tuple(
            cls._escrow_row(e)
            for e in EscrowRecord.objects.filter(
                tenant_id=tenant_id,
                order__isnull=False,
            )
            .select_related("order")
            .order_by("-created_at")[:200]
        )

    @classmethod
    def get_escrow_detail(cls, *, tenant_id, escrow_id) -> EscrowDetail | None:
        escrow = EscrowRecord.objects.filter(tenant_id=tenant_id, id=escrow_id).select_related("order").first()
        if escrow is None:
            return None
        row = cls._escrow_row(escrow)
        movements = tuple(
            {
                "movement_type": m.get_movement_type_display(),
                "amount_irr": m.amount_irr,
                "reason": m.reason,
                "created_at_label": m.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for m in escrow.movements.all()[:100]
        )
        disputes = tuple(cls._dispute_row(d) for d in escrow.disputes.all().prefetch_related("lines"))
        releases = tuple(cls._release_row(r) for r in escrow.release_instructions.all())
        refunds = tuple(cls._refund_row(r) for r in escrow.refund_instructions.all())
        return EscrowDetail(
            **row.__dict__,
            movements=movements,
            disputes=disputes,
            release_instructions=releases,
            refund_instructions=refunds,
        )

    @classmethod
    def list_disputes_for_tenant(cls, *, tenant_id, status=None) -> tuple[DisputeRow, ...]:
        from ..models.dispute import Dispute

        queryset = Dispute.objects.filter(tenant_id=tenant_id).select_related("order").prefetch_related("lines")
        if status:
            queryset = queryset.filter(status=status)
        return tuple(cls._dispute_row(d) for d in queryset.order_by("-opened_at")[:200])

    @classmethod
    def get_dispute_detail(cls, *, tenant_id, dispute_id):
        from ..models.dispute import Dispute

        return (
            Dispute.objects.filter(tenant_id=tenant_id, id=dispute_id)
            .select_related(
                "order",
                "escrow",
            )
            .first()
        )

    @classmethod
    def list_release_instructions_for_tenant(cls, *, tenant_id) -> tuple[ReleaseInstructionRow, ...]:
        from ..models.release_instruction import ReleaseInstruction

        return tuple(
            cls._release_row(r)
            for r in ReleaseInstruction.objects.filter(
                tenant_id=tenant_id,
            )
            .select_related("order")
            .order_by("-created_at")[:200]
        )

    @classmethod
    def list_refund_instructions_for_tenant(cls, *, tenant_id) -> tuple[RefundInstructionRow, ...]:
        from ..models.release_instruction import RefundInstruction

        return tuple(
            cls._refund_row(r)
            for r in RefundInstruction.objects.filter(
                tenant_id=tenant_id,
            )
            .select_related("order")
            .order_by("-created_at")[:200]
        )

    @classmethod
    def get_feature_gate_status(cls, *, tenant_id) -> FeatureGateStatus:
        return FeatureGateStatus(
            preservice_payment_enabled=CommissionConfiguration.get_preservice_payment_enabled(tenant_id=tenant_id),
            escrow_production_enabled=CommissionConfiguration.get_escrow_production_enabled(tenant_id=tenant_id),
            objection_automation_enabled=CommissionConfiguration.get_objection_automation_enabled(
                tenant_id=tenant_id,
            ),
            dispute_release_enabled=CommissionConfiguration.get_dispute_release_enabled(tenant_id=tenant_id),
            objection_period_seconds=CommissionConfiguration.get_objection_period_seconds(tenant_id=tenant_id),
        )

    # --- internal helpers -------------------------------------------------

    @staticmethod
    def _escrow_row(escrow) -> EscrowRow:
        order = escrow.order
        return EscrowRow(
            id=str(escrow.id),
            order_id=str(order.id) if order else "",
            order_number=order.order_number if order else "",
            status=escrow.status,
            status_label=escrow.get_status_display(),
            original_amount_irr=escrow.original_amount_irr,
            held_amount_irr=escrow.held_amount_irr,
            releasable_amount_irr=escrow.releasable_amount_irr,
            blocked_amount_irr=escrow.blocked_amount_irr,
            released_amount_irr=escrow.released_amount_irr,
            refunded_amount_irr=escrow.refunded_amount_irr,
            remaining_amount_irr=escrow.remaining_amount_irr,
            created_at_label=escrow.created_at.strftime("%Y-%m-%d %H:%M"),
        )

    @staticmethod
    def _dispute_row(dispute) -> DisputeRow:
        lines = tuple(
            DisputeLineRow(
                id=str(line.id),
                description=line.invoice_item.description,
                disputed_amount_irr=line.disputed_amount_irr,
                reason=line.reason,
            )
            for line in dispute.lines.all()
        )
        order = dispute.order
        return DisputeRow(
            id=str(dispute.id),
            order_id=str(order.id) if order else "",
            order_number=order.order_number if order else "",
            disputed_amount_irr=dispute.disputed_amount_irr,
            reason_code=dispute.reason_code,
            reason_code_label=dispute.get_reason_code_display(),
            status=dispute.status,
            status_label=dispute.get_status_display(),
            opened_at_label=dispute.opened_at.strftime("%Y-%m-%d %H:%M"),
            lines=lines,
        )

    @staticmethod
    def _release_row(instruction) -> ReleaseInstructionRow:
        order = instruction.order
        return ReleaseInstructionRow(
            id=str(instruction.id),
            order_id=str(order.id) if order else "",
            order_number=order.order_number if order else "",
            source_label=instruction.get_source_display(),
            gross_releasable_amount_irr=instruction.gross_releasable_amount_irr,
            status=instruction.status,
            status_label=instruction.get_status_display(),
            created_at_label=instruction.created_at.strftime("%Y-%m-%d %H:%M"),
        )

    @staticmethod
    def _refund_row(instruction) -> RefundInstructionRow:
        order = instruction.order
        return RefundInstructionRow(
            id=str(instruction.id),
            order_id=str(order.id) if order else "",
            order_number=order.order_number if order else "",
            source_label=instruction.get_source_display(),
            amount_irr=instruction.amount_irr,
            status=instruction.status,
            status_label=instruction.get_status_display(),
            created_at_label=instruction.created_at.strftime("%Y-%m-%d %H:%M"),
        )
