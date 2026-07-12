"""
AllocationCalculator — Financial Core PR-A.

Deterministic integer-IRR allocation with a fixed rounding rule (Business
Model Section 13): platform's and company's shares are floored to the
nearest whole Rial; the caregiver receives the exact residual. This
guarantees, by construction and independent of the input amount:

    platform_amount + company_amount + caregiver_amount == base_amount_irr

exactly, for every input — no Rial can ever disappear or be created,
because caregiver_amount is computed as a subtraction, never its own
independent rounding.

PR-A ships this as a standalone, independently-testable primitive. It is
not yet wired into real settlement (that remains
apps.payments.services.settlement_adjustments.SettlementAdjustmentPipeline,
untouched by PR-A) — see the PR-A final report's "known limitations for
PR-B onward" section.
"""

from dataclasses import dataclass


class AllocationError(Exception):
    pass


@dataclass(frozen=True)
class AllocationResult:
    base_amount_irr: int
    platform_rate_percent: int
    company_rate_percent: int
    caregiver_rate_percent: int
    platform_amount_irr: int
    company_amount_irr: int
    caregiver_amount_irr: int

    def __post_init__(self):
        total = self.platform_amount_irr + self.company_amount_irr + self.caregiver_amount_irr
        if total != self.base_amount_irr:
            raise AllocationError(
                f"Allocation conservation violated: {self.platform_amount_irr} + "
                f"{self.company_amount_irr} + {self.caregiver_amount_irr} = {total} != "
                f"{self.base_amount_irr}.",
            )


class AllocationCalculator:
    """Splits an integer-IRR base amount by whole-percent shares that sum to 100."""

    @classmethod
    def allocate(
        cls,
        *,
        base_amount_irr: int,
        platform_rate_percent: int,
        company_rate_percent: int,
        caregiver_rate_percent: int,
    ) -> AllocationResult:
        if not isinstance(base_amount_irr, int) or isinstance(base_amount_irr, bool):
            raise AllocationError(f"base_amount_irr must be an int, got {type(base_amount_irr).__name__}.")
        if base_amount_irr < 0:
            raise AllocationError(f"base_amount_irr must be non-negative, got {base_amount_irr}.")

        total_rate = platform_rate_percent + company_rate_percent + caregiver_rate_percent
        if total_rate != 100:
            raise AllocationError(f"Commission rates must sum to exactly 100, got {total_rate}.")

        platform_amount = (base_amount_irr * platform_rate_percent) // 100
        company_amount = (base_amount_irr * company_rate_percent) // 100
        caregiver_amount = base_amount_irr - platform_amount - company_amount

        return AllocationResult(
            base_amount_irr=base_amount_irr,
            platform_rate_percent=platform_rate_percent,
            company_rate_percent=company_rate_percent,
            caregiver_rate_percent=caregiver_rate_percent,
            platform_amount_irr=platform_amount,
            company_amount_irr=company_amount,
            caregiver_amount_irr=caregiver_amount,
        )
