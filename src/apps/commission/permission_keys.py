"""
RBAC permission_key taxonomy for apps.commission — Financial Core PR-A.

Re-export facade over the canonical registry (apps.kernel.permissions.keys),
mirroring apps.finance.permission_keys/apps.booking.permission_keys.
"""

from apps.kernel.permissions.keys import (
    COMMISSION_CONTRACT_APPROVE,
    COMMISSION_CONTRACT_PROPOSE,
    COMMISSION_CONTRACT_TERMINATE,
    COMMISSION_DEADLINE_EXTEND,
    COMMISSION_POLICY_MANAGE,
)

__all__ = [
    "COMMISSION_POLICY_MANAGE",
    "COMMISSION_CONTRACT_PROPOSE",
    "COMMISSION_CONTRACT_APPROVE",
    "COMMISSION_CONTRACT_TERMINATE",
    "COMMISSION_DEADLINE_EXTEND",
]
