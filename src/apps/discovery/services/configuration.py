"""
Discovery Configuration wrapper — Module 12 foundation.

Discovery service code must never call ConfigResolver directly. All
discovery-specific config keys and defaults are centralized here, mirroring
apps.booking.services.configuration.BookingConfiguration.
"""

import uuid
from decimal import Decimal

from apps.kernel.services.config_resolver import ConfigResolver

VERIFICATION_WEIGHT_KEY = "discovery.ranking.weight.verification"
REPUTATION_WEIGHT_KEY = "discovery.ranking.weight.reputation"
AVAILABILITY_WEIGHT_KEY = "discovery.ranking.weight.availability"
CAPACITY_WEIGHT_KEY = "discovery.ranking.weight.capacity"

DEFAULT_RANKING_WEIGHTS = {
    "verification": Decimal("1.0"),
    "reputation": Decimal("1.0"),
    "availability": Decimal("1.0"),
    "capacity": Decimal("1.0"),
}

# Platform-wide bound on page size — a fixed safety limit, not yet
# tenant-configurable (no requirement to make it so in this foundation).
DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class DiscoveryConfiguration:
    """Central resolver for all Discovery module configuration values."""

    @classmethod
    def get_ranking_weights(cls, *, tenant_id: uuid.UUID) -> dict[str, Decimal]:
        return {
            "verification": cls._get_decimal(VERIFICATION_WEIGHT_KEY, tenant_id, DEFAULT_RANKING_WEIGHTS["verification"]),
            "reputation": cls._get_decimal(REPUTATION_WEIGHT_KEY, tenant_id, DEFAULT_RANKING_WEIGHTS["reputation"]),
            "availability": cls._get_decimal(AVAILABILITY_WEIGHT_KEY, tenant_id, DEFAULT_RANKING_WEIGHTS["availability"]),
            "capacity": cls._get_decimal(CAPACITY_WEIGHT_KEY, tenant_id, DEFAULT_RANKING_WEIGHTS["capacity"]),
        }

    @staticmethod
    def _get_decimal(key: str, tenant_id: uuid.UUID, default: Decimal) -> Decimal:
        value = ConfigResolver.get_or_default(key, tenant_id=tenant_id, default=default)
        try:
            return value if isinstance(value, Decimal) else Decimal(str(value))
        except (ValueError, ArithmeticError):
            return default
