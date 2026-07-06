"""
Tests for Feature Flag model and FeatureFlagService.

Covers:
- Boolean flag evaluation
- Percentage-based evaluation (deterministic)
- Kill switch overrides everything
- Actor allowlist/blocklist
- Non-existent flag returns False (safe default)
- Flag status must be 'enabled' to return True
"""

import uuid

from django.test import TestCase

from apps.kernel.models.feature_flag import FeatureFlag, FlagStatus, FlagType
from apps.kernel.services.feature_flag_service import FeatureFlagService


class FeatureFlagModelTest(TestCase):
    """Test FeatureFlag model."""

    def setUp(self):
        self.tenant_id = uuid.uuid4()

    def test_create_boolean_flag(self):
        flag = FeatureFlag.objects.create(
            tenant_id=self.tenant_id,
            key="feature.test",
            name="Test Feature",
            flag_type=FlagType.BOOLEAN,
            status=FlagStatus.ENABLED,
            is_enabled=True,
        )
        self.assertEqual(flag.key, "feature.test")
        self.assertTrue(flag.is_enabled)

    def test_unique_per_tenant(self):
        FeatureFlag.objects.create(
            tenant_id=self.tenant_id,
            key="feature.unique",
            name="First",
            flag_type=FlagType.BOOLEAN,
        )
        with self.assertRaises(Exception):
            FeatureFlag.objects.create(
                tenant_id=self.tenant_id,
                key="feature.unique",
                name="Duplicate",
                flag_type=FlagType.BOOLEAN,
            )

    def test_version_increments_on_save(self):
        flag = FeatureFlag.objects.create(
            tenant_id=self.tenant_id,
            key="feature.version",
            name="Version Test",
        )
        self.assertEqual(flag.version, 1)
        flag.name = "Updated"
        flag.save()
        self.assertEqual(flag.version, 2)


class FeatureFlagServiceTest(TestCase):
    """Test FeatureFlagService evaluation logic."""

    def setUp(self):
        self.tenant_id = uuid.uuid4()

    def test_nonexistent_flag_returns_false(self):
        result = FeatureFlagService.is_enabled(
            "nonexistent.flag", tenant_id=self.tenant_id, use_cache=False
        )
        self.assertFalse(result)

    def test_boolean_flag_enabled(self):
        FeatureFlag.objects.create(
            tenant_id=self.tenant_id,
            key="feature.active",
            name="Active Feature",
            flag_type=FlagType.BOOLEAN,
            status=FlagStatus.ENABLED,
            is_enabled=True,
        )
        result = FeatureFlagService.is_enabled(
            "feature.active", tenant_id=self.tenant_id, use_cache=False
        )
        self.assertTrue(result)

    def test_boolean_flag_disabled_status(self):
        FeatureFlag.objects.create(
            tenant_id=self.tenant_id,
            key="feature.draft",
            name="Draft Feature",
            flag_type=FlagType.BOOLEAN,
            status=FlagStatus.DRAFT,
            is_enabled=True,  # is_enabled True but status not 'enabled'
        )
        result = FeatureFlagService.is_enabled(
            "feature.draft", tenant_id=self.tenant_id, use_cache=False
        )
        self.assertFalse(result)

    def test_kill_switch_overrides(self):
        FeatureFlag.objects.create(
            tenant_id=self.tenant_id,
            key="feature.killed",
            name="Killed Feature",
            flag_type=FlagType.BOOLEAN,
            status=FlagStatus.ENABLED,
            is_enabled=True,
            kill_switch=True,
        )
        result = FeatureFlagService.is_enabled(
            "feature.killed", tenant_id=self.tenant_id, use_cache=False
        )
        self.assertFalse(result)

    def test_percentage_flag_deterministic(self):
        actor_id = uuid.uuid4()
        FeatureFlag.objects.create(
            tenant_id=self.tenant_id,
            key="feature.rollout",
            name="Rollout",
            flag_type=FlagType.PERCENTAGE,
            status=FlagStatus.ENABLED,
            percentage=50,
        )
        # Same actor + key always produces same result
        r1 = FeatureFlagService.is_enabled(
            "feature.rollout", tenant_id=self.tenant_id, actor_id=actor_id, use_cache=False
        )
        r2 = FeatureFlagService.is_enabled(
            "feature.rollout", tenant_id=self.tenant_id, actor_id=actor_id, use_cache=False
        )
        self.assertEqual(r1, r2)

    def test_actor_blocklist(self):
        blocked_actor = uuid.uuid4()
        FeatureFlag.objects.create(
            tenant_id=self.tenant_id,
            key="feature.blocked",
            name="Blocked Test",
            flag_type=FlagType.BOOLEAN,
            status=FlagStatus.ENABLED,
            is_enabled=True,
            actor_blocklist=[str(blocked_actor)],
        )
        result = FeatureFlagService.is_enabled(
            "feature.blocked", tenant_id=self.tenant_id,
            actor_id=blocked_actor, use_cache=False
        )
        self.assertFalse(result)

    def test_actor_allowlist(self):
        allowed_actor = uuid.uuid4()
        FeatureFlag.objects.create(
            tenant_id=self.tenant_id,
            key="feature.allowed",
            name="Allowlist Test",
            flag_type=FlagType.PERCENTAGE,
            status=FlagStatus.ENABLED,
            percentage=0,  # Would normally be off
            actor_allowlist=[str(allowed_actor)],
        )
        result = FeatureFlagService.is_enabled(
            "feature.allowed", tenant_id=self.tenant_id,
            actor_id=allowed_actor, use_cache=False
        )
        self.assertTrue(result)
