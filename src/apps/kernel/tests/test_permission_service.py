"""
Tests for PermissionService — Module 08 RBAC Enforcement foundation.

Covers: allow/deny, tenant isolation, missing-permission fail-closed,
missing-role-assignment fail-closed, scope matching, actor type support
(UserAccount and Person), the enforcement toggle, the PermissionDenied
event + audit trail, and the explicitly-audited system-context path.
"""

from unittest.mock import patch

from django.test import TestCase

from apps.kernel.models.audit import AuditLog
from apps.kernel.models.event_outbox import EventOutbox
from apps.kernel.services.errors import PermissionDenied
from apps.kernel.services.permission_service import PermissionService

from .rbac_helpers import grant_permissions, make_actor, make_tenant

PERMISSION_KEY = "finance.document.issue"


class PermissionServiceCheckTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.other_tenant = make_tenant("other")
        self.actor = make_actor(self.tenant)

    def test_check_allows_when_role_carries_permission(self):
        grant_permissions(self.tenant, self.actor, [PERMISSION_KEY])

        self.assertTrue(
            PermissionService.check(self.actor, PERMISSION_KEY, tenant_id=self.tenant.id),
        )

    def test_check_denies_when_role_lacks_permission(self):
        grant_permissions(self.tenant, self.actor, ["some.other.permission"])

        self.assertFalse(
            PermissionService.check(self.actor, PERMISSION_KEY, tenant_id=self.tenant.id),
        )

    def test_check_denies_when_no_role_assignment_exists(self):
        self.assertFalse(
            PermissionService.check(self.actor, PERMISSION_KEY, tenant_id=self.tenant.id),
        )

    def test_check_denies_across_tenants(self):
        grant_permissions(self.tenant, self.actor, [PERMISSION_KEY])

        self.assertFalse(
            PermissionService.check(self.actor, PERMISSION_KEY, tenant_id=self.other_tenant.id),
        )

    def test_check_denies_when_actor_is_none(self):
        self.assertFalse(
            PermissionService.check(None, PERMISSION_KEY, tenant_id=self.tenant.id),
        )

    def test_check_denies_when_tenant_id_is_none(self):
        grant_permissions(self.tenant, self.actor, [PERMISSION_KEY])

        self.assertFalse(
            PermissionService.check(self.actor, PERMISSION_KEY, tenant_id=None),
        )

    def test_check_denies_for_inactive_assignment(self):
        grant_permissions(self.tenant, self.actor, [PERMISSION_KEY], is_active=False)

        self.assertFalse(
            PermissionService.check(self.actor, PERMISSION_KEY, tenant_id=self.tenant.id),
        )

    def test_check_denies_for_expired_assignment(self):
        from django.utils import timezone

        grant_permissions(
            self.tenant,
            self.actor,
            [PERMISSION_KEY],
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )

        self.assertFalse(
            PermissionService.check(self.actor, PERMISSION_KEY, tenant_id=self.tenant.id),
        )

    def test_check_platform_scope_always_matches(self):
        grant_permissions(self.tenant, self.actor, [PERMISSION_KEY])  # blank scope_type == platform-wide

        self.assertTrue(
            PermissionService.check(
                self.actor,
                PERMISSION_KEY,
                tenant_id=self.tenant.id,
                scope={"scope_type": "organization", "scope_id": "11111111-1111-1111-1111-111111111111"},
            ),
        )

    def test_check_denies_scope_mismatch(self):
        import uuid

        org_a = uuid.uuid4()
        org_b = uuid.uuid4()
        grant_permissions(self.tenant, self.actor, [PERMISSION_KEY], scope_type="organization", scope_id=org_a)

        self.assertFalse(
            PermissionService.check(
                self.actor,
                PERMISSION_KEY,
                tenant_id=self.tenant.id,
                scope={"scope_type": "organization", "scope_id": org_b},
            ),
        )

    def test_check_allows_scope_match(self):
        import uuid

        org_a = uuid.uuid4()
        grant_permissions(self.tenant, self.actor, [PERMISSION_KEY], scope_type="organization", scope_id=org_a)

        self.assertTrue(
            PermissionService.check(
                self.actor,
                PERMISSION_KEY,
                tenant_id=self.tenant.id,
                scope={"scope_type": "organization", "scope_id": org_a},
            ),
        )

    def test_check_unscoped_call_does_not_match_organization_scoped_assignment(self):
        """Epic 05 (Permission-Key Registry & Authorization Hardening)
        scope validation hardening: an org-scoped RoleAssignment must not
        satisfy a platform-wide (unscoped) check — previously it did,
        since `scope is None` short-circuited True unconditionally."""
        import uuid

        grant_permissions(self.tenant, self.actor, [PERMISSION_KEY], scope_type="organization", scope_id=uuid.uuid4())

        self.assertFalse(
            PermissionService.check(self.actor, PERMISSION_KEY, tenant_id=self.tenant.id),
        )

    def test_check_scope_dict_missing_scope_type_fails_closed(self):
        import uuid

        org_a = uuid.uuid4()
        grant_permissions(self.tenant, self.actor, [PERMISSION_KEY], scope_type="organization", scope_id=org_a)

        self.assertFalse(
            PermissionService.check(
                self.actor,
                PERMISSION_KEY,
                tenant_id=self.tenant.id,
                scope={"scope_id": str(org_a)},
            ),
        )

    def test_check_scope_dict_missing_scope_id_fails_closed(self):
        import uuid

        org_a = uuid.uuid4()
        grant_permissions(self.tenant, self.actor, [PERMISSION_KEY], scope_type="organization", scope_id=org_a)

        self.assertFalse(
            PermissionService.check(
                self.actor,
                PERMISSION_KEY,
                tenant_id=self.tenant.id,
                scope={"scope_type": "organization"},
            ),
        )

    def test_check_null_scope_id_in_request_fails_closed(self):
        import uuid

        grant_permissions(self.tenant, self.actor, [PERMISSION_KEY], scope_type="organization", scope_id=uuid.uuid4())

        self.assertFalse(
            PermissionService.check(
                self.actor,
                PERMISSION_KEY,
                tenant_id=self.tenant.id,
                scope={"scope_type": "organization", "scope_id": None},
            ),
        )

    def test_check_malformed_assignment_with_null_scope_id_never_matches(self):
        """A RoleAssignment carrying a real scope_type but a null scope_id
        is malformed (should never have been created that way) — it must
        never authorize anything, even a request that also (coincidentally
        or maliciously) supplies scope_id=None."""
        grant_permissions(self.tenant, self.actor, [PERMISSION_KEY], scope_type="organization", scope_id=None)

        self.assertFalse(
            PermissionService.check(
                self.actor,
                PERMISSION_KEY,
                tenant_id=self.tenant.id,
                scope={"scope_type": "organization", "scope_id": None},
            ),
        )

    def test_check_string_and_uuid_scope_id_are_equivalent(self):
        """scope_id may be passed as a real UUID or its string form —
        both must be treated identically."""
        import uuid

        org_a = uuid.uuid4()
        grant_permissions(self.tenant, self.actor, [PERMISSION_KEY], scope_type="organization", scope_id=org_a)

        self.assertTrue(
            PermissionService.check(
                self.actor,
                PERMISSION_KEY,
                tenant_id=self.tenant.id,
                scope={"scope_type": "organization", "scope_id": str(org_a)},
            ),
        )
        self.assertTrue(
            PermissionService.check(
                self.actor,
                PERMISSION_KEY,
                tenant_id=self.tenant.id,
                scope={"scope_type": "organization", "scope_id": org_a},
            ),
        )

    def test_check_supports_person_actor(self):
        grant_permissions(self.tenant, self.actor, [PERMISSION_KEY])

        self.assertTrue(
            PermissionService.check(self.actor.person, PERMISSION_KEY, tenant_id=self.tenant.id),
        )


class PermissionServiceRequireTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()
        self.actor = make_actor(self.tenant)

    def test_require_passes_silently_when_authorized(self):
        grant_permissions(self.tenant, self.actor, [PERMISSION_KEY])

        PermissionService.require(self.actor, PERMISSION_KEY, tenant_id=self.tenant.id)  # must not raise

    def test_require_raises_permission_denied_when_unauthorized(self):
        with self.assertRaises(PermissionDenied):
            PermissionService.require(self.actor, PERMISSION_KEY, tenant_id=self.tenant.id)

    def test_require_denial_emits_event_and_audit(self):
        with self.assertRaises(PermissionDenied):
            PermissionService.require(self.actor, PERMISSION_KEY, tenant_id=self.tenant.id)

        self.assertTrue(
            EventOutbox.objects.filter(
                tenant_id=self.tenant.id,
                event_type="RBAC.PermissionDenied.v1",
            ).exists(),
        )
        self.assertTrue(
            AuditLog.objects.filter(
                tenant_id=self.tenant.id,
                action="rbac.permission.denied",
            ).exists(),
        )

    def test_require_denial_audit_includes_a_reason(self):
        """Epic 05 (Permission-Key Registry & Authorization Hardening)."""
        with self.assertRaises(PermissionDenied):
            PermissionService.require(self.actor, PERMISSION_KEY, tenant_id=self.tenant.id)

        entry = AuditLog.objects.get(tenant_id=self.tenant.id, action="rbac.permission.denied")
        self.assertTrue(entry.reason)

    def test_require_is_noop_when_enforcement_disabled(self):
        with patch(
            "apps.kernel.services.permission_service.RBACConfiguration.get_enforcement_enabled",
            return_value=False,
        ):
            PermissionService.require(self.actor, PERMISSION_KEY, tenant_id=self.tenant.id)  # must not raise

        self.assertFalse(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action="rbac.permission.denied").exists(),
        )

    def test_require_with_actor_none_does_not_raise_and_is_audited(self):
        PermissionService.require(None, PERMISSION_KEY, tenant_id=self.tenant.id)  # must not raise

        self.assertTrue(
            AuditLog.objects.filter(
                tenant_id=self.tenant.id,
                action="rbac.permission.system_context",
            ).exists(),
        )
        # System-context is explicitly NOT a denial: no PermissionDenied event.
        self.assertFalse(
            EventOutbox.objects.filter(
                tenant_id=self.tenant.id,
                event_type="RBAC.PermissionDenied.v1",
            ).exists(),
        )


class PermissionServiceOwnershipAuthorizedTest(TestCase):
    """ownership_authorized_by — Enterprise Architecture Review follow-up,
    finding #5. A real, named actor whose authority comes from a verified
    ownership check upstream, not (yet) an RBAC role."""

    def setUp(self):
        self.tenant = make_tenant()
        self.actor = make_actor(self.tenant)

    def test_ownership_fallback_does_not_raise_when_actor_has_no_role(self):
        PermissionService.require(
            None,
            PERMISSION_KEY,
            tenant_id=self.tenant.id,
            ownership_authorized_by=self.actor,
        )  # must not raise

    def test_ownership_fallback_is_audited_as_ownership_authorized_not_system(self):
        PermissionService.require(
            None,
            PERMISSION_KEY,
            tenant_id=self.tenant.id,
            ownership_authorized_by=self.actor,
        )

        entry = AuditLog.objects.get(tenant_id=self.tenant.id, action="rbac.permission.ownership_authorized")
        self.assertEqual(entry.actor_id, self.actor.person_id)
        self.assertEqual(entry.actor_type, "user")

        # The point of this finding: no "system" mislabeling for this call.
        self.assertFalse(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action="rbac.permission.system_context").exists(),
        )

    def test_ownership_fallback_audit_flags_when_actor_has_no_role_assignment_at_all(self):
        """Epic 05 (Permission-Key Registry & Authorization Hardening)
        ownership-fallback observability: has_any_role_assignment=False
        when the actor genuinely has zero RBAC setup — distinguishing
        "backfill hasn't run yet" from a scope/grant mismatch."""
        PermissionService.require(
            None,
            PERMISSION_KEY,
            tenant_id=self.tenant.id,
            ownership_authorized_by=self.actor,
        )

        entry = AuditLog.objects.get(tenant_id=self.tenant.id, action="rbac.permission.ownership_authorized")
        self.assertFalse(entry.metadata["has_any_role_assignment"])

    def test_ownership_fallback_audit_flags_when_actor_has_a_non_matching_role_assignment(self):
        """The actor holds a real RoleAssignment — just not one granting
        this permission_key/scope. has_any_role_assignment=True is the
        more actionable signal here (a grant mistake, not a missing
        backfill)."""
        grant_permissions(self.tenant, self.actor, ["some.other.permission"])

        PermissionService.require(
            None,
            PERMISSION_KEY,
            tenant_id=self.tenant.id,
            ownership_authorized_by=self.actor,
        )

        entry = AuditLog.objects.get(tenant_id=self.tenant.id, action="rbac.permission.ownership_authorized")
        self.assertTrue(entry.metadata["has_any_role_assignment"])

    def test_ownership_fallback_does_not_emit_permission_denied_event(self):
        PermissionService.require(
            None,
            PERMISSION_KEY,
            tenant_id=self.tenant.id,
            ownership_authorized_by=self.actor,
        )

        self.assertFalse(
            EventOutbox.objects.filter(
                tenant_id=self.tenant.id,
                event_type="RBAC.PermissionDenied.v1",
            ).exists(),
        )

    def test_real_rbac_role_is_used_when_present_no_ownership_audit_entry(self):
        """The whole point of trying ownership_authorized_by as a normal
        actor first: the moment a real RoleAssignment exists, enforcement
        just works, and the ownership-authorized fallback path is never
        reached at all."""
        grant_permissions(self.tenant, self.actor, [PERMISSION_KEY])

        PermissionService.require(
            None,
            PERMISSION_KEY,
            tenant_id=self.tenant.id,
            ownership_authorized_by=self.actor,
        )  # must not raise

        self.assertFalse(
            AuditLog.objects.filter(
                tenant_id=self.tenant.id,
                action="rbac.permission.ownership_authorized",
            ).exists(),
        )
        self.assertFalse(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action="rbac.permission.system_context").exists(),
        )

    def test_explicit_actor_takes_precedence_over_ownership_authorized_by(self):
        """If both are somehow supplied, the explicit actor is authoritative
        — ownership_authorized_by is only ever a fallback for actor=None."""
        other_actor = make_actor(self.tenant, full_name="Other Actor")

        with self.assertRaises(PermissionDenied):
            PermissionService.require(
                self.actor,
                PERMISSION_KEY,
                tenant_id=self.tenant.id,
                ownership_authorized_by=other_actor,
            )

        self.assertTrue(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action="rbac.permission.denied").exists(),
        )
