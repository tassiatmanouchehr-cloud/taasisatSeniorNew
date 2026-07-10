"""Tests for ProviderAssignmentActionService — Epic 02."""

import uuid

from django.test import TestCase

from apps.accounts.models.profiles import CaregiverProfile
from apps.accounts.services.provider_identity import resolve_supplier_for_user
from apps.booking.models import SupplierAssignment, SupplierAssignmentStatus
from apps.booking.services.assignment_service import AssignmentService
from apps.booking.services.provider_actions import ProviderAssignmentActionError, ProviderAssignmentActionService
from apps.kernel.models import Person, Tenant, UserAccount
from apps.orders.models import CatalogStatus, Order, OrderSource, OrderStatus, ServiceCategory


class ProviderAssignmentActionTestCase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"provact-{uuid.uuid4().hex[:8]}", name="Provider Action Tenant")
        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )
        self.order = Order.objects.create(
            tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category, description="x", city="tehran", address="addr", phone="0912",
        )
        self.provider_user, self.supplier = self._create_provider()
        self.other_provider_user, self.other_supplier = self._create_provider(phone="09123334455")

        self.assignment = AssignmentService.assign(order_id=self.order.id, supplier=self.supplier)

    def _create_provider(self, *, phone=None):
        phone = phone or f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=self.tenant, full_name="Provider")
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)
        CaregiverProfile.objects.create(user=user, person=person, phone=phone, display_name="Provider")
        supplier = resolve_supplier_for_user(user)
        return user, supplier


class ConfirmAssignmentTest(ProviderAssignmentActionTestCase):
    def test_confirm_transitions_to_confirmed(self):
        result = ProviderAssignmentActionService.confirm(assignment_id=self.assignment.id, actor=self.provider_user)
        self.assertEqual(result.status, SupplierAssignmentStatus.CONFIRMED)

    def test_confirm_persists(self):
        ProviderAssignmentActionService.confirm(assignment_id=self.assignment.id, actor=self.provider_user)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, SupplierAssignmentStatus.CONFIRMED)

    def test_other_provider_cannot_confirm(self):
        with self.assertRaises(ProviderAssignmentActionError):
            ProviderAssignmentActionService.confirm(assignment_id=self.assignment.id, actor=self.other_provider_user)

    def test_cannot_confirm_already_confirmed(self):
        ProviderAssignmentActionService.confirm(assignment_id=self.assignment.id, actor=self.provider_user)
        with self.assertRaises(ProviderAssignmentActionError):
            ProviderAssignmentActionService.confirm(assignment_id=self.assignment.id, actor=self.provider_user)

    def test_confirm_unknown_assignment_raises(self):
        with self.assertRaises(ProviderAssignmentActionError):
            ProviderAssignmentActionService.confirm(assignment_id=uuid.uuid4(), actor=self.provider_user)

    def test_confirm_does_not_touch_order_status(self):
        self.order.refresh_from_db()
        before = self.order.status  # already transitioned by AssignmentService.assign() in setUp
        ProviderAssignmentActionService.confirm(assignment_id=self.assignment.id, actor=self.provider_user)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, before)


class DeclineAssignmentTest(ProviderAssignmentActionTestCase):
    def test_decline_transitions_to_declined(self):
        result = ProviderAssignmentActionService.decline(
            assignment_id=self.assignment.id, actor=self.provider_user, reason="Too far",
        )
        self.assertEqual(result.status, SupplierAssignmentStatus.DECLINED)

    def test_decline_stores_reason_in_metadata(self):
        ProviderAssignmentActionService.decline(
            assignment_id=self.assignment.id, actor=self.provider_user, reason="Too far",
        )
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.metadata.get("decline_reason"), "Too far")

    def test_other_provider_cannot_decline(self):
        with self.assertRaises(ProviderAssignmentActionError):
            ProviderAssignmentActionService.decline(assignment_id=self.assignment.id, actor=self.other_provider_user)

    def test_cannot_decline_already_declined(self):
        ProviderAssignmentActionService.decline(assignment_id=self.assignment.id, actor=self.provider_user)
        with self.assertRaises(ProviderAssignmentActionError):
            ProviderAssignmentActionService.decline(assignment_id=self.assignment.id, actor=self.provider_user)


class ProviderAssignmentEventPublishingTest(ProviderAssignmentActionTestCase):
    def test_confirm_publishes_and_audits(self):
        from apps.kernel.models.audit import AuditLog

        with self.captureOnCommitCallbacks(execute=True):
            ProviderAssignmentActionService.confirm(assignment_id=self.assignment.id, actor=self.provider_user)

        entry = AuditLog.objects.get(action="domain_event.ProviderAssignmentAccepted", resource_id=self.assignment.id)
        self.assertEqual(entry.resource_type, "SupplierAssignment")
        self.assertEqual(entry.actor_id, self.provider_user.person_id)

    def test_decline_publishes_and_audits(self):
        from apps.kernel.models.audit import AuditLog

        with self.captureOnCommitCallbacks(execute=True):
            ProviderAssignmentActionService.decline(assignment_id=self.assignment.id, actor=self.provider_user)

        entry = AuditLog.objects.get(action="domain_event.ProviderAssignmentRejected", resource_id=self.assignment.id)
        self.assertEqual(entry.resource_type, "SupplierAssignment")


class CrossTenantAssignmentIsolationTest(TestCase):
    """A provider registered in Tenant A must not be able to view, confirm,
    or decline a SupplierAssignment that belongs to Tenant B — even when
    passing their own (correct) tenant_id and their own (correct) supplier,
    and even when they know the order_id (e.g. by guessing a sequential id
    or via a leaked URL). This is the production-shape scenario: the portal
    always passes the acting provider's own tenant_id/supplier, so the only
    realistic attack is targeting another tenant's order_id."""

    def setUp(self):
        self.tenant_a = Tenant.objects.create(slug=f"tena-{uuid.uuid4().hex[:8]}", name="Tenant A")
        self.tenant_b = Tenant.objects.create(slug=f"tenb-{uuid.uuid4().hex[:8]}", name="Tenant B")

        self.category_a = ServiceCategory.objects.create(
            tenant=self.tenant_a, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )
        self.category_b = ServiceCategory.objects.create(
            tenant=self.tenant_b, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )

        self.order_a = Order.objects.create(
            tenant=self.tenant_a, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category_a, description="x", city="tehran", address="addr", phone="0912",
        )
        self.order_b = Order.objects.create(
            tenant=self.tenant_b, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category_b, description="x", city="tehran", address="addr", phone="0912",
        )

        self.provider_a, self.supplier_a = self._create_provider(tenant=self.tenant_a, phone="09121110001")
        self.provider_b, self.supplier_b = self._create_provider(tenant=self.tenant_b, phone="09121110002")

        self.assignment_a = AssignmentService.assign(order_id=self.order_a.id, supplier=self.supplier_a)
        self.assignment_b = AssignmentService.assign(order_id=self.order_b.id, supplier=self.supplier_b)

    def _create_provider(self, *, tenant, phone):
        person = Person.objects.create(tenant=tenant, full_name="Provider")
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        CaregiverProfile.objects.create(user=user, person=person, phone=phone, display_name="Provider")
        supplier = resolve_supplier_for_user(user)
        return user, supplier

    def test_list_for_supplier_never_includes_another_tenants_assignment(self):
        from apps.booking.services.queries import ProviderAssignmentQueryService

        results = ProviderAssignmentQueryService.list_for_supplier(supplier=self.supplier_a, tenant_id=self.tenant_a.id)
        self.assertEqual([a.id for a in results], [self.assignment_a.id])

    def test_get_for_supplier_cannot_view_another_tenants_order(self):
        """Provider A, using their OWN tenant_id and supplier, asks for
        order_b's assignment (order_b only exists in tenant B)."""
        from apps.booking.services.queries import ProviderAssignmentNotFoundError, ProviderAssignmentQueryService

        with self.assertRaises(ProviderAssignmentNotFoundError):
            ProviderAssignmentQueryService.get_for_supplier(
                supplier=self.supplier_a, tenant_id=self.tenant_a.id, order_id=self.order_b.id,
            )

    def test_confirm_cannot_reach_another_tenants_assignment(self):
        with self.assertRaises(ProviderAssignmentActionError):
            ProviderAssignmentActionService.confirm(assignment_id=self.assignment_b.id, actor=self.provider_a)

        self.assignment_b.refresh_from_db()
        self.assertEqual(self.assignment_b.status, SupplierAssignmentStatus.ASSIGNED)

    def test_decline_cannot_reach_another_tenants_assignment(self):
        with self.assertRaises(ProviderAssignmentActionError):
            ProviderAssignmentActionService.decline(assignment_id=self.assignment_b.id, actor=self.provider_a)

        self.assignment_b.refresh_from_db()
        self.assertEqual(self.assignment_b.status, SupplierAssignmentStatus.ASSIGNED)


class ProviderIdentityResolutionTest(ProviderAssignmentActionTestCase):
    def test_resolve_supplier_for_user_is_idempotent(self):
        first = resolve_supplier_for_user(self.provider_user)
        second = resolve_supplier_for_user(self.provider_user)
        self.assertEqual(first.id, second.id)

    def test_resolve_supplier_for_user_without_caregiver_profile_raises(self):
        from apps.accounts.services.errors import AccountsError

        person = Person.objects.create(tenant=self.tenant, full_name="No Provider")
        user = UserAccount.objects.create_user(phone="09129998877", person=person, tenant=self.tenant)
        with self.assertRaises(AccountsError):
            resolve_supplier_for_user(user)
