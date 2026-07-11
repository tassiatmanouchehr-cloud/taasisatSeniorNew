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

Security contract of `ownership_authorized_by` (Epic 05 Architecture
Review, Major finding M1 — documentation clarification, not a behavior
change): `ownership_authorized_by` is **not, on its own, a standalone
authorization boundary**. `PermissionService` does not and cannot
independently verify that the actor passed as `ownership_authorized_by`
actually owns or administers the resource in question — it assumes the
caller has already established that upstream, before this method is ever
invoked. The normal production path is: request -> the calling
portal/service resolves the caller's own organization/resource (e.g.
`apps.organization_portal.permissions.resolve_organization()`) -> that
resolution *is* the ownership verification -> `PermissionService.require()`
is called with the now-verified actor -> real RBAC evaluation is tried
first -> the audited ownership fallback is used only when a matching
`RoleAssignment` has not yet been synced for that actor. If a caller ever
passes the wrong actor as `ownership_authorized_by` (e.g. an admin who
administers a *different* organization than the resource being acted on),
`PermissionService` will still authorize that call once it falls back to
the ownership-authorized path — the fallback audits and allows a
verified-by-construction actor, it does not re-derive or re-check that
verification. **This is a caller bug, not a `PermissionService` bug**:
callers of `require(..., ownership_authorized_by=...)` are responsible
for having already verified ownership, in the same way `require(actor,
...)`'s own real-RBAC path trusts that `actor` is a genuine, already-
authenticated identity. See `docs/architecture/rbac-permissions.md` for
the call-site-level restatement of this contract.

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
            #
            # Epic 05 (Permission-Key Registry & Authorization Hardening)
            # ownership-fallback observability: has_any_role_assignment
            # distinguishes "this actor has zero RBAC setup at all" from
            # "this actor holds some RoleAssignment, just not one matching
            # this permission_key/scope" — the second case is the more
            # actionable signal (a scope or permission-grant mistake,
            # rather than a backfill that simply hasn't run yet).
            has_any_role_assignment = cls._actor_filter(effective_actor) is not None and RoleAssignment.objects.filter(
                tenant_id=tenant_id, is_active=True, **cls._actor_filter(effective_actor),
            ).exists()
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
                metadata={"has_any_role_assignment": has_any_role_assignment},
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
            reason="No active RoleAssignment grants this permission_key in the requested scope.",
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
        """
        Epic 05 (Permission-Key Registry & Authorization Hardening) scope
        validation hardening. An unscoped or explicitly platform-scoped
        assignment is the broadest possible grant and satisfies any
        request, scoped or not — unchanged from before this Epic.

        Everything below this point is new: an assignment carrying a real,
        narrower scope (e.g. "organization") can only satisfy a request
        that asks for that exact scope. Previously, `scope is None`
        short-circuited `True` unconditionally — meaning an
        organization-scoped RoleAssignment also satisfied a platform-wide
        (unscoped) check, a gap identified and deliberately left unfixed
        during Epic 04 (Enterprise Organization Isolation) pending this
        Epic. Not exploitable by any call site that existed before this
        Epic (every organization-scoped grant was new in Epic 04, and
        every organization-isolation enforcement point already passes an
        explicit scope) — closed here before a future caller could depend
        on the looser behavior.

        Fails closed, explicitly, for every malformed shape: a `scope`
        dict missing `scope_type`/`scope_id` entirely, and an assignment
        row whose own `scope_id` is None despite carrying a real
        `scope_type` (a malformed RoleAssignment, not a valid platform
        grant) — the previous implementation only failed on these
        incidentally, via `str(None) == str(some_uuid)` comparisons, which
        breaks the moment both sides are coincidentally None.
        """
        if not assignment.scope_type or assignment.scope_type == "platform":
            return True

        if scope is None:
            return False

        if "scope_type" not in scope or "scope_id" not in scope:
            return False

        if assignment.scope_id is None:
            return False

        return (
            assignment.scope_type == scope.get("scope_type")
            and scope.get("scope_id") is not None
            and str(assignment.scope_id) == str(scope.get("scope_id"))
        )
