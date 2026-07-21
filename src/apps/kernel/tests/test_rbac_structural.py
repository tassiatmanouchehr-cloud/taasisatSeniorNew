"""
Structural guarantees for Module 08 RBAC Enforcement:

- Business modules (finance/booking/execution) never hardcode a role slug.
- Business modules call PermissionService.require(...) — they never query
  RoleAssignment (or Role.permissions) directly.
- PermissionService is the only service-layer code that evaluates
  RoleAssignment/Role.permissions for an authorization decision.
"""

import inspect

from django.test import TestCase

from apps.booking.services import assignment_service
from apps.execution.services import session_service
from apps.finance.services import document_service, ledger_service, payment_service, settlement_service
from apps.kernel.services import permission_service

# Platform role slugs seeded by apps.kernel.management.commands.seed_tenant —
# business modules must never reference these directly.
_KNOWN_ROLE_SLUGS = (
    "platform-owner",
    "platform-team",
    "organization-owner",
    "organization-staff",
    "organization-operator",
    "independent-provider",
    "organization-provider",
    "customer",
    "customer-delegate",
    "trusted-person",
    "support-user",
    "finance-user",
    "compliance-user",
    "read-only-auditor",
)

_GATED_BUSINESS_MODULES = (
    document_service,
    payment_service,
    ledger_service,
    settlement_service,
    assignment_service,
    session_service,
)


class RBACStructuralTest(TestCase):
    def test_business_modules_never_hardcode_role_slugs(self):
        for module in _GATED_BUSINESS_MODULES:
            source = inspect.getsource(module)
            for slug in _KNOWN_ROLE_SLUGS:
                self.assertNotIn(
                    f'"{slug}"',
                    source,
                    f"{module.__name__} must not hardcode role slug '{slug}'",
                )
                self.assertNotIn(
                    f"'{slug}'",
                    source,
                    f"{module.__name__} must not hardcode role slug '{slug}'",
                )

    def test_business_modules_never_query_roleassignment_directly(self):
        for module in _GATED_BUSINESS_MODULES:
            source = inspect.getsource(module)
            self.assertNotIn("RoleAssignment", source, f"{module.__name__} must not query RoleAssignment directly")
            self.assertNotIn(
                ".permissions",
                source,
                f"{module.__name__} must not inspect Role.permissions directly",
            )

    def test_business_modules_call_permission_service(self):
        for module in _GATED_BUSINESS_MODULES:
            source = inspect.getsource(module)
            self.assertIn(
                "PermissionService.require(",
                source,
                f"{module.__name__} must gate its high-risk action via PermissionService.require(...)",
            )

    def test_permission_service_is_the_sole_rbac_evaluator(self):
        """No other kernel service module evaluates RoleAssignment/Role.permissions."""
        from apps.kernel import services as kernel_services

        for name in kernel_services.__all__:
            obj = getattr(kernel_services, name)
            module = inspect.getmodule(obj)
            if module is permission_service:
                continue
            if module is None:
                continue
            source = inspect.getsource(module)
            self.assertNotIn(
                "RoleAssignment.objects",
                source,
                f"{module.__name__} must not evaluate RoleAssignment directly — only PermissionService may.",
            )
