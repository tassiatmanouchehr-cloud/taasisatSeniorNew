"""
RBAC permission_key taxonomy for apps.finance — Epic 05 (Permission-Key
Registry & Authorization Hardening).

Re-export facade over the canonical registry (apps.kernel.permissions
.keys) — replaces five literal permission-key strings previously
hardcoded directly in ledger_service.py/payment_service.py
/settlement_service.py/document_service.py.
"""

from apps.kernel.permissions.keys import (
    FINANCE_DOCUMENT_ISSUE,
    FINANCE_DOCUMENT_LOCK,
    FINANCE_LEDGER_POST,
    FINANCE_PAYMENT_RECORD,
    FINANCE_SETTLEMENT_CREATE_BATCH,
)

__all__ = [
    "FINANCE_LEDGER_POST",
    "FINANCE_PAYMENT_RECORD",
    "FINANCE_SETTLEMENT_CREATE_BATCH",
    "FINANCE_DOCUMENT_ISSUE",
    "FINANCE_DOCUMENT_LOCK",
]
