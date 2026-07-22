"""
Tests for order cancellation authorization enforcement (Sprint 5.3A).

Verifies STRICT RBAC enforcement:
- orders.cancellation.request: actor without permission → PermissionDenied
- orders.cancellation.approve: actor without permission → PermissionDenied
- actor=None (system context): audited and allowed (legitimate internal path)
- Denied operations produce no state mutation or side effects

Uses real roles and permission assignments — does not mock authorization.
"""

from django.test import TestCase

from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.rbac import Role, RoleAssignment
from apps.kernel.services.errors import PermissionDenied
from apps.orders.models import CatalogStatus, OrderStatus, ServiceCategory
from apps.orders.services.order_creation import create_operator_order
from apps.orders.services.status_machine import (
    OrderStateError,
    approve_cancellation,
    request_cancellation,
)


def _create_role_with_permissions(tenant, slug, permissions):
    """Create a Role with the given permission keys."""
    return Role.objects.create(
        tenant=tenant,
        slug=slug,
        name=slug.replace("-", " ").title(),
        permissions=permissions,
    )


def _assign_role(tenant, user, role):
    """Assign a role to a user."""
    return RoleAssignment.objects.create(
        tenant=tenant,
        user=user,
        role=role,
        is_active=True,
    )


class RequestCancellationAuthorizationTest(TestCase):
    """STRICT enforcement tests for request_cancellation()."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug="cancel-auth-req", name="Cancel Auth Req")
        self.person = Person.objects.create(tenant=self.tenant, full_name="Customer")
        self.customer = UserAccount.objects.create_user(phone="09120000030", person=self.person, tenant=self.tenant)
        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Test", slug="test-cancel-req", status=CatalogStatus.ACTIVE
        )
        self.order = create_operator_order(
            service_category_id=self.category.id,
            description="Test order for cancellation auth",
            phone="09121111111",
            address="Test address",
            city="tehran",
        )

    def test_actor_with_request_permission_can_request(self):
        """Actor with orders.cancellation.request succeeds."""
        role = _create_role_with_permissions(self.tenant, "customer-cancel-req", ["orders.cancellation.request"])
        _assign_role(self.tenant, self.customer, role)

        order = request_cancellation(order_id=self.order.id, requested_by=self.customer)
        self.assertEqual(order.status, OrderStatus.CANCELLATION_REQUESTED)
        self.assertEqual(order.cancellation_requested_by, self.customer)

    def test_actor_without_permission_receives_permission_denied(self):
        """Actor WITHOUT orders.cancellation.request receives PermissionDenied."""
        # No role assigned — strict RBAC denies
        with self.assertRaises(PermissionDenied):
            request_cancellation(order_id=self.order.id, requested_by=self.customer)

    def test_actor_with_wrong_permission_is_denied(self):
        """Actor with a different permission but NOT cancellation.request is denied."""
        role = _create_role_with_permissions(
            self.tenant,
            "other-perm",
            ["orders.cancellation.approve"],  # wrong key
        )
        _assign_role(self.tenant, self.customer, role)

        with self.assertRaises(PermissionDenied):
            request_cancellation(order_id=self.order.id, requested_by=self.customer)

    def test_cross_tenant_actor_is_denied(self):
        """Actor with permission in ANOTHER tenant cannot request on THIS order."""
        other_tenant = Tenant.objects.create(slug="other-tenant-req", name="Other Req")
        other_person = Person.objects.create(tenant=other_tenant, full_name="Other")
        other_user = UserAccount.objects.create_user(phone="09120000031", person=other_person, tenant=other_tenant)
        # Permission in other_tenant, not in self.tenant
        role = _create_role_with_permissions(other_tenant, "other-cancel", ["orders.cancellation.request"])
        _assign_role(other_tenant, other_user, role)

        with self.assertRaises(PermissionDenied):
            request_cancellation(order_id=self.order.id, requested_by=other_user)

    def test_denial_leaves_status_unchanged(self):
        """When denied, order status and timestamps remain unchanged."""
        original_status = self.order.status
        original_updated_at = self.order.updated_at

        try:
            request_cancellation(order_id=self.order.id, requested_by=self.customer)
        except PermissionDenied:
            pass

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, original_status)
        self.assertIsNone(self.order.cancellation_requested_by_id)
        self.assertEqual(self.order.cancellation_reason, "")

    def test_existing_state_machine_rules_enforced_after_permission(self):
        """State-machine validation (already-requested) remains enforced."""
        role = _create_role_with_permissions(self.tenant, "cancel-role-dup", ["orders.cancellation.request"])
        _assign_role(self.tenant, self.customer, role)

        request_cancellation(order_id=self.order.id, requested_by=self.customer)
        with self.assertRaises(OrderStateError):
            request_cancellation(order_id=self.order.id, requested_by=self.customer)

    def test_permission_key_is_registered(self):
        """The orders.cancellation.request key exists in the permission registry."""
        from apps.kernel.permissions.registry import _REGISTRY

        self.assertIn("orders.cancellation.request", _REGISTRY)


class ApproveCancellationAuthorizationTest(TestCase):
    """STRICT enforcement tests for approve_cancellation()."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug="cancel-auth-app", name="Cancel Auth App")
        self.person = Person.objects.create(tenant=self.tenant, full_name="Customer")
        self.customer = UserAccount.objects.create_user(phone="09120000040", person=self.person, tenant=self.tenant)
        self.admin_person = Person.objects.create(tenant=self.tenant, full_name="Admin")
        self.admin = UserAccount.objects.create_user(phone="09120000041", person=self.admin_person, tenant=self.tenant)
        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Test", slug="test-cancel-app", status=CatalogStatus.ACTIVE
        )
        self.order = create_operator_order(
            service_category_id=self.category.id,
            description="Test order for approval auth",
            phone="09121111111",
            address="Test address",
            city="tehran",
        )
        # Grant request permission to customer for setUp
        req_role = _create_role_with_permissions(self.tenant, "customer-req-app", ["orders.cancellation.request"])
        _assign_role(self.tenant, self.customer, req_role)

        # Put order into CANCELLATION_REQUESTED state
        request_cancellation(order_id=self.order.id, requested_by=self.customer)

    def test_actor_with_approve_permission_can_approve(self):
        """Actor with orders.cancellation.approve succeeds."""
        role = _create_role_with_permissions(self.tenant, "admin-approve", ["orders.cancellation.approve"])
        _assign_role(self.tenant, self.admin, role)

        order = approve_cancellation(order_id=self.order.id, changed_by=self.admin)
        self.assertEqual(order.status, OrderStatus.CANCELLED)

    def test_actor_without_approve_permission_is_denied(self):
        """Actor WITHOUT orders.cancellation.approve receives PermissionDenied."""
        # Customer has request permission but NOT approve
        with self.assertRaises(PermissionDenied):
            approve_cancellation(order_id=self.order.id, changed_by=self.customer)

    def test_cross_tenant_actor_is_denied(self):
        """Actor with approve permission in another tenant is denied."""
        other_tenant = Tenant.objects.create(slug="other-tenant-app", name="Other App")
        other_person = Person.objects.create(tenant=other_tenant, full_name="OtherAdmin")
        other_admin = UserAccount.objects.create_user(phone="09120000042", person=other_person, tenant=other_tenant)
        role = _create_role_with_permissions(other_tenant, "other-approve", ["orders.cancellation.approve"])
        _assign_role(other_tenant, other_admin, role)

        with self.assertRaises(PermissionDenied):
            approve_cancellation(order_id=self.order.id, changed_by=other_admin)

    def test_denial_leaves_status_unchanged(self):
        """When denied, order remains in CANCELLATION_REQUESTED."""
        try:
            approve_cancellation(order_id=self.order.id, changed_by=self.customer)
        except PermissionDenied:
            pass

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.CANCELLATION_REQUESTED)
        self.assertIsNone(self.order.cancelled_at)

    def test_system_context_approve_is_allowed(self):
        """changed_by=None (system/internal context) is deliberately allowed.

        This is the documented system-context path in PermissionService:
        actor=None, ownership_authorized_by=None → audited, allowed.
        Legitimate for background jobs and cascading internal operations.
        """
        order = approve_cancellation(order_id=self.order.id, changed_by=None)
        self.assertEqual(order.status, OrderStatus.CANCELLED)

    def test_existing_state_machine_rules_enforced_after_permission(self):
        """State-machine validation (wrong status) remains enforced."""
        role = _create_role_with_permissions(self.tenant, "admin-approve-dup", ["orders.cancellation.approve"])
        _assign_role(self.tenant, self.admin, role)

        approve_cancellation(order_id=self.order.id, changed_by=self.admin)
        # Order is now CANCELLED (final) — re-approve should fail
        with self.assertRaises(OrderStateError):
            approve_cancellation(order_id=self.order.id, changed_by=self.admin)

    def test_permission_key_is_registered(self):
        """The orders.cancellation.approve key exists in the permission registry."""
        from apps.kernel.permissions.registry import _REGISTRY

        self.assertIn("orders.cancellation.approve", _REGISTRY)
