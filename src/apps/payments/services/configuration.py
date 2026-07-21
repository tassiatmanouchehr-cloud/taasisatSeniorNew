"""
Payments Configuration wrapper — Module 15 foundation.

Payment service code must never call ConfigResolver directly. All
payments-specific config keys and defaults are centralized here, mirroring
apps.wallet.services.configuration.WalletConfiguration.
"""

import uuid

from apps.kernel.services.config_resolver import ConfigResolver

from ..models import PaymentProvider

DEFAULT_PROVIDER_KEY = "payments.default_provider"
INTENT_EXPIRY_SECONDS_KEY = "payments.intent.expiry_seconds"

DEFAULT_PROVIDER = PaymentProvider.FAKE
DEFAULT_INTENT_EXPIRY_SECONDS = 900  # 15 minutes


class PaymentConfiguration:
    """Central resolver for all Payments module configuration values."""

    @classmethod
    def get_default_provider(cls, *, tenant_id: uuid.UUID) -> str:
        value = ConfigResolver.get_or_default(
            DEFAULT_PROVIDER_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_PROVIDER,
        )
        if isinstance(value, str) and value in PaymentProvider.values:
            return value
        return DEFAULT_PROVIDER

    @classmethod
    def get_intent_expiry_seconds(cls, *, tenant_id: uuid.UUID) -> int:
        value = ConfigResolver.get_or_default(
            INTENT_EXPIRY_SECONDS_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_INTENT_EXPIRY_SECONDS,
        )
        try:
            return int(value)
        except (TypeError, ValueError):
            return DEFAULT_INTENT_EXPIRY_SECONDS
