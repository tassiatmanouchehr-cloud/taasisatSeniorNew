"""
Tests for RBACConfiguration's enforcement-toggle emergency control —
RBAC Enforcement-Toggle Visibility & Audit Remediation.

Covers: default state, effective-status reporting (default vs explicit
override), the sanctioned write path's validation (tenant, actor,
reason), audit recording for real changes and no-op (same-value)
requests, tenant isolation of the audit trail, cache-invalidation timing
(only after commit, never on rollback), and that no unrelated
configuration key is ever touched.
"""

import uuid

from django.core.cache import cache
from django.db import transaction
from django.test import TestCase

from apps.kernel.models.audit import AuditLog
from apps.kernel.models.configuration import ConfigurationKey, ConfigurationValue
from apps.kernel.services.config_resolver import ConfigResolver
from apps.kernel.services.rbac_configuration import (
    ACTION_CHANGED,
    ACTION_NO_OP,
    DEFAULT_ENFORCEMENT_ENABLED,
    ENFORCEMENT_ENABLED_KEY,
    RBACConfiguration,
    RBACConfigurationError,
)

from .rbac_helpers import make_tenant


class GetEnforcementEnabledDefaultTest(TestCase):
    def test_default_state_is_enabled(self):
        tenant = make_tenant()
        self.assertTrue(RBACConfiguration.get_enforcement_enabled(tenant_id=tenant.id))
        self.assertTrue(DEFAULT_ENFORCEMENT_ENABLED)


class GetEnforcementStatusTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()

    def test_reports_implicit_default_when_no_override_exists(self):
        status = RBACConfiguration.get_enforcement_status(tenant_id=self.tenant.id)
        self.assertTrue(status.enabled)
        self.assertEqual(status.source, "default")
        self.assertIsNone(status.last_changed_at)

    def test_reports_explicit_override_after_a_real_change(self):
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=False,
            actor_display="ops:test",
            reason="incident response",
        )
        status = RBACConfiguration.get_enforcement_status(tenant_id=self.tenant.id)
        self.assertFalse(status.enabled)
        self.assertEqual(status.source, "override")
        self.assertEqual(status.last_changed_by, "ops:test")
        self.assertEqual(status.last_change_reason, "incident response")
        self.assertIsNotNone(status.last_changed_at)


class SetEnforcementEnabledValidationTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()

    def test_missing_tenant_rejected(self):
        with self.assertRaises(RBACConfigurationError):
            RBACConfiguration.set_enforcement_enabled(
                tenant_id=None,
                enabled=False,
                actor_display="ops:test",
                reason="x",
            )

    def test_nonexistent_tenant_rejected(self):
        with self.assertRaises(RBACConfigurationError):
            RBACConfiguration.set_enforcement_enabled(
                tenant_id=uuid.uuid4(),
                enabled=False,
                actor_display="ops:test",
                reason="x",
            )

    def test_missing_actor_rejected(self):
        with self.assertRaises(RBACConfigurationError):
            RBACConfiguration.set_enforcement_enabled(
                tenant_id=self.tenant.id,
                enabled=False,
                actor_display="",
                reason="x",
            )

    def test_blank_actor_rejected(self):
        with self.assertRaises(RBACConfigurationError):
            RBACConfiguration.set_enforcement_enabled(
                tenant_id=self.tenant.id,
                enabled=False,
                actor_display="   ",
                reason="x",
            )

    def test_missing_reason_rejected(self):
        with self.assertRaises(RBACConfigurationError):
            RBACConfiguration.set_enforcement_enabled(
                tenant_id=self.tenant.id,
                enabled=False,
                actor_display="ops:test",
                reason="",
            )

    def test_blank_reason_rejected(self):
        with self.assertRaises(RBACConfigurationError):
            RBACConfiguration.set_enforcement_enabled(
                tenant_id=self.tenant.id,
                enabled=False,
                actor_display="ops:test",
                reason="   ",
            )

    def test_invalid_request_creates_no_configurationvalue_row(self):
        with self.assertRaises(RBACConfigurationError):
            RBACConfiguration.set_enforcement_enabled(
                tenant_id=self.tenant.id,
                enabled=False,
                actor_display="ops:test",
                reason="",
            )
        self.assertFalse(ConfigurationValue.objects.filter(tenant_id=self.tenant.id).exists())


class SetEnforcementEnabledChangeTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()

    def test_actual_change_persists_and_reports_new_state(self):
        status = RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=False,
            actor_display="ops:test",
            reason="incident response",
        )
        self.assertFalse(status.enabled)
        self.assertEqual(status.source, "override")
        self.assertFalse(RBACConfiguration.get_enforcement_enabled(tenant_id=self.tenant.id))

    def test_previous_and_new_values_recorded_in_audit(self):
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=False,
            actor_display="ops:test",
            reason="r1",
        )
        entry = AuditLog.objects.get(tenant_id=self.tenant.id, action=ACTION_CHANGED)
        self.assertEqual(entry.before_snapshot, {"enabled": True, "source": "default"})
        self.assertEqual(entry.after_snapshot, {"enabled": False, "source": "override"})

    def test_second_change_uses_prior_override_as_previous_value(self):
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=False,
            actor_display="ops:test",
            reason="r1",
        )
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=True,
            actor_display="ops:test",
            reason="r2",
        )
        entries = list(AuditLog.objects.filter(tenant_id=self.tenant.id, action=ACTION_CHANGED).order_by("occurred_at"))
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[1].before_snapshot, {"enabled": False, "source": "override"})
        self.assertEqual(entries[1].after_snapshot, {"enabled": True, "source": "override"})

    def test_audit_record_created_for_actual_change(self):
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=False,
            actor_display="ops:test",
            reason="r1",
        )
        self.assertTrue(AuditLog.objects.filter(tenant_id=self.tenant.id, action=ACTION_CHANGED).exists())

    def test_audit_tenant_matches_target_tenant(self):
        other_tenant = make_tenant("other")
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=False,
            actor_display="ops:test",
            reason="r1",
        )
        self.assertTrue(AuditLog.objects.filter(tenant_id=self.tenant.id, action=ACTION_CHANGED).exists())
        self.assertFalse(AuditLog.objects.filter(tenant_id=other_tenant.id, action=ACTION_CHANGED).exists())

    def test_audit_class_is_security(self):
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=False,
            actor_display="ops:test",
            reason="r1",
        )
        entry = AuditLog.objects.get(tenant_id=self.tenant.id, action=ACTION_CHANGED)
        self.assertEqual(entry.audit_class, "security")

    def test_version_increments_on_real_change(self):
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=False,
            actor_display="ops:test",
            reason="r1",
        )
        value = ConfigurationValue.objects.get(
            tenant_id=self.tenant.id,
            config_key__key=ENFORCEMENT_ENABLED_KEY,
        )
        self.assertEqual(value.version, 1)  # freshly created row

        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=True,
            actor_display="ops:test",
            reason="r2",
        )
        value.refresh_from_db()
        self.assertEqual(value.version, 2)  # updated in place

    def test_no_unrelated_configuration_key_is_modified(self):
        other_key = ConfigurationKey.objects.create(
            key="marketplace.some_other_flag",
            owner_module="M99",
            default_value=False,
        )
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=False,
            actor_display="ops:test",
            reason="r1",
        )
        self.assertFalse(ConfigurationValue.objects.filter(config_key=other_key).exists())
        self.assertEqual(
            ConfigurationKey.objects.filter(key=ENFORCEMENT_ENABLED_KEY).count(),
            1,
        )


class SetEnforcementEnabledNoOpTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()

    def test_same_value_as_implicit_default_is_a_no_op(self):
        status = RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=True,
            actor_display="ops:test",
            reason="confirm state",
        )
        self.assertTrue(status.enabled)
        self.assertEqual(status.source, "default")
        self.assertFalse(ConfigurationValue.objects.filter(tenant_id=self.tenant.id).exists())

    def test_no_op_does_not_create_a_changed_audit_event(self):
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=True,
            actor_display="ops:test",
            reason="confirm state",
        )
        self.assertFalse(AuditLog.objects.filter(tenant_id=self.tenant.id, action=ACTION_CHANGED).exists())

    def test_no_op_creates_a_distinct_no_op_audit_event(self):
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=True,
            actor_display="ops:test",
            reason="confirm state",
        )
        entry = AuditLog.objects.get(tenant_id=self.tenant.id, action=ACTION_NO_OP)
        self.assertEqual(entry.metadata.get("no_op"), True)

    def test_repeated_disable_after_override_is_also_a_no_op(self):
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=False,
            actor_display="ops:test",
            reason="r1",
        )
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=False,
            actor_display="ops:test",
            reason="r2 (repeat)",
        )
        self.assertEqual(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=ACTION_CHANGED).count(),
            1,
        )
        self.assertEqual(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=ACTION_NO_OP).count(),
            1,
        )
        value = ConfigurationValue.objects.get(
            tenant_id=self.tenant.id,
            config_key__key=ENFORCEMENT_ENABLED_KEY,
        )
        self.assertEqual(value.version, 1)  # the no-op repeat did not bump the version


class SetEnforcementEnabledCacheInvalidationTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()

    def _cache_key(self):
        return ConfigResolver._build_cache_key(ENFORCEMENT_ENABLED_KEY, self.tenant.id, {})

    def test_cache_invalidated_only_after_commit(self):
        # A ConfigurationKey must exist before ConfigResolver.get() can
        # populate the cache at all (get_or_default() silently skips
        # caching on ConfigurationKey.DoesNotExist) — create the first
        # override, which registers the key, then prime the cache with
        # that (correct, at the time) resolved value.
        with self.captureOnCommitCallbacks(execute=True):
            RBACConfiguration.set_enforcement_enabled(
                tenant_id=self.tenant.id,
                enabled=False,
                actor_display="ops:test",
                reason="initial",
            )
        self.assertFalse(RBACConfiguration.get_enforcement_enabled(tenant_id=self.tenant.id))
        self.assertIsNotNone(cache.get(self._cache_key()))

        with self.captureOnCommitCallbacks(execute=True):
            RBACConfiguration.set_enforcement_enabled(
                tenant_id=self.tenant.id,
                enabled=True,
                actor_display="ops:test",
                reason="r1",
            )

        self.assertIsNone(cache.get(self._cache_key()))
        self.assertTrue(RBACConfiguration.get_enforcement_enabled(tenant_id=self.tenant.id))

    def test_rollback_does_not_invalidate_cache_for_an_uncommitted_change(self):
        self.assertTrue(RBACConfiguration.get_enforcement_enabled(tenant_id=self.tenant.id))
        cache.set(self._cache_key(), True, timeout=300)

        class _Rollback(Exception):
            pass

        with self.assertRaises(_Rollback), transaction.atomic():
            RBACConfiguration.set_enforcement_enabled(
                tenant_id=self.tenant.id,
                enabled=False,
                actor_display="ops:test",
                reason="r1",
            )
            raise _Rollback

        # The write was rolled back, so on_commit never fired: the primed
        # cache entry must be exactly what it was before — never wrongly
        # invalidated for a change that never actually committed.
        self.assertEqual(cache.get(self._cache_key()), True)
        self.assertFalse(ConfigurationValue.objects.filter(tenant_id=self.tenant.id).exists())


class SetEnforcementEnabledSequentialWritesTest(TestCase):
    """Models the concurrency-safety contract (select_for_update-guarded
    read-modify-write): two writes in sequence must never lose an update
    or corrupt the before/after chain, which is exactly what an
    unguarded race would break."""

    def setUp(self):
        self.tenant = make_tenant()

    def test_sequential_writes_do_not_lose_updates(self):
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=False,
            actor_display="ops:a",
            reason="r1",
        )
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=True,
            actor_display="ops:b",
            reason="r2",
        )
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=False,
            actor_display="ops:c",
            reason="r3",
        )

        self.assertFalse(RBACConfiguration.get_enforcement_enabled(tenant_id=self.tenant.id))
        value = ConfigurationValue.objects.get(
            tenant_id=self.tenant.id,
            config_key__key=ENFORCEMENT_ENABLED_KEY,
        )
        self.assertEqual(value.version, 3)
        self.assertEqual(
            AuditLog.objects.filter(tenant_id=self.tenant.id, action=ACTION_CHANGED).count(),
            3,
        )
