"""
Reporting Configuration wrapper — Module 16 foundation.

Reporting service code must never call ConfigResolver directly. All
reporting-specific config keys and defaults are centralized here, mirroring
apps.wallet.services.configuration.WalletConfiguration.
"""

import uuid

from apps.kernel.services.config_resolver import ConfigResolver

CATEGORY_DISTRIBUTION_LIMIT_KEY = "reporting.marketplace.category_distribution_limit"
DEFAULT_CATEGORY_DISTRIBUTION_LIMIT = 10


class ReportingConfiguration:
    """Central resolver for all Reporting module configuration values."""

    @classmethod
    def get_category_distribution_limit(cls, *, tenant_id: uuid.UUID) -> int:
        value = ConfigResolver.get_or_default(
            CATEGORY_DISTRIBUTION_LIMIT_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_CATEGORY_DISTRIBUTION_LIMIT,
        )
        try:
            resolved = int(value)
        except (TypeError, ValueError):
            return DEFAULT_CATEGORY_DISTRIBUTION_LIMIT
        return resolved if resolved > 0 else DEFAULT_CATEGORY_DISTRIBUTION_LIMIT
