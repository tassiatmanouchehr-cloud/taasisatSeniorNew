"""
RBAC permission_key taxonomy for the admin portal — Module 19.

Epic 05 (Permission-Key Registry & Authorization Hardening): this module
is now a re-export facade over the canonical registry
(apps.kernel.permissions.keys) — the constant *values* and local names are
both unchanged; only registration/metadata/duplicate-detection moved to
one place. Every existing `from apps.admin_portal.permission_keys import
X` call site is unaffected.
"""

from apps.kernel.permissions.keys import (
    ADMIN_FINANCE_READ as FINANCE_READ,
)
from apps.kernel.permissions.keys import (
    ADMIN_ORDERS_READ as ORDERS_READ,
)
from apps.kernel.permissions.keys import (
    ADMIN_PORTAL_ACCESS as PORTAL_ACCESS,
)
from apps.kernel.permissions.keys import (
    ADMIN_SUPPLIERS_READ as SUPPLIERS_READ,
)
from apps.kernel.permissions.keys import (
    ADMIN_SYSTEM_READ as SYSTEM_READ,
)
from apps.kernel.permissions.keys import (
    ADMIN_RBAC_ENFORCEMENT_READ as RBAC_ENFORCEMENT_READ,
)
from apps.kernel.permissions.keys import (
    ADMIN_TENANTS_READ as TENANTS_READ,
)
from apps.kernel.permissions.keys import (
    ACCOUNTS_DOCUMENT_REVIEW as DOCUMENT_REVIEW,
)
from apps.kernel.permissions.keys import (
    ACCOUNTS_PROFILE_ACTIVATE as PROFILE_ACTIVATE,
)
from apps.kernel.permissions.keys import (
    COMMISSION_DISPUTE_RESOLVE,
    COMMISSION_ESCROW_VIEW,
)

__all__ = [
    "PORTAL_ACCESS",
    "TENANTS_READ",
    "SUPPLIERS_READ",
    "ORDERS_READ",
    "FINANCE_READ",
    "SYSTEM_READ",
    "RBAC_ENFORCEMENT_READ",
    "COMMISSION_ESCROW_VIEW",
    "COMMISSION_DISPUTE_RESOLVE",
    "DOCUMENT_REVIEW",
    "PROFILE_ACTIVATE",
]
