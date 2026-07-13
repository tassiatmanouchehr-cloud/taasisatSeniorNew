"""Tests proving every gated commission-write action denies an unauthorized
actor and produces zero business-side effects when denied."""

from apps.commission.services.cooperation_type import CooperationType
from apps.commission.services.policy_service import CommissionPolicyService
from apps.kernel.services.errors import PermissionDenied
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor

from .helpers import CommissionTestCase


class CommissionPolicyPermissionEnforcementTest(CommissionTestCase):
    def setUp(self):
        super().setUp()
        self.unauthorized_actor = make_actor(self.tenant, full_name="No Permission Actor")

    def test_set_global_defaults_denied_without_permission(self):
        from apps.commission.services.policy_service import DEFAULT_SHARES

        with self.assertRaises(PermissionDenied):
            CommissionPolicyService.set_global_defaults(
                tenant_id=self.tenant.id,
                payload=DEFAULT_SHARES,
                change_reason="x",
                actor=self.unauthorized_actor,
            )

        self.assertIsNone(CommissionPolicyService.get_global_defaults(tenant_id=self.tenant.id))

    def test_set_global_defaults_allowed_with_permission(self):
        from apps.commission.services.policy_service import DEFAULT_SHARES

        grant_permissions(self.tenant, self.unauthorized_actor, ["commission.policy.manage"])
        version = CommissionPolicyService.set_global_defaults(
            tenant_id=self.tenant.id,
            payload=DEFAULT_SHARES,
            change_reason="x",
            actor=self.unauthorized_actor,
        )
        self.assertIsNotNone(version)

    def test_set_cooperation_default_denied_without_permission(self):
        with self.assertRaises(PermissionDenied):
            CommissionPolicyService.set_cooperation_default(
                tenant_id=self.tenant.id,
                key=CooperationType.INDEPENDENT,
                shares={"platform": 15, "company": 0, "caregiver": 85},
                change_reason="x",
                actor=self.unauthorized_actor,
            )
        self.assertIsNone(
            CommissionPolicyService.get_cooperation_default(tenant_id=self.tenant.id, key=CooperationType.INDEPENDENT)
        )

    def test_set_platform_override_denied_without_permission(self):
        import uuid

        with self.assertRaises(PermissionDenied):
            CommissionPolicyService.set_platform_override(
                tenant_id=self.tenant.id,
                key=CooperationType.INDEPENDENT,
                party_scope_type="caregiver",
                party_id=uuid.uuid4(),
                shares={"platform": 15, "company": 0, "caregiver": 85},
                change_reason="x",
                actor=self.unauthorized_actor,
            )

    def test_seeding_uses_system_context_not_a_real_actor(self):
        """seed_commission_defaults is a bootstrap management command — it
        must succeed with no actor at all (system context), matching every
        other one-time bootstrap/settlement system-context call in this
        codebase."""
        version = CommissionPolicyService.seed_defaults_if_missing(tenant_id=self.tenant.id)
        self.assertIsNotNone(version)
