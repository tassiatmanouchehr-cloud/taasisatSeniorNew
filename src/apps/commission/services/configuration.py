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

# Financial Core PR-B — Real Escrow, Objection Period, Disputes & Partial
# Release. Four independent feature gates, each DISABLED by default for
# every existing and legacy tenant (Section 18: "Legacy tenants and legacy
# transactions must not be silently moved into the new Escrow flow").
# Enabling PRESERVICE_PAYMENT without also enabling DEADLINE_ACTIVATION_
# ENABLED_KEY above leaves the payment deadline recorded but not
# expiry-enforced — operationally coherent (the two are usually turned on
# together) but deliberately not code-coupled, so a tenant can be moved to
# pre-service payment without its expiry-reopening semantics changing on
# the same day if that is ever operationally desired.
PRESERVICE_PAYMENT_ENABLED_KEY = "commission.preservice_payment.enabled"
DEFAULT_PRESERVICE_PAYMENT_ENABLED = False

# Gates whether a captured PaymentIntent tagged as a pre-service payment
# (metadata["financial_core_flow"] == "preservice") routes to a real Escrow
# hold instead of apps.payments.services.settlement_orchestration_service's
# existing Direct Settlement path. Distinct from PRESERVICE_PAYMENT_ENABLED
# so an operator can, in principle, stage the two independently — but in
# practice both must be True for the intended end-to-end flow, since a
# preservice-tagged intent settling through Direct Settlement instead of
# Escrow would violate the "no immediate beneficiary credit" invariant.
ESCROW_PRODUCTION_ENABLED_KEY = "commission.escrow_production.enabled"
DEFAULT_ESCROW_PRODUCTION_ENABLED = False

# Gates whether the scheduled commission.objection_period.auto_approve job
# is allowed to actually auto-approve a due, undisputed objection period.
# When disabled, ObjectionPeriodService.auto_approve_if_due() is a safe
# no-op (matches the deadline-activation gate's own re-check-independently
# pattern) — an objection period can still be explicitly approved by the
# customer, or resolved by a platform-authorized dispute resolution,
# regardless of this gate.
OBJECTION_AUTOMATION_ENABLED_KEY = "commission.objection.automation_enabled"
DEFAULT_OBJECTION_AUTOMATION_ENABLED = False

# Gates whether DisputeService/DisputeResolutionService/
# ReleaseInstructionService/RefundInstructionService write paths are
# reachable at all for a tenant — defense in depth against a tenant that
# has not yet adopted the new Escrow flow having its (nonexistent) Escrow
# records disputed or released.
DISPUTE_RELEASE_ENABLED_KEY = "commission.dispute_release.enabled"
DEFAULT_DISPUTE_RELEASE_ENABLED = False

# Objection period duration — independently configurable from the four
# enablement gates above, per Section 6 ("its duration is configurable by
# Manouchehr; the default must be configurable, not hardcoded").
OBJECTION_PERIOD_SECONDS_KEY = "commission.objection.period_seconds"
DEFAULT_OBJECTION_PERIOD_SECONDS = 3 * 24 * 60 * 60  # 3 days.


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
    def get_preservice_payment_enabled(cls, *, tenant_id: uuid.UUID) -> bool:
        value = ConfigResolver.get_or_default(
            PRESERVICE_PAYMENT_ENABLED_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_PRESERVICE_PAYMENT_ENABLED,
        )
        return cls._to_bool(value, DEFAULT_PRESERVICE_PAYMENT_ENABLED)

    @classmethod
    def get_escrow_production_enabled(cls, *, tenant_id: uuid.UUID) -> bool:
        value = ConfigResolver.get_or_default(
            ESCROW_PRODUCTION_ENABLED_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_ESCROW_PRODUCTION_ENABLED,
        )
        return cls._to_bool(value, DEFAULT_ESCROW_PRODUCTION_ENABLED)

    @classmethod
    def get_objection_automation_enabled(cls, *, tenant_id: uuid.UUID) -> bool:
        value = ConfigResolver.get_or_default(
            OBJECTION_AUTOMATION_ENABLED_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_OBJECTION_AUTOMATION_ENABLED,
        )
        return cls._to_bool(value, DEFAULT_OBJECTION_AUTOMATION_ENABLED)

    @classmethod
    def get_dispute_release_enabled(cls, *, tenant_id: uuid.UUID) -> bool:
        value = ConfigResolver.get_or_default(
            DISPUTE_RELEASE_ENABLED_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_DISPUTE_RELEASE_ENABLED,
        )
        return cls._to_bool(value, DEFAULT_DISPUTE_RELEASE_ENABLED)

    @classmethod
    def get_objection_period_seconds(cls, *, tenant_id: uuid.UUID) -> int:
        value = ConfigResolver.get_or_default(
            OBJECTION_PERIOD_SECONDS_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_OBJECTION_PERIOD_SECONDS,
        )
        return cls._to_int(value, DEFAULT_OBJECTION_PERIOD_SECONDS)

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
