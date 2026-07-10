"""
PermissionService — Module 08 RBAC Enforcement foundation.

The ONLY code allowed to evaluate Role / Permission / RoleAssignment records
for an authorization decision. Business modules call check()/require() —
they never query RoleAssignment directly and never hardcode role slugs.

Evaluation is fail-closed: no tenant, no actor, no matching active
RoleAssignment, or a role that doesn't carry the requested permission_key
all deny. The one deliberate exception is `require()` being called with
actor=None, which today only happens from true internal/system call sites
(no real human initiated the call) — that path is explicitly audited as
system context, not silently allowed. See Module 08 sprint report for the
follow-up once real actors are wired through everywhere.

`ownership_authorized_by` (Epic 02 Enterprise Architecture Review,
finding #5) is a second, narrower exception for a real, named human whose
authority to call this comes from a verified ownership check upstream
(e.g. "you administer this organization"), not from an RBAC role
assignment that doesn't exist for them yet. It is tried as a normal RBAC
actor first — the moment a real `RoleAssignment` exists for them, this
call is fully, normally enforced with zero further code changes anywhere.
Only on RBAC failure does it fall back to an explicit
`rbac.permission.ownership_authorized` audit entry, correctly attributed
to that real actor — never silently logged as `system_context`, and never
silently allowed as if unauthenticated. See
docs/architecture/GAP_ANALYSIS.md for the tracked follow-up (seed real
organization-scoped roles, then this parameter becomes unnecessary for
that call site).

References:
- ADR-001.13 (RBAC evaluation belongs to Module 08)
- apps.kernel.models.rbac (Role / Permission / RoleAssignment — M25-owned data)
"""

import logging
import uuid
from typing import Any

from django.utils import timezone

from apps.kernel.models.rbac import RoleAssignment
from apps.kernel.models.user import Person, UserAccount
from apps.kernel.services.audit_service import AuditService
from apps.kernel.services.event_publisher import EventPublisher

from .errors import PermissionDenied
from .rbac_configuration import RBACConfiguration

logger = logging.getLogger(__name__)

SOURCE_MODULE = "M08"


class PermissionService:
    """Central, sole evaluator of RBAC authorization decisions."""

    @classmethod
    def check(cls, actor, permission_key: str, *, tenant_id, scope: dict[str, Any] | None = None) -> bool:
        """Pure evaluation: does `actor` hold `permission_key` in `tenant_id` (optionally scoped)?

        Ignores the enforcement toggle — this always reflects the true
        RBAC state, independent of whether require() would currently enforce it.
        """
        if not tenant_id or actor is None or not permission_key:
            return False

        actor_filter = cls._actor_filter(actor)
        if actor_filter is None:
            return False

        now = timezone.now()
        assignments = RoleAssignment.objects.filter(
            tenant_id=tenant_id, is_active=True, **actor_filter,
        ).select_related("role")

        for assignment in assignments:
            if assignment.expires_at is not None and assignment.expires_at <= now:
                continue
            if not cls._scope_matches(assignment, scope):
                continue
            if permission_key in (assignment.role.permissions or []):
                return True

        return False

    @classmethod
    def require(
        cls,
        actor,
        permission_key: str,
        *,
        tenant_id,
        scope: dict[str, Any] | None = None,
        ownership_authorized_by=None,
    ) -> None:
        """Enforce `check()`, raising PermissionDenied (and auditing) on failure.

        No-ops entirely if RBACConfiguration.get_enforcement_enabled(tenant_id) is False.

        ownership_authorized_by: only consulted when actor is None. See the
        module docstring for the full reasoning — in short, a real, named
        human whose authority comes from a verified ownership check
        upstream, not (yet) an RBAC role. Tried as a normal actor first;
        only falls back to an explicit, correctly-attributed
        "ownership_authorized" audit entry if that actor genuinely has no
        matching RoleAssignment — never silently logged as system context.
        """
        if not RBACConfiguration.get_enforcement_enabled(tenant_id=tenant_id):
            return

        if actor is None and ownership_authorized_by is None:
            # True system/internal context — no actor was ever supplied.
            # Audited, not a silent bypass.
            AuditService.log_security(
                tenant_id=tenant_id,
                action="rbac.permission.system_context",
                resource_type="Permission",
                module_id=SOURCE_MODULE,
                actor_type="system",
                after={"permission_key": permission_key, "scope": scope or {}},
            )
            return

        is_ownership_fallback = actor is None
        effective_actor = actor if actor is not None else ownership_authorized_by

        if cls.check(effective_actor, permission_key, tenant_id=tenant_id, scope=scope):
            return

        if is_ownership_fallback:
            # A real, named actor was supplied but holds no matching RBAC
            # role yet. Rather than deny (breaking every caller of this
            # shape before scoped RBAC seeding exists) or mislabel this as
            # system context, audit it explicitly and honestly as a real,
            # ownership-authorized human action.
            AuditService.log_security(
                tenant_id=tenant_id,
                action="rbac.permission.ownership_authorized",
                resource_type="Permission",
                module_id=SOURCE_MODULE,
                actor_id=cls._actor_id(effective_actor),
                actor_type="user",
                after={"permission_key": permission_key, "scope": scope or {}},
                reason=(
                    "Actor authorized by a verified ownership check upstream, "
                    "not by an RBAC role assignment."
                ),
            )
            return

        actor_id = cls._actor_id(effective_actor)
        EventPublisher.publish(
            tenant_id=tenant_id,
            event_type="RBAC.PermissionDenied.v1",
            source_module=SOURCE_MODULE,
            source_entity_id=actor_id,
            source_entity_type="Actor",
            payload={
                "permission_key": permission_key,
                "scope": scope or {},
                "actor_id": str(actor_id) if actor_id else None,
            },
            actor_id=actor_id,
        )
        AuditService.log_security(
            tenant_id=tenant_id,
            action="rbac.permission.denied",
            resource_type="Permission",
            module_id=SOURCE_MODULE,
            actor_id=actor_id,
            after={"permission_key": permission_key, "scope": scope or {}},
        )

        raise PermissionDenied(f"Actor is not authorized for '{permission_key}'.")

    # --- internal helpers -------------------------------------------------

    @staticmethod
    def _actor_filter(actor) -> dict[str, Any] | None:
        if isinstance(actor, UserAccount):
            return {"user_id": actor.id}
        if isinstance(actor, Person):
            return {"user__person_id": actor.id}
        return None

    @staticmethod
    def _actor_id(actor) -> uuid.UUID | None:
        if isinstance(actor, UserAccount):
            return actor.person_id
        if isinstance(actor, Person):
            return actor.id
        return None

    @staticmethod
    def _scope_matches(assignment: RoleAssignment, scope: dict[str, Any] | None) -> bool:
        if scope is None:
            return True
        if not assignment.scope_type or assignment.scope_type == "platform":
            return True
        return (
            assignment.scope_type == scope.get("scope_type")
            and str(assignment.scope_id) == str(scope.get("scope_id"))
        )
