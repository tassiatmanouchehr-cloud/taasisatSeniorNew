"""Tests for service catalog and order foundation (25 cases)."""

from django.test import TestCase

from apps.accounts.models import CaregiverProfile
from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_caregiver
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.rbac import Role, RoleAssignment
from apps.orders.models import (
    CatalogStatus,
    OrderSource,
    OrderStatus,
    OrderStatusHistory,
    ServiceCategory,
    ServiceType,
)
from apps.orders.services.order_creation import (
    OrderValidationError,
    create_operator_order,
    create_public_order,
)
from apps.orders.services.status_machine import (
    OrderStateError,
    approve_cancellation,
    approve_public_order,
    assign_supplier,
    complete_order,
    remove_supplier,
    replace_supplier,
    request_cancellation,
    start_order,
)


class BaseOrderTest(TestCase):
    def setUp(self):
        self.tenant, _ = Tenant.objects.get_or_create(slug="salmandyar", defaults={"name": "Test"})
        self.person = Person.objects.create(tenant=self.tenant, full_name="Test Person")
        self.user = UserAccount.objects.create_user(phone="09120000001", person=self.person, tenant=self.tenant)
        # Grant cancellation permissions (Sprint 5.3A)
        cancellation_role = Role.objects.create(
            tenant=self.tenant,
            slug="test-cancellation-role",
            name="Test Cancellation Role",
            permissions=["orders.cancellation.request", "orders.cancellation.approve"],
        )
        RoleAssignment.objects.create(
            tenant=self.tenant,
            user=self.user,
            role=cancellation_role,
            is_active=True,
        )
        self.category = ServiceCategory.objects.create(
            tenant_id=self.tenant.id, name="Test Category", slug="test-cat", status=CatalogStatus.ACTIVE
        )
        self.inactive_cat = ServiceCategory.objects.create(
            tenant_id=self.tenant.id, name="Inactive", slug="inactive-cat", status=CatalogStatus.INACTIVE
        )
        self.service_type = ServiceType.objects.create(
            tenant_id=self.tenant.id,
            category=self.category,
            name="Test Type",
            slug="test-type",
            status=CatalogStatus.ACTIVE,
        )
        self.inactive_type = ServiceType.objects.create(
            tenant_id=self.tenant.id,
            category=self.category,
            name="Inactive Type",
            slug="inactive-type",
            status=CatalogStatus.INACTIVE,
        )
        # Caregiver for assignment tests
        self.cg_person = Person.objects.create(tenant=self.tenant, full_name="Caregiver")
        self.cg_user = UserAccount.objects.create_user(phone="09130000001", person=self.cg_person, tenant=self.tenant)
        self.caregiver = CaregiverProfile.objects.create(
            user=self.cg_user,
            person=self.cg_person,
            phone="09130000001",
            display_name="Caregiver",
        )
        self.supplier = get_or_create_supplier_for_caregiver(self.caregiver, tenant_id=self.tenant.id)

    def _make_order_kwargs(self, **overrides):
        defaults = {
            "service_category_id": self.category.id,
            "description": "Test order",
            "phone": "09121111111",
            "address": "Test address",
            "city": "tehran",
        }
        defaults.update(overrides)
        return defaults


# === Catalog Tests ===


class CatalogTest(BaseOrderTest):
    def test_active_category_usable(self):
        order = create_public_order(**self._make_order_kwargs())
        self.assertEqual(order.service_category, self.category)

    def test_inactive_category_rejected(self):
        with self.assertRaises(OrderValidationError):
            create_public_order(**self._make_order_kwargs(service_category_id=self.inactive_cat.id))

    def test_active_type_usable(self):
        order = create_public_order(**self._make_order_kwargs(service_type_id=self.service_type.id))
        self.assertEqual(order.service_type, self.service_type)

    def test_inactive_type_rejected(self):
        with self.assertRaises(OrderValidationError):
            create_public_order(**self._make_order_kwargs(service_type_id=self.inactive_type.id))

    def test_seed_catalog_idempotent(self):
        from django.core.management import call_command

        call_command("seed_service_catalog")
        count1 = ServiceCategory.objects.count()
        call_command("seed_service_catalog")
        count2 = ServiceCategory.objects.count()
        self.assertEqual(count1, count2)


# === Order Creation Tests ===


class OrderCreationTest(BaseOrderTest):
    def test_public_order_pending_review(self):
        order = create_public_order(**self._make_order_kwargs())
        self.assertEqual(order.status, OrderStatus.PENDING_OPERATOR_REVIEW)
        self.assertEqual(order.source, OrderSource.PUBLIC)

    def test_operator_order_no_provider_new(self):
        order = create_operator_order(**self._make_order_kwargs())
        self.assertEqual(order.status, OrderStatus.NEW)

    def test_operator_order_with_provider_waiting(self):
        order = create_operator_order(**self._make_order_kwargs(assigned_supplier=self.supplier))
        self.assertEqual(order.status, OrderStatus.WAITING_SERVICE)

    def test_category_required(self):
        import uuid

        with self.assertRaises(OrderValidationError):
            create_public_order(**self._make_order_kwargs(service_category_id=uuid.uuid4()))

    def test_phone_required(self):
        with self.assertRaises(OrderValidationError):
            create_public_order(**self._make_order_kwargs(phone=""))

    def test_address_required(self):
        with self.assertRaises(OrderValidationError):
            create_public_order(**self._make_order_kwargs(address=""))

    def test_description_required(self):
        with self.assertRaises(OrderValidationError):
            create_public_order(**self._make_order_kwargs(description=""))

    def test_creation_writes_history(self):
        order = create_public_order(**self._make_order_kwargs())
        history = OrderStatusHistory.objects.filter(order=order)
        self.assertEqual(history.count(), 1)
        self.assertEqual(history.first().to_status, OrderStatus.PENDING_OPERATOR_REVIEW)


# === Approval Tests ===


class OrderApprovalTest(BaseOrderTest):
    def test_approve_without_provider_new(self):
        order = create_public_order(**self._make_order_kwargs())
        order = approve_public_order(order_id=order.id, reviewed_by=self.user)
        self.assertEqual(order.status, OrderStatus.NEW)

    def test_approve_with_provider_waiting(self):
        order = create_public_order(**self._make_order_kwargs())
        order = approve_public_order(order_id=order.id, reviewed_by=self.user, assigned_supplier=self.supplier)
        self.assertEqual(order.status, OrderStatus.WAITING_SERVICE)


# === Assignment Tests ===


class AssignmentTest(BaseOrderTest):
    def test_assign_provider_waiting(self):
        order = create_operator_order(**self._make_order_kwargs())
        order = assign_supplier(order_id=order.id, supplier=self.supplier)
        self.assertEqual(order.status, OrderStatus.WAITING_SERVICE)

    def test_remove_provider_new(self):
        order = create_operator_order(**self._make_order_kwargs(assigned_supplier=self.supplier))
        order = remove_supplier(order_id=order.id)
        self.assertEqual(order.status, OrderStatus.NEW)

    def test_replace_provider_waiting(self):
        order = create_operator_order(**self._make_order_kwargs(assigned_supplier=self.supplier))
        cg2_person = Person.objects.create(tenant=self.tenant, full_name="CG2")
        cg2_user = UserAccount.objects.create_user(phone="09130000002", person=cg2_person, tenant=self.tenant)
        cg2 = CaregiverProfile.objects.create(user=cg2_user, person=cg2_person, phone="09130000002", display_name="CG2")
        cg2_supplier = get_or_create_supplier_for_caregiver(cg2, tenant_id=self.tenant.id)
        order = replace_supplier(order_id=order.id, new_supplier=cg2_supplier)
        self.assertEqual(order.status, OrderStatus.WAITING_SERVICE)
        self.assertEqual(order.assigned_provider, cg2)


# === Execution Tests ===


class ExecutionTest(BaseOrderTest):
    def test_start_order(self):
        order = create_operator_order(**self._make_order_kwargs(assigned_supplier=self.supplier))
        order = start_order(order_id=order.id)
        self.assertEqual(order.status, OrderStatus.IN_PROGRESS)

    def test_complete_order(self):
        order = create_operator_order(**self._make_order_kwargs(assigned_supplier=self.supplier))
        order = start_order(order_id=order.id)
        order = complete_order(order_id=order.id)
        self.assertEqual(order.status, OrderStatus.COMPLETED)


# === Cancellation Tests ===


class CancellationTest(BaseOrderTest):
    def test_request_cancellation(self):
        order = create_operator_order(**self._make_order_kwargs())
        order = request_cancellation(order_id=order.id, requested_by=self.user)
        self.assertEqual(order.status, OrderStatus.CANCELLATION_REQUESTED)

    def test_approve_cancellation(self):
        order = create_operator_order(**self._make_order_kwargs())
        request_cancellation(order_id=order.id, requested_by=self.user)
        order = approve_cancellation(order_id=order.id, changed_by=self.user)
        self.assertEqual(order.status, OrderStatus.CANCELLED)


# === Final State Immutability ===


class FinalStateTest(BaseOrderTest):
    def test_cannot_assign_completed(self):
        order = create_operator_order(**self._make_order_kwargs(assigned_supplier=self.supplier))
        start_order(order_id=order.id)
        complete_order(order_id=order.id)
        with self.assertRaises(OrderStateError):
            assign_supplier(order_id=order.id, supplier=self.supplier)

    def test_cannot_start_cancelled(self):
        order = create_operator_order(**self._make_order_kwargs(assigned_supplier=self.supplier))
        request_cancellation(order_id=order.id, requested_by=self.user)
        approve_cancellation(order_id=order.id)
        with self.assertRaises(OrderStateError):
            start_order(order_id=order.id)

    def test_cannot_complete_cancelled(self):
        order = create_operator_order(**self._make_order_kwargs(assigned_supplier=self.supplier))
        request_cancellation(order_id=order.id, requested_by=self.user)
        approve_cancellation(order_id=order.id)
        with self.assertRaises(OrderStateError):
            complete_order(order_id=order.id)
