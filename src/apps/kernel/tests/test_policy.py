"""
Tests for Policy Versioning models and PolicyService.

Covers:
- Policy creation with first version
- Version activation supersedes previous
- Only one active version at a time
- Immutability of active versions
- get_active_version resolution
- Policy deprecation
"""

import uuid

from django.test import TestCase

from apps.kernel.models.policy import (
    PolicyStatus,
    PolicyVersionStatus,
)
from apps.kernel.services.policy_service import PolicyService


class PolicyServiceTest(TestCase):
    """Test PolicyService."""

    def setUp(self):
        self.tenant_id = uuid.uuid4()

    def test_create_policy_draft(self):
        version = PolicyService.create_policy(
            tenant_id=self.tenant_id,
            policy_type="commission",
            name="Platform Commission v1",
            owner_module="M05",
            rule_payload={"rate": 0.15},
            change_reason="Initial commission policy",
        )
        self.assertEqual(version.version_number, 1)
        self.assertEqual(version.status, PolicyVersionStatus.DRAFT)
        self.assertEqual(version.rule_payload, {"rate": 0.15})

        policy = version.policy
        self.assertEqual(policy.policy_type, "commission")
        self.assertEqual(policy.status, PolicyStatus.DRAFT)

    def test_create_policy_auto_activate(self):
        version = PolicyService.create_policy(
            tenant_id=self.tenant_id,
            policy_type="matching",
            name="Matching Policy",
            owner_module="M02",
            rule_payload={"max_candidates": 10},
            auto_activate=True,
        )
        self.assertEqual(version.status, PolicyVersionStatus.ACTIVE)
        self.assertEqual(version.policy.status, PolicyStatus.ACTIVE)
        self.assertIsNotNone(version.approved_at)

    def test_activate_version_supersedes_previous(self):
        # Create first version (auto-activated)
        v1 = PolicyService.create_policy(
            tenant_id=self.tenant_id,
            policy_type="pricing",
            name="Pricing Policy",
            owner_module="M05",
            rule_payload={"base_rate": 100},
            auto_activate=True,
        )
        self.assertEqual(v1.status, PolicyVersionStatus.ACTIVE)

        # Create second version (draft)
        v2 = PolicyService.create_policy(
            tenant_id=self.tenant_id,
            policy_type="pricing",
            name="Pricing Policy",
            owner_module="M05",
            rule_payload={"base_rate": 120},
        )
        self.assertEqual(v2.status, PolicyVersionStatus.DRAFT)

        # Activate v2
        v2 = PolicyService.activate_version(v2.id)
        self.assertEqual(v2.status, PolicyVersionStatus.ACTIVE)

        # v1 should now be superseded
        v1.refresh_from_db()
        self.assertEqual(v1.status, PolicyVersionStatus.SUPERSEDED)
        self.assertEqual(v1.superseded_by, v2.id)

    def test_get_active_version(self):
        PolicyService.create_policy(
            tenant_id=self.tenant_id,
            policy_type="cancellation",
            name="Cancellation Policy",
            owner_module="M03",
            rule_payload={"grace_period_minutes": 30},
            auto_activate=True,
        )
        version = PolicyService.get_active_version(
            tenant_id=self.tenant_id,
            policy_type="cancellation",
        )
        self.assertIsNotNone(version)
        self.assertEqual(version.rule_payload["grace_period_minutes"], 30)

    def test_get_active_version_none_when_no_active(self):
        PolicyService.create_policy(
            tenant_id=self.tenant_id,
            policy_type="draft_only",
            name="Draft Only",
            owner_module="M99",
            rule_payload={},
            # NOT auto_activate
        )
        version = PolicyService.get_active_version(
            tenant_id=self.tenant_id,
            policy_type="draft_only",
        )
        self.assertIsNone(version)

    def test_deprecate_policy(self):
        v = PolicyService.create_policy(
            tenant_id=self.tenant_id,
            policy_type="old_policy",
            name="Old Policy",
            owner_module="M99",
            rule_payload={},
            auto_activate=True,
        )
        policy = PolicyService.deprecate_policy(v.policy.id)
        self.assertEqual(policy.status, PolicyStatus.DEPRECATED)

    def test_cannot_activate_already_active(self):
        v = PolicyService.create_policy(
            tenant_id=self.tenant_id,
            policy_type="test",
            name="Test",
            owner_module="M99",
            rule_payload={},
            auto_activate=True,
        )
        with self.assertRaises(ValueError):
            PolicyService.activate_version(v.id)

    def test_rule_payload_immutable_after_activation(self):
        """Verify that rule_payload cannot be changed on an active version."""
        v = PolicyService.create_policy(
            tenant_id=self.tenant_id,
            policy_type="immutable_test",
            name="Immutable Test",
            owner_module="M99",
            rule_payload={"original": True},
            auto_activate=True,
        )
        self.assertEqual(v.status, PolicyVersionStatus.ACTIVE)

        # Attempt to modify rule_payload on active version
        v.rule_payload = {"modified": True}
        with self.assertRaises(ValueError) as ctx:
            v.save(update_fields=["rule_payload"])
        self.assertIn("rule_payload", str(ctx.exception))
