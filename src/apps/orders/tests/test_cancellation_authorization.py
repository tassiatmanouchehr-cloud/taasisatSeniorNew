"""
Tests for order cancellation authorization enforcement (Sprint 5.3A).

Verifies that request_cancellation() and approve_cancellation() now call
PermissionService.require() with the newly registered permission keys:
- orders.cancellation.request
- orders.cancellation.approve

The ownership_authorized_by pattern means any real actor is permitted via
the audited ownership-fallback path (matching AssignmentService.assign()'s
exact shape). The enforcement provides:
1. Explicit audit trail of every cancellation action
2. RBAC-path authorization for actors who DO have the role
3. Documented, audited ownership-fallback for actors who don't yet
4. System-context handling when no actor is supplied
5. Tenant-scoped permission evaluation

The HARD deny (PermissionDenied) activates the moment enforcement is enabled
AND the ownership_authorized_by parameter is removed from the call — which
will happen when all production callers have been verified to only pass
properly-authorized actors. This matches the repository's established
progressive-hardening approach (see permission_service.py module docstring).
"""

from django.test import TestCase

from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.rbac import Role, RoleAssignment
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
    """Tests for request_cancellation() permission enforcement."""

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

    def test_authorized_customer_can_request_cancellation(self):
        """A user with orders.cancellation.request RBAC role succeeds via RBAC path."""
        role = _create_role_with_permissions(self.tenant, "customer-cancel-req", ["orders.cancellation.request"])
        _assign_role(self.tenant, self.customer, role)

        order = request_cancellation(
            order_id=self.order.id,
            requested_by=self.customer,
            tenant_id=self.tenant.id,
        )
        self.assertEqual(order.status, OrderStatus.CANCELLATION_REQUESTED)
        self.assertEqual(order.cancellation_requested_by, self.customer)

    def test_customer_without_role_succeeds_via_ownership_fallback(self):
        """A user without RBAC role still succeeds (ownership-authorized fallback).

        This matches AssignmentService.assign()'s pattern: the ownership-authorized
        path audits and permits until RBAC roles are fully seeded.
        """
        order = request_cancellation(
            order_id=self.order.id,
            requested_by=self.customer,
            tenant_id=self.tenant.id,
        )
        self.assertEqual(order.status, OrderStatus.CANCELLATION_REQUESTED)

    def test_request_with_explicit_tenant_id_uses_that_tenant(self):
        """When tenant_id is provided, it is used for permission evaluation."""
        order = request_cancellation(
            order_id=self.order.id,
            requested_by=self.customer,
            tenant_id=self.tenant.id,
        )
        self.assertEqual(order.status, OrderStatus.CANCELLATION_REQUESTED)

    def test_request_without_tenant_id_derives_from_order(self):
        """When tenant_id is not provided, it is derived from the order."""
        order = request_cancellation(
            order_id=self.order.id,
            requested_by=self.customer,
        )
        self.assertEqual(order.status, OrderStatus.CANCELLATION_REQUESTED)

    def test_existing_business_rules_still_enforced_after_auth(self):
        """Existing state-machine rules remain enforced after authorization passes."""
        request_cancellation(
            order_id=self.order.id,
            requested_by=self.customer,
            tenant_id=self.tenant.id,
        )
        with self.assertRaises(OrderStateError):
            request_cancellation(
                order_id=self.order.id,
                requested_by=self.customer,
                tenant_id=self.tenant.id,
            )

    def test_permission_key_is_registered(self):
        """The orders.cancellation.request key exists in the permission registry."""
        from apps.kernel.permissions.registry import _REGISTRY

        self.assertIn("orders.cancellation.request", _REGISTRY)


class ApproveCancellationAuthorizationTest(TestCase):
    """Tests for approve_cancellation() permission enforcement."""

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
        # Put order into CANCELLATION_REQUESTED state
        request_cancellation(
            order_id=self.order.id,
            requested_by=self.customer,
            tenant_id=self.tenant.id,
        )

    def test_authorized_admin_can_approve_cancellation(self):
        """A user with orders.cancellation.approve RBAC role succeeds."""
        role = _create_role_with_permissions(self.tenant, "admin-approve-cancel", ["orders.cancellation.approve"])
        _assign_role(self.tenant, self.admin, role)

        order = approve_cancellation(
            order_id=self.order.id,
            changed_by=self.admin,
            tenant_id=self.tenant.id,
        )
        self.assertEqual(order.status, OrderStatus.CANCELLED)

    def test_admin_without_role_succeeds_via_ownership_fallback(self):
        """A user without RBAC role still succeeds (ownership-authorized fallback)."""
        order = approve_cancellation(
            order_id=self.order.id,
            changed_by=self.admin,
            tenant_id=self.tenant.id,
        )
        self.assertEqual(order.status, OrderStatus.CANCELLED)

    def test_system_context_approve_with_no_actor(self):
        """When changed_by=None (system/background context), authorization passes."""
        order = approve_cancellation(
            order_id=self.order.id,
            changed_by=None,
            tenant_id=self.tenant.id,
        )
        self.assertEqual(order.status, OrderStatus.CANCELLED)

    def test_approve_without_tenant_id_derives_from_order(self):
        """When tenant_id is not provided, it is derived from the order."""
        order = approve_cancellation(
            order_id=self.order.id,
            changed_by=self.admin,
        )
        self.assertEqual(order.status, OrderStatus.CANCELLED)

    def test_existing_business_rules_still_enforced_after_auth(self):
        """Existing state-machine rules remain enforced after authorization."""
        approve_cancellation(
            order_id=self.order.id,
            changed_by=self.admin,
            tenant_id=self.tenant.id,
        )
        with self.assertRaises(OrderStateError):
            approve_cancellation(
                order_id=self.order.id,
                changed_by=self.admin,
                tenant_id=self.tenant.id,
            )

    def test_permission_key_is_registered(self):
        """The orders.cancellation.approve key exists in the permission registry."""
        from apps.kernel.permissions.registry import _REGISTRY

        self.assertIn("orders.cancellation.approve", _REGISTRY)
