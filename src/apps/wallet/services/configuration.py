"""
Wallet Configuration wrapper — Module 14 foundation.

Wallet service code must never call ConfigResolver directly. All
wallet-specific config keys and defaults are centralized here, mirroring
apps.availability.services.configuration.AvailabilityConfiguration.
"""

import uuid
from decimal import Decimal

from apps.kernel.services.config_resolver import ConfigResolver

OVERDRAFT_ENABLED_KEY = "wallet.overdraft.enabled"
DEFAULT_CURRENCY_KEY = "wallet.default_currency"
MAX_MANUAL_ADJUSTMENT_KEY = "wallet.max_manual_adjustment"

DEFAULT_OVERDRAFT_ENABLED = False
DEFAULT_CURRENCY = "IRR"
DEFAULT_MAX_MANUAL_ADJUSTMENT = None  # None = unlimited


class WalletConfiguration:
    """Central resolver for all Wallet module configuration values."""

    @classmethod
    def get_overdraft_enabled(cls, *, tenant_id: uuid.UUID) -> bool:
        value = ConfigResolver.get_or_default(
            OVERDRAFT_ENABLED_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_OVERDRAFT_ENABLED,
        )
        return cls._to_bool(value, DEFAULT_OVERDRAFT_ENABLED)

    @classmethod
    def get_default_currency(cls, *, tenant_id: uuid.UUID) -> str:
        value = ConfigResolver.get_or_default(
            DEFAULT_CURRENCY_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_CURRENCY,
        )
        if isinstance(value, str) and value:
            return value
        return DEFAULT_CURRENCY

    @classmethod
    def get_max_manual_adjustment(cls, *, tenant_id: uuid.UUID) -> Decimal | None:
        value = ConfigResolver.get_or_default(
            MAX_MANUAL_ADJUSTMENT_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_MAX_MANUAL_ADJUSTMENT,
        )
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return DEFAULT_MAX_MANUAL_ADJUSTMENT

    @staticmethod
    def _to_bool(value, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return default
