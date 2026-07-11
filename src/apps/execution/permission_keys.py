"""
RBAC permission_key taxonomy for apps.execution — Epic 05 (Permission-Key
Registry & Authorization Hardening).

Re-export facade over the canonical registry (apps.kernel.permissions
.keys) — replaces the literal string `"execution.session.close"`
previously hardcoded directly in session_service.py.
"""

from apps.kernel.permissions.keys import EXECUTION_SESSION_CLOSE

__all__ = ["EXECUTION_SESSION_CLOSE"]
