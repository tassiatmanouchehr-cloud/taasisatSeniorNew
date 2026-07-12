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


class CommissionConfiguration:
    """Central resolver for all apps.commission configuration values."""

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
