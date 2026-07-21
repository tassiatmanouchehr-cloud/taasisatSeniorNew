"""
Tests for the `set_rbac_enforcement` management command — the only
supported write path for the rbac.enforcement.enabled emergency control
(RBAC Enforcement-Toggle Visibility & Audit Remediation).
"""

import uuid
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.kernel.models.audit import AuditLog
from apps.kernel.models.configuration import ConfigurationValue
from apps.kernel.services.rbac_configuration import RBACConfiguration

from .rbac_helpers import make_tenant


def _run(**options):
    out = StringIO()
    call_command("set_rbac_enforcement", stdout=out, **options)
    return out.getvalue()


class SetRbacEnforcementEnableTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()

    def test_enable_succeeds_with_all_required_arguments(self):
        output = _run(tenant=str(self.tenant.id), enabled="true", reason="restore after incident", actor="ops:jane")
        self.assertIn("ENABLED", output)
        self.assertTrue(RBACConfiguration.get_enforcement_enabled(tenant_id=self.tenant.id))

    def test_resolves_tenant_by_slug(self):
        output = _run(tenant=self.tenant.slug, enabled="true", reason="confirm", actor="ops:jane")
        self.assertIn("ENABLED", output)

    def test_accepts_common_boolean_spellings(self):
        for spelling in ("true", "TRUE", "1", "yes"):
            with self.subTest(spelling=spelling):
                RBACConfiguration.set_enforcement_enabled(
                    tenant_id=self.tenant.id,
                    enabled=False,
                    actor_display="setup",
                    reason="setup",
                )
                _run(tenant=str(self.tenant.id), enabled=spelling, reason="r", actor="ops:jane")
                self.assertTrue(RBACConfiguration.get_enforcement_enabled(tenant_id=self.tenant.id))


class SetRbacEnforcementDisableConfirmationTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()

    def test_disable_succeeds_only_with_explicit_confirmation(self):
        output = _run(
            tenant=str(self.tenant.id),
            enabled="false",
            reason="emergency bypass, approved",
            actor="ops:jane",
            confirm_disable=True,
        )
        self.assertIn("DISABLED", output)
        self.assertIn("WARNING", output)
        self.assertFalse(RBACConfiguration.get_enforcement_enabled(tenant_id=self.tenant.id))

    def test_disable_without_confirmation_fails(self):
        with self.assertRaises(CommandError):
            _run(tenant=str(self.tenant.id), enabled="false", reason="emergency bypass", actor="ops:jane")
        self.assertTrue(RBACConfiguration.get_enforcement_enabled(tenant_id=self.tenant.id))
        self.assertFalse(ConfigurationValue.objects.filter(tenant_id=self.tenant.id).exists())


class SetRbacEnforcementValidationTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()

    def test_missing_actor_fails(self):
        with self.assertRaises(CommandError):
            _run(tenant=str(self.tenant.id), enabled="true", reason="r", actor="")

    def test_missing_reason_fails(self):
        with self.assertRaises(CommandError):
            _run(tenant=str(self.tenant.id), enabled="true", reason="", actor="ops:jane")

    def test_invalid_tenant_uuid_fails(self):
        with self.assertRaises(CommandError):
            _run(tenant=str(uuid.uuid4()), enabled="true", reason="r", actor="ops:jane")

    def test_invalid_tenant_slug_fails(self):
        with self.assertRaises(CommandError):
            _run(tenant="no-such-tenant-slug", enabled="true", reason="r", actor="ops:jane")

    def test_malformed_boolean_fails(self):
        with self.assertRaises(CommandError):
            _run(tenant=str(self.tenant.id), enabled="maybe", reason="r", actor="ops:jane")

    def test_missing_tenant_argument_fails(self):
        with self.assertRaises(CommandError):
            _run(tenant="", enabled="true", reason="r", actor="ops:jane")


class SetRbacEnforcementDelegationTest(TestCase):
    """The command must not touch models directly — it only validates CLI
    input, then delegates the entire write to RBACConfiguration."""

    def setUp(self):
        self.tenant = make_tenant()

    def test_command_delegates_to_service_layer(self):
        with patch(
            "apps.kernel.management.commands.set_rbac_enforcement.RBACConfiguration.set_enforcement_enabled",
        ) as mock_set:
            mock_set.return_value = RBACConfiguration.get_enforcement_status(tenant_id=self.tenant.id)
            _run(tenant=str(self.tenant.id), enabled="true", reason="r", actor="ops:jane")

        mock_set.assert_called_once_with(
            tenant_id=self.tenant.id,
            enabled=True,
            actor_display="ops:jane",
            reason="r",
            correlation_id=None,
            source="management_command",
            operation="set_rbac_enforcement",
        )

    def test_command_does_not_mutate_models_directly(self):
        with patch(
            "apps.kernel.management.commands.set_rbac_enforcement.RBACConfiguration.set_enforcement_enabled",
        ) as mock_set:
            mock_set.return_value = RBACConfiguration.get_enforcement_status(tenant_id=self.tenant.id)
            _run(tenant=str(self.tenant.id), enabled="true", reason="r", actor="ops:jane")

        # With the service mocked out, nothing else in the command wrote a
        # ConfigurationValue or AuditLog row.
        self.assertFalse(ConfigurationValue.objects.filter(tenant_id=self.tenant.id).exists())
        self.assertFalse(AuditLog.objects.filter(tenant_id=self.tenant.id).exists())

    def test_source_argument_is_forwarded(self):
        with patch(
            "apps.kernel.management.commands.set_rbac_enforcement.RBACConfiguration.set_enforcement_enabled",
        ) as mock_set:
            mock_set.return_value = RBACConfiguration.get_enforcement_status(tenant_id=self.tenant.id)
            _run(tenant=str(self.tenant.id), enabled="true", reason="r", actor="ops:jane", source="incident-runbook")

        self.assertEqual(mock_set.call_args.kwargs["source"], "incident-runbook")


class SetRbacEnforcementOutputTest(TestCase):
    def setUp(self):
        self.tenant = make_tenant()

    def test_output_does_not_leak_unrelated_configuration_data(self):
        RBACConfiguration.set_enforcement_enabled(
            tenant_id=self.tenant.id,
            enabled=False,
            actor_display="setup",
            reason="unrelated secret setup reason - do not print",
        )
        output = _run(
            tenant=str(self.tenant.id),
            enabled="true",
            reason="restore",
            actor="ops:jane",
        )
        self.assertNotIn("unrelated secret setup reason", output)
        self.assertIn(str(self.tenant.slug), output)

    def test_exit_status_is_correct_for_invalid_input(self):
        # call_command surfaces CommandError directly; Django's CLI entry
        # point (execute_from_command_line) is what turns this into a
        # non-zero process exit code — asserting the exception here is the
        # in-process equivalent of asserting "exit status != 0".
        with self.assertRaises(CommandError):
            _run(tenant=str(self.tenant.id), enabled="not-a-bool", reason="r", actor="ops:jane")

    def test_no_exception_and_valid_output_for_correct_input(self):
        output = _run(tenant=str(self.tenant.id), enabled="true", reason="r", actor="ops:jane")
        self.assertIn("ENABLED", output)
