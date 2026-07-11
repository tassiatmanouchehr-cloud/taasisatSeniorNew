"""
RBAC permission_key taxonomy for apps.booking — Epic 05 (Permission-Key
Registry & Authorization Hardening).

Re-export facade over the canonical registry (apps.kernel.permissions
.keys) — same convention as apps.api.permission_keys/apps.admin_portal
.permission_keys/apps.accounts.permission_keys. Replaces the literal
string `"booking.assignment.assign"` that AssignmentService.assign()
previously hardcoded directly.
"""

from apps.kernel.permissions.keys import BOOKING_ASSIGNMENT_ASSIGN

__all__ = ["BOOKING_ASSIGNMENT_ASSIGN"]
