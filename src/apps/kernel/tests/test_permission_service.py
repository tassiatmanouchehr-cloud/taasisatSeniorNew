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
            self.tenant, self.actor, [PERMISSION_KEY],
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )

        self.assertFalse(
            PermissionService.check(self.actor, PERMISSION_KEY, tenant_id=self.tenant.id),
        )

    def test_check_platform_scope_always_matches(self):
        grant_permissions(self.tenant, self.actor, [PERMISSION_KEY])  # blank scope_type == platform-wide

        self.assertTrue(
            PermissionService.check(
                self.actor, PERMISSION_KEY, tenant_id=self.tenant.id,
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
                self.actor, PERMISSION_KEY, tenant_id=self.tenant.id,
                scope={"scope_type": "organization", "scope_id": org_b},
            ),
        )

    def test_check_allows_scope_match(self):
        import uuid

        org_a = uuid.uuid4()
        grant_permissions(self.tenant, self.actor, [PERMISSION_KEY], scope_type="organization", scope_id=org_a)

        self.assertTrue(
            PermissionService.check(
                self.actor, PERMISSION_KEY, tenant_id=self.tenant.id,
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
                tenant_id=self.tenant.id, event_type="RBAC.PermissionDenied.v1",
            ).exists(),
        )
        self.assertTrue(
            AuditLog.objects.filter(
                tenant_id=self.tenant.id, action="rbac.permission.denied",
            ).exists(),
        )

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
                tenant_id=self.tenant.id, action="rbac.permission.system_context",
            ).exists(),
        )
        # System-context is explicitly NOT a denial: no PermissionDenied event.
        self.assertFalse(
            EventOutbox.objects.filter(
                tenant_id=self.tenant.id, event_type="RBAC.PermissionDenied.v1",
            ).exists(),
        )
