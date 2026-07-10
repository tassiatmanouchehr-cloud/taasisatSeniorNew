"""
Settlement Adjustment Pipeline — Sprint 1 (Epic 03, Financial Settlement).

The extension point approved by the Financial Settlement Architecture
Specification: a single seam through which future commission, tax,
discount-recovery, and promotional-credit rules will compute a net
settlement amount from a gross amount. Sprint 1 intentionally implements
no real adjustment logic — every rule returns zero — but the shape below
(a list of named, signed adjustment lines) is the one all future rules
will plug into, so nothing about this seam needs to change when a real
rule is added.

Do not add real commission/tax/discount logic here yet — that is
explicitly out of scope for Sprint 1 (see PROJECT root Sprint 1 spec).
"""

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class SettlementAdjustment:
    """One named, signed adjustment line (negative reduces the beneficiary's net)."""

    code: str
    amount: Decimal
    description: str = ""


@dataclass(frozen=True)
class SettlementAdjustmentResult:
    """Gross-to-net breakdown for a single settlement."""

    gross_amount: Decimal
    net_amount: Decimal
    commission_amount: Decimal
    tax_amount: Decimal
    discount_recovery_amount: Decimal
    adjustments: list[SettlementAdjustment] = field(default_factory=list)


class SettlementAdjustmentPipeline:
    """Computes the net settlement amount for a gross payment.

    Sprint 1: identity pipeline. Every component is zero and net == gross.
    Future sprints add real commission/tax/discount/promotional-credit
    rules here without changing any caller of `run()`.
    """

    @classmethod
    def run(cls, *, gross_amount: Decimal) -> SettlementAdjustmentResult:
        zero = Decimal("0.00")
        return SettlementAdjustmentResult(
            gross_amount=gross_amount,
            net_amount=gross_amount,
            commission_amount=zero,
            tax_amount=zero,
            discount_recovery_amount=zero,
            adjustments=[],
        )
