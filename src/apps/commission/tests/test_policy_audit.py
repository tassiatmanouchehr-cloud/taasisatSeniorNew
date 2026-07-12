"""Remediation 4 (System Architect Review of PR #44): every commission
policy write (global defaults / cooperation-type default / platform
override) must produce a FINANCIAL-classified AuditLog entry — previously
these three CommissionPolicyService methods only inherited PolicyService
.create_policy()'s plain logger.info() call, with no queryable audit trail
at all."""

from apps.commission.services.cooperation_type import CooperationType
from apps.commission.services.policy_service import DEFAULT_SHARES, CommissionPolicyService
from apps.kernel.models.audit import AuditClassification, AuditLog
from apps.kernel.services.errors import PermissionDenied
from apps.kernel.tests.rbac_helpers import grant_permissions, make_actor

from .helpers import CommissionTestCase


class CommissionPolicyAuditTest(CommissionTestCase):
    def setUp(self):
        super().setUp()
        self.actor = make_actor(self.tenant, full_name="Platform Accounting")
        grant_permissions(self.tenant, self.actor, ["commission.policy.manage"])

    def _entries(self, action):
        return AuditLog.objects.filter(tenant_id=self.tenant.id, action=action).order_by("occurred_at")

    def test_set_global_defaults_writes_one_financial_audit_entry(self):
        CommissionPolicyService.set_global_defaults(
            tenant_id=self.tenant.id,
            payload=DEFAULT_SHARES,
            change_reason="initial",
            actor=self.actor,
        )
        entries = self._entries("commission.policy.global_defaults.set")
        self.assertEqual(entries.count(), 1)
        entry = entries.first()
        self.assertEqual(entry.audit_class, AuditClassification.FINANCIAL)
        self.assertEqual(entry.actor_id, self.actor.person_id)
        self.assertIsNone(entry.before_snapshot)
        self.assertIsNotNone(entry.after_snapshot)

    def test_set_global_defaults_second_write_records_before_and_after(self):
        CommissionPolicyService.set_global_defaults(
            tenant_id=self.tenant.id,
            payload=DEFAULT_SHARES,
            change_reason="initial",
            actor=self.actor,
        )
        first_version = CommissionPolicyService.get_global_defaults(tenant_id=self.tenant.id)

        changed = {**DEFAULT_SHARES, CooperationType.INDEPENDENT: {"platform": 25, "company": 0, "caregiver": 75}}
        CommissionPolicyService.set_global_defaults(
            tenant_id=self.tenant.id,
            payload=changed,
            change_reason="rate change",
            actor=self.actor,
        )
        second_version = CommissionPolicyService.get_global_defaults(tenant_id=self.tenant.id)

        entries = list(self._entries("commission.policy.global_defaults.set"))
        self.assertEqual(len(entries), 2)
        second_entry = entries[1]
        self.assertEqual(second_entry.before_snapshot["policy_version_id"], str(first_version.id))
        self.assertEqual(second_entry.after_snapshot["policy_version_id"], str(second_version.id))
        self.assertNotEqual(first_version.id, second_version.id)

    def test_set_cooperation_default_writes_financial_audit_with_cooperation_type_metadata(self):
        CommissionPolicyService.set_cooperation_default(
            tenant_id=self.tenant.id,
            key=CooperationType.INDEPENDENT,
            shares={"platform": 15, "company": 0, "caregiver": 85},
            change_reason="x",
            actor=self.actor,
        )
        entry = self._entries("commission.policy.cooperation_default.set").get()
        self.assertEqual(entry.audit_class, AuditClassification.FINANCIAL)
        self.assertEqual(entry.metadata.get("cooperation_type"), CooperationType.INDEPENDENT)

    def test_set_platform_override_writes_financial_audit_with_party_metadata(self):
        import uuid

        party_id = uuid.uuid4()
        CommissionPolicyService.set_platform_override(
            tenant_id=self.tenant.id,
            key=CooperationType.INDEPENDENT,
            party_scope_type="caregiver",
            party_id=party_id,
            shares={"platform": 10, "company": 0, "caregiver": 90},
            change_reason="x",
            actor=self.actor,
        )
        entry = self._entries("commission.policy.platform_override.set").get()
        self.assertEqual(entry.audit_class, AuditClassification.FINANCIAL)
        self.assertEqual(entry.metadata.get("party_scope_type"), "caregiver")
        self.assertEqual(entry.metadata.get("party_id"), str(party_id))

    def test_denied_write_creates_no_false_success_audit(self):
        unauthorized = make_actor(self.tenant, full_name="No Permission")
        with self.assertRaises(PermissionDenied):
            CommissionPolicyService.set_global_defaults(
                tenant_id=self.tenant.id,
                payload=DEFAULT_SHARES,
                change_reason="x",
                actor=unauthorized,
            )
        self.assertEqual(self._entries("commission.policy.global_defaults.set").count(), 0)

    def test_seed_defaults_if_missing_writes_system_context_audit(self):
        CommissionPolicyService.seed_defaults_if_missing(tenant_id=self.tenant.id)
        entry = self._entries("commission.policy.global_defaults.set").get()
        self.assertEqual(entry.actor_type, "system")
        self.assertIsNone(entry.actor_id)

    def test_seed_defaults_if_missing_second_call_does_not_write_a_duplicate_audit(self):
        CommissionPolicyService.seed_defaults_if_missing(tenant_id=self.tenant.id)
        result = CommissionPolicyService.seed_defaults_if_missing(tenant_id=self.tenant.id)
        self.assertIsNone(result)
        self.assertEqual(self._entries("commission.policy.global_defaults.set").count(), 1)
