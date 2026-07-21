"""
Finance Configuration wrapper — Module 05 foundation.

Finance service code must never call ConfigResolver directly. All
finance-specific config keys and defaults are centralized here, mirroring
apps.booking.services.configuration.BookingConfiguration.
"""

import uuid

from apps.kernel.services.config_resolver import ConfigResolver

from ..models import DEFAULT_CURRENCY

WALLET_ENABLED_KEY = "financial.wallet.enabled"
ESCROW_ENABLED_KEY = "financial.escrow.enabled"
DEFAULT_CURRENCY_KEY = "financial.document.default_currency"

DEFAULT_WALLET_ENABLED = True
DEFAULT_ESCROW_ENABLED = True


class FinanceConfiguration:
    """Central resolver for all Finance module configuration values."""

    @classmethod
    def get_wallet_enabled(cls, *, tenant_id: uuid.UUID) -> bool:
        value = ConfigResolver.get_or_default(
            WALLET_ENABLED_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_WALLET_ENABLED,
        )
        return cls._to_bool(value, DEFAULT_WALLET_ENABLED)

    @classmethod
    def get_escrow_enabled(cls, *, tenant_id: uuid.UUID) -> bool:
        value = ConfigResolver.get_or_default(
            ESCROW_ENABLED_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_ESCROW_ENABLED,
        )
        return cls._to_bool(value, DEFAULT_ESCROW_ENABLED)

    @classmethod
    def get_default_currency(cls, *, tenant_id: uuid.UUID) -> str:
        value = ConfigResolver.get_or_default(
            DEFAULT_CURRENCY_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_CURRENCY,
        )
        return value or DEFAULT_CURRENCY

    @staticmethod
    def _to_bool(value, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return default
