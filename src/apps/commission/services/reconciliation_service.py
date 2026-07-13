"""
EscrowReconciliationService — Financial Core PR-B (Section 25).

Read-only. Verifies, per order/Escrow, the invariants PR-B's own services
are supposed to maintain — and reports discrepancies explicitly rather
than auto-correcting them (a discrepancy is a bug to be investigated, not
data to be silently normalized).
"""

from dataclasses import dataclass, field

from apps.finance.models import EscrowRecord


@dataclass(frozen=True)
class ReconciliationResult:
    escrow_id: str
    order_id: str
    ok: bool
    discrepancies: list[str] = field(default_factory=list)


class EscrowReconciliationService:
    @classmethod
    def check_escrow(cls, *, escrow_id) -> ReconciliationResult:
        escrow = EscrowRecord.objects.select_related("payment_transaction", "order").get(id=escrow_id)
        discrepancies = []

        # captured payment == original Escrow amount
        if escrow.payment_transaction_id and escrow.payment_transaction is not None:
            captured = int(escrow.payment_transaction.amount)
            if captured != escrow.original_amount_irr:
                discrepancies.append(
                    f"captured payment ({captured}) != original_amount_irr ({escrow.original_amount_irr})",
                )

        # original = released + refunded + blocked + remaining (also DB-enforced; re-checked here read-only)
        conserved = (
            escrow.released_amount_irr
            + escrow.refunded_amount_irr
            + escrow.blocked_amount_irr
            + escrow.remaining_amount_irr
        )
        if conserved != escrow.original_amount_irr:
            discrepancies.append(
                f"conservation violated: released+refunded+blocked+remaining ({conserved}) "
                f"!= original_amount_irr ({escrow.original_amount_irr})",
            )

        # active dispute total == blocked amount
        from .dispute_service import DisputeService

        active_disputed = DisputeService.open_disputed_total_for_escrow(escrow=escrow)
        if active_disputed != escrow.blocked_amount_irr:
            discrepancies.append(
                f"open dispute total ({active_disputed}) != blocked_amount_irr ({escrow.blocked_amount_irr})",
            )

        # release instructions <= releasable amount ever granted (approximated: <= released_amount_irr, since
        # every ReleaseInstruction's amount was consumed into released_amount_irr at creation time)
        from ..models.release_instruction import ReleaseInstruction

        release_total = sum(
            ReleaseInstruction.objects.filter(tenant_id=escrow.tenant_id, escrow=escrow).values_list(
                "gross_releasable_amount_irr",
                flat=True,
            ),
        )
        if release_total > escrow.released_amount_irr:
            discrepancies.append(
                f"sum of ReleaseInstruction amounts ({release_total}) > released_amount_irr "
                f"({escrow.released_amount_irr})",
            )

        # refund instructions <= refundable held amount ever granted (same reasoning as release, against refunded)
        from ..models.release_instruction import RefundInstruction

        refund_total = sum(
            RefundInstruction.objects.filter(tenant_id=escrow.tenant_id, escrow=escrow).values_list(
                "amount_irr",
                flat=True,
            ),
        )
        if refund_total > escrow.refunded_amount_irr:
            discrepancies.append(
                f"sum of RefundInstruction amounts ({refund_total}) > refunded_amount_irr "
                f"({escrow.refunded_amount_irr})",
            )

        return ReconciliationResult(
            escrow_id=str(escrow.id),
            order_id=str(escrow.order_id) if escrow.order_id else "",
            ok=not discrepancies,
            discrepancies=discrepancies,
        )

    @classmethod
    def check_tenant(cls, *, tenant_id) -> list[ReconciliationResult]:
        return [
            cls.check_escrow(escrow_id=escrow_id)
            for escrow_id in EscrowRecord.objects.filter(tenant_id=tenant_id).values_list("id", flat=True)
        ]
