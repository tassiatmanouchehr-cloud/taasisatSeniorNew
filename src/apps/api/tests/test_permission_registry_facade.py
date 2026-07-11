"""
apps.api.permission_keys registry-consistency check — Epic 05
(Permission-Key Registry & Authorization Hardening).

Lives here, not in apps.kernel.tests, because apps.api sits at the apex of
the dependency graph (docs/architecture/dependency-graph.md) — nothing
outside apps/api/ may import it (see NoReverseApiImportTest in
apps.kernel.tests.test_architecture_guardrails). The equivalent check for
every other app's permission_keys.py facade lives in
apps.kernel.tests.test_permission_registry_guardrails.
"""

from django.test import SimpleTestCase

from apps.api import permission_keys as api_keys
from apps.kernel.permissions.registry import PermissionRegistry


class ApiPermissionKeysRegistryConsistencyTest(SimpleTestCase):
    def test_every_api_permission_key_is_registered(self):
        for name in api_keys.__all__:
            value = getattr(api_keys, name)
            self.assertTrue(
                PermissionRegistry.exists(value),
                f"apps.api.permission_keys.{name} = {value!r} is not registered in the canonical registry",
            )
