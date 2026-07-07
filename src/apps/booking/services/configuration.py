"""
Booking Configuration wrapper — Module 03 Booking foundation.

Assignment service code must never call ConfigResolver directly. All
booking-specific config keys and defaults are centralized here, mirroring
apps.matching.services.configuration.MatchingConfiguration.
"""

import uuid

from apps.kernel.services.config_resolver import ConfigResolver

AUTO_ACCEPT_ENABLED_KEY = "booking.assignment.auto_accept_enabled"
REASSIGNMENT_ENABLED_KEY = "booking.reassignment.enabled"

DEFAULT_AUTO_ACCEPT_ENABLED = False
DEFAULT_REASSIGNMENT_ENABLED = True


class BookingConfiguration:
    """Central resolver for all Booking module configuration values."""

    @classmethod
    def get_auto_accept_enabled(cls, *, tenant_id: uuid.UUID) -> bool:
        value = ConfigResolver.get_or_default(
            AUTO_ACCEPT_ENABLED_KEY, tenant_id=tenant_id, default=DEFAULT_AUTO_ACCEPT_ENABLED,
        )
        return cls._to_bool(value, DEFAULT_AUTO_ACCEPT_ENABLED)

    @classmethod
    def get_reassignment_enabled(cls, *, tenant_id: uuid.UUID) -> bool:
        value = ConfigResolver.get_or_default(
            REASSIGNMENT_ENABLED_KEY, tenant_id=tenant_id, default=DEFAULT_REASSIGNMENT_ENABLED,
        )
        return cls._to_bool(value, DEFAULT_REASSIGNMENT_ENABLED)

    @staticmethod
    def _to_bool(value, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return default
