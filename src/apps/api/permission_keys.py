"""
RBAC permission_key taxonomy — Module 17A/17B, documented in
docs/architecture/rbac-permissions.md.

Epic 05 (Permission-Key Registry & Authorization Hardening): this module
is now a re-export facade over the canonical registry
(apps.kernel.permissions.keys) — the constant *values* are unchanged
(same strings, same behavior), but registration/metadata/duplicate-
detection now lives in exactly one place. Every existing `from
apps.api.permission_keys import X` call site is unaffected; this file's
public names are preserved for that reason.
"""

from apps.kernel.permissions.keys import (
    DISCOVERY_SUPPLIERS_READ,
    PAYMENTS_ATTEMPTS_CREATE,
    PAYMENTS_INTENTS_CREATE,
    PRICING_QUOTES_CREATE,
    REPORTING_READ,
    REVIEWS_READ,
    REVIEWS_SUBMIT,
    WALLET_READ,
)

__all__ = [
    "REPORTING_READ",
    "DISCOVERY_SUPPLIERS_READ",
    "PRICING_QUOTES_CREATE",
    "REVIEWS_SUBMIT",
    "REVIEWS_READ",
    "WALLET_READ",
    "PAYMENTS_INTENTS_CREATE",
    "PAYMENTS_ATTEMPTS_CREATE",
]
