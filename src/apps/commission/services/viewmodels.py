"""Read-only ViewModels for the Financial Core PR-B minimal UI (Section 24).

Frozen dataclasses only — no ORM model instance, permission check, or
financial calculation may cross from apps.commission.services.queries into
a template; templates consume only these. Mirrors the established
apps.portal.services.viewmodels pattern."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DisputeLineRow:
    id: str
    description: str
    disputed_amount_irr: int
    reason: str


@dataclass(frozen=True)
class DisputeRow:
    id: str
    order_id: str
    order_number: str
    disputed_amount_irr: int
    reason_code: str
    reason_code_label: str
    status: str
    status_label: str
    opened_at_label: str
    lines: tuple[DisputeLineRow, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReleaseInstructionRow:
    id: str
    order_id: str
    order_number: str
    source_label: str
    gross_releasable_amount_irr: int
    status: str
    status_label: str
    created_at_label: str


@dataclass(frozen=True)
class RefundInstructionRow:
    id: str
    order_id: str
    order_number: str
    source_label: str
    amount_irr: int
    status: str
    status_label: str
    created_at_label: str


@dataclass(frozen=True)
class EscrowRow:
    id: str
    order_id: str
    order_number: str
    status: str
    status_label: str
    original_amount_irr: int
    held_amount_irr: int
    releasable_amount_irr: int
    blocked_amount_irr: int
    released_amount_irr: int
    refunded_amount_irr: int
    remaining_amount_irr: int
    created_at_label: str


@dataclass(frozen=True)
class EscrowDetail(EscrowRow):
    movements: tuple[dict, ...] = field(default_factory=tuple)
    disputes: tuple[DisputeRow, ...] = field(default_factory=tuple)
    release_instructions: tuple[ReleaseInstructionRow, ...] = field(default_factory=tuple)
    refund_instructions: tuple[RefundInstructionRow, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class OrderFinancialView:
    """The one thing every portal's order-scoped financial page needs —
    "is money held, how much, is it disputed, can I approve, can I
    dispute" — assembled once here so no portal repeats the read logic."""

    order_id: str
    preservice_payment_enabled: bool
    escrow_exists: bool
    escrow_id: str = ""
    escrow_status: str = ""
    escrow_status_label: str = ""
    original_amount_irr: int = 0
    held_amount_irr: int = 0
    releasable_amount_irr: int = 0
    blocked_amount_irr: int = 0
    released_amount_irr: int = 0
    refunded_amount_irr: int = 0
    remaining_amount_irr: int = 0
    pending_payment_intent_id: str = ""
    objection_exists: bool = False
    objection_id: str = ""
    objection_status: str = ""
    objection_status_label: str = ""
    objection_deadline_label: str = ""
    can_customer_approve: bool = False
    can_customer_dispute: bool = False
    disputes: tuple[DisputeRow, ...] = field(default_factory=tuple)
    release_instructions: tuple[ReleaseInstructionRow, ...] = field(default_factory=tuple)
    refund_instructions: tuple[RefundInstructionRow, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FeatureGateStatus:
    preservice_payment_enabled: bool
    escrow_production_enabled: bool
    objection_automation_enabled: bool
    dispute_release_enabled: bool
    objection_period_seconds: int
