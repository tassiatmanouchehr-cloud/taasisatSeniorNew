import uuid

from apps.commission.models.snapshot import PolicySource
from apps.commission.services.cooperation_type import CooperationType
from apps.commission.services.errors import InvalidPolicyError
from apps.commission.services.policy_service import DEFAULT_SHARES, CommissionPolicyService
from apps.commission.services.resolver_service import CommissionRuleResolver

from .helpers import CommissionTestCase


class DefaultPolicyTest(CommissionTestCase):
    def test_seed_defaults_if_missing_creates_active_global_policy(self):
        version = CommissionPolicyService.seed_defaults_if_missing(tenant_id=self.tenant.id)
        self.assertIsNotNone(version)
        self.assertEqual(version.rule_payload, DEFAULT_SHARES)

    def test_seed_defaults_if_missing_is_idempotent(self):
        first = CommissionPolicyService.seed_defaults_if_missing(tenant_id=self.tenant.id)
        second = CommissionPolicyService.seed_defaults_if_missing(tenant_id=self.tenant.id)
        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_default_independent_20_80(self):
        rule = CommissionRuleResolver.resolve_service_rule(
            tenant_id=self.tenant.id,
            cooperation_type=CooperationType.INDEPENDENT,
        )
        self.assertEqual(rule.platform_rate_percent, 20)
        self.assertEqual(rule.caregiver_rate_percent, 80)
        self.assertEqual(rule.policy_source, PolicySource.GLOBAL_DEFAULT)

    def test_default_affiliated_7_13_80(self):
        rule = CommissionRuleResolver.resolve_service_rule(
            tenant_id=self.tenant.id,
            cooperation_type=CooperationType.AFFILIATED,
        )
        self.assertEqual(rule.platform_rate_percent, 7)
        self.assertEqual(rule.company_rate_percent, 13)
        self.assertEqual(rule.caregiver_rate_percent, 80)

    def test_default_company_direct_7_93(self):
        rule = CommissionRuleResolver.resolve_service_rule(
            tenant_id=self.tenant.id,
            cooperation_type=CooperationType.COMPANY_DIRECT,
        )
        self.assertEqual(rule.platform_rate_percent, 7)
        self.assertEqual(rule.company_rate_percent, 93)
        self.assertEqual(rule.caregiver_rate_percent, 0)

    def test_default_goods_0_0_100(self):
        rule = CommissionRuleResolver.resolve_goods_rule(tenant_id=self.tenant.id)
        self.assertEqual(rule.platform_rate_percent, 0)
        self.assertEqual(rule.company_rate_percent, 0)
        self.assertEqual(rule.caregiver_rate_percent, 100)

    def test_resolves_deterministically_even_when_unseeded(self):
        """A tenant with zero PolicyVersions ever created still resolves to
        the documented final defaults, per resolver_service's hard-fallback."""
        unseeded_tenant_id = uuid.uuid4()
        rule = CommissionRuleResolver.resolve_service_rule(
            tenant_id=unseeded_tenant_id,
            cooperation_type=CooperationType.INDEPENDENT,
        )
        self.assertEqual(rule.platform_rate_percent, 20)
        self.assertIsNone(rule.policy_version_id)


class InvalidPolicyRejectionTest(CommissionTestCase):
    def test_shares_not_summing_to_100_rejected(self):
        with self.assertRaises(InvalidPolicyError):
            CommissionPolicyService.set_cooperation_default(
                tenant_id=self.tenant.id,
                key=CooperationType.INDEPENDENT,
                shares={"platform": 50, "company": 0, "caregiver": 40},
                change_reason="test",
            )

    def test_negative_share_rejected(self):
        with self.assertRaises(InvalidPolicyError):
            CommissionPolicyService.set_cooperation_default(
                tenant_id=self.tenant.id,
                key=CooperationType.INDEPENDENT,
                shares={"platform": -10, "company": 0, "caregiver": 110},
                change_reason="test",
            )

    def test_missing_key_rejected(self):
        with self.assertRaises(InvalidPolicyError):
            CommissionPolicyService.set_cooperation_default(
                tenant_id=self.tenant.id,
                key=CooperationType.INDEPENDENT,
                shares={"platform": 20, "caregiver": 80},
                change_reason="test",
            )

    def test_incomplete_global_payload_rejected(self):
        with self.assertRaises(InvalidPolicyError):
            CommissionPolicyService.set_global_defaults(
                tenant_id=self.tenant.id,
                payload={CooperationType.INDEPENDENT: {"platform": 20, "company": 0, "caregiver": 80}},
                change_reason="test",
            )


class PriorityChainTest(CommissionTestCase):
    """Business Model Section 9: contract > platform override > cooperation default > global default."""

    def setUp(self):
        super().setUp()
        CommissionPolicyService.seed_defaults_if_missing(tenant_id=self.tenant.id)

    def test_cooperation_default_overrides_global_default(self):
        CommissionPolicyService.set_cooperation_default(
            tenant_id=self.tenant.id,
            key=CooperationType.INDEPENDENT,
            shares={"platform": 25, "company": 0, "caregiver": 75},
            change_reason="test override",
            auto_activate=True,
        )
        rule = CommissionRuleResolver.resolve_service_rule(
            tenant_id=self.tenant.id,
            cooperation_type=CooperationType.INDEPENDENT,
        )
        self.assertEqual(rule.platform_rate_percent, 25)
        self.assertEqual(rule.policy_source, PolicySource.COOPERATION_DEFAULT)

    def test_platform_override_for_caregiver_overrides_cooperation_default(self):
        CommissionPolicyService.set_cooperation_default(
            tenant_id=self.tenant.id,
            key=CooperationType.INDEPENDENT,
            shares={"platform": 25, "company": 0, "caregiver": 75},
            change_reason="test",
            auto_activate=True,
        )
        caregiver_party_id = uuid.uuid4()
        CommissionPolicyService.set_platform_override(
            tenant_id=self.tenant.id,
            key=CooperationType.INDEPENDENT,
            party_scope_type="caregiver",
            party_id=caregiver_party_id,
            shares={"platform": 15, "company": 0, "caregiver": 85},
            change_reason="VIP caregiver rate",
            auto_activate=True,
        )
        rule = CommissionRuleResolver.resolve_service_rule(
            tenant_id=self.tenant.id,
            cooperation_type=CooperationType.INDEPENDENT,
            caregiver_party_id=caregiver_party_id,
        )
        self.assertEqual(rule.platform_rate_percent, 15)
        self.assertEqual(rule.policy_source, PolicySource.PLATFORM_OVERRIDE)

        # A different caregiver, no override, still gets the cooperation default.
        other_rule = CommissionRuleResolver.resolve_service_rule(
            tenant_id=self.tenant.id,
            cooperation_type=CooperationType.INDEPENDENT,
            caregiver_party_id=uuid.uuid4(),
        )
        self.assertEqual(other_rule.platform_rate_percent, 25)

    def test_later_global_config_change_does_not_affect_a_resolved_snapshot(self):
        """Business Model Section 11: 'No later configuration change may
        affect the accepted order.' Proven end-to-end via a real
        CommissionSnapshot, not just the resolver in isolation."""
        from apps.commission.services.snapshot_service import CommissionSnapshotService

        order = self._make_order()
        supplier = self._make_independent_supplier()
        snapshot = CommissionSnapshotService.create_snapshot_for_order(order=order, supplier=supplier)
        self.assertEqual(snapshot.platform_rate_percent, 20)

        CommissionPolicyService.set_global_defaults(
            tenant_id=self.tenant.id,
            payload={**DEFAULT_SHARES, CooperationType.INDEPENDENT: {"platform": 50, "company": 0, "caregiver": 50}},
            change_reason="platform changed its mind",
            auto_activate=True,
        )

        snapshot.refresh_from_db()
        self.assertEqual(snapshot.platform_rate_percent, 20)

        new_rule = CommissionRuleResolver.resolve_service_rule(
            tenant_id=self.tenant.id,
            cooperation_type=CooperationType.INDEPENDENT,
        )
        self.assertEqual(new_rule.platform_rate_percent, 50)
