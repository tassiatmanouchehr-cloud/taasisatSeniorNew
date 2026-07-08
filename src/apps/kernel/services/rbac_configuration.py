"""
RBAC Configuration wrapper — Module 08 RBAC Enforcement foundation.

PermissionService must never call ConfigResolver directly — all Module 08
config keys and defaults are centralized here, mirroring
apps.booking.services.configuration.BookingConfiguration.
"""

import uuid

from apps.kernel.services.config_resolver import ConfigResolver

ENFORCEMENT_ENABLED_KEY = "rbac.enforcement.enabled"

DEFAULT_ENFORCEMENT_ENABLED = True


class RBACConfiguration:
    """Central resolver for all Module 08 RBAC configuration values."""

    @classmethod
    def get_enforcement_enabled(cls, *, tenant_id: uuid.UUID) -> bool:
        value = ConfigResolver.get_or_default(
            ENFORCEMENT_ENABLED_KEY, tenant_id=tenant_id, default=DEFAULT_ENFORCEMENT_ENABLED,
        )
        return cls._to_bool(value, DEFAULT_ENFORCEMENT_ENABLED)

    @staticmethod
    def _to_bool(value, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return default
