"""
Pricing Configuration wrapper — Module 11 foundation.

Pricing service code must never call ConfigResolver directly. All
pricing-specific config keys and defaults are centralized here, mirroring
apps.booking.services.configuration.BookingConfiguration.
"""

import uuid

from apps.kernel.services.config_resolver import ConfigResolver

WEEKEND_DAYS_KEY = "pricing.weekend.days"

# Friday=4, Saturday=5 (Python date.weekday(): Monday=0..Sunday=6). This is a
# configurable DEFAULT ASSUMPTION, not a hardcoded business rule — tenants
# that observe a different weekend (e.g. Thursday/Friday) must override
# `pricing.weekend.days` via ConfigResolver.
DEFAULT_WEEKEND_DAYS = [4, 5]


class PricingConfiguration:
    """Central resolver for all Pricing module configuration values."""

    @classmethod
    def get_weekend_days(cls, *, tenant_id: uuid.UUID) -> list[int]:
        value = ConfigResolver.get_or_default(
            WEEKEND_DAYS_KEY,
            tenant_id=tenant_id,
            default=DEFAULT_WEEKEND_DAYS,
        )
        if isinstance(value, list) and all(isinstance(v, int) for v in value):
            return value
        return DEFAULT_WEEKEND_DAYS
