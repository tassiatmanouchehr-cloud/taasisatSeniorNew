"""
CommissionConfiguration — Financial Core PR-A.

Commission/deadline service code must never call ConfigResolver directly,
mirroring apps.booking.services.configuration.BookingConfiguration and
every other *Configuration wrapper in this codebase.
"""

import uuid

from apps.kernel.services.config_resolver import ConfigResolver

PAYMENT_DEADLINE_SECONDS_KEY = "commission.payment_deadline.seconds"
DEFAULT_PAYMENT_DEADLINE_SECONDS = 30 * 60  # Business Model Section 2: 30-minute default.

EXTRA_INVOICE_EDIT_WINDOW_SECONDS_KEY = "commission.extra_invoice.edit_window_seconds"
DEFAULT_EXTRA_INVOICE_EDIT_WINDOW_SECONDS = 10 * 60  # Business Model Section 15: 10-minute default.

# System Architect Review of PR #44, Remediation 6 (authoritative payment-
# timing decision): the correct final business rule is pay-before-service
# with Escrow — an accepted proposal is frozen, the customer must pay within
# the deadline, payment succeeds BEFORE service execution, and the money
# then sits in Escrow until completion/dispute handling/release. The
# CURRENT order lifecycle in this repository is execution-first
# (assign -> execute -> invoice -> pay) and does NOT match that rule yet;
# redesigning the order/payment/execution lifecycle is explicitly out of
# scope for this remediation (it is PR-B+ work). Until a real pre-service
# PaymentIntent -> successful callback -> Escrow hold exists (see
# apps.commission.services.deadline_service module docstring for the exact
# prerequisite), a PaymentDeadline's expiry job must not be allowed to
# reopen a real order — expire_due() calling AssignmentService.expire()
# today would incorrectly cancel an assignment whose (post-paid) execution
# may already be legitimately underway or complete. This key gates that
# specific behavior. Default is DISABLED for every existing and legacy
# tenant; it must be explicitly, platform-authorized-only enabled per
# tenant once the pre-service payment prerequisite lands.
DEADLINE_ACTIVATION_ENABLED_KEY = "commission.payment_deadline.activation_enabled"
DEFAULT_DEADLINE_ACTIVATION_ENABLED = False


class CommissionConfiguration:
    """Central resolver for all apps.commission configuration values."""

    @classmethod
    def get_deadline_activation_enabled(cls, *, tenant_id: uuid.UUID) -> bool:
        value = ConfigResolver.get_or_default(
            DEADLINE_ACTIVATION_ENABLED_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_DEADLINE_ACTIVATION_ENABLED,
        )
        return cls._to_bool(value, DEFAULT_DEADLINE_ACTIVATION_ENABLED)

    @classmethod
    def get_payment_deadline_seconds(cls, *, tenant_id: uuid.UUID) -> int:
        value = ConfigResolver.get_or_default(
            PAYMENT_DEADLINE_SECONDS_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_PAYMENT_DEADLINE_SECONDS,
        )
        return cls._to_int(value, DEFAULT_PAYMENT_DEADLINE_SECONDS)

    @classmethod
    def get_extra_invoice_edit_window_seconds(cls, *, tenant_id: uuid.UUID) -> int:
        value = ConfigResolver.get_or_default(
            EXTRA_INVOICE_EDIT_WINDOW_SECONDS_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_EXTRA_INVOICE_EDIT_WINDOW_SECONDS,
        )
        return cls._to_int(value, DEFAULT_EXTRA_INVOICE_EDIT_WINDOW_SECONDS)

    @staticmethod
    def _to_int(value, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_bool(value, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return default
