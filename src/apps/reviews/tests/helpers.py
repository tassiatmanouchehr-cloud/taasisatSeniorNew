"""Shared fixtures for reviews tests (not a test module itself)."""

import uuid

from django.test import TestCase

from apps.accounts.models.profiles import CustomerProfile
from apps.booking.services.assignment_service import AssignmentService
from apps.execution.services.session_service import ExecutionService
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)
from apps.orders.models import CatalogStatus, Order, OrderSource, OrderStatus, ServiceCategory


class ReviewsTestCase(TestCase):
    """Base test case: a tenant, an assigned supplier, and a helper to drive an order to COMPLETED."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"reviews-{uuid.uuid4().hex[:8]}", name="Reviews Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"reviews-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        self.category = ServiceCategory.objects.create(
            tenant=self.tenant,
            name="Home Care",
            slug="home-care",
            status=CatalogStatus.ACTIVE,
        )

        self.customer_profile = self._create_customer(tenant=self.tenant)

        self.order = self._create_order(
            tenant=self.tenant, category=self.category, customer_profile=self.customer_profile
        )

        self.supplier = self._create_supplier(tenant=self.tenant)
        self.supplier_assignment = AssignmentService.assign(order_id=self.order.id, supplier=self.supplier)
        self.order.refresh_from_db()

    def _create_customer(self, *, tenant, display_name="Test Customer", phone=None) -> CustomerProfile:
        phone = phone or f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=display_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return CustomerProfile.objects.create(
            user=user,
            person=person,
            phone=phone,
            display_name=display_name,
        )

    def _create_order(self, *, tenant, category, customer_profile) -> Order:
        return Order.objects.create(
            tenant=tenant,
            source=OrderSource.OPERATOR,
            status=OrderStatus.NEW,
            service_category=category,
            customer_profile=customer_profile,
            description="Need home care",
            city="tehran",
            address="Some address",
            phone="09120000000",
        )

    def _create_supplier(self, *, tenant=None, **kwargs) -> ServiceSupplier:
        tenant = tenant or self.tenant
        defaults = {
            "tenant_id": tenant.id,
            "supplier_type": SupplierType.INDEPENDENT_PROVIDER,
            "linked_entity_id": uuid.uuid4(),
            "linked_entity_type": "TestProfile",
            "display_name": "Test Supplier",
            "status": SupplierStatus.ACTIVE,
            "availability_status": AvailabilityStatus.AVAILABLE,
            "verification_level": VerificationLevel.BASIC,
            "service_categories": [str(self.category.id)],
        }
        defaults.update(kwargs)
        return ServiceSupplier.objects.create(**defaults)

    def _complete_order(self, *, order=None, supplier_assignment=None) -> Order:
        """Drives an order through execution to COMPLETED, returns the refreshed Order."""
        order = order or self.order
        supplier_assignment = supplier_assignment or self.supplier_assignment
        session = ExecutionService.create_session(supplier_assignment=supplier_assignment)
        ExecutionService.start_session(session_id=session.id)
        ExecutionService.complete_session(session_id=session.id)
        ExecutionService.close_session(session_id=session.id)
        order.refresh_from_db()
        return order

    @staticmethod
    def _dimension_scores(**overrides):
        scores = {
            "QUALITY": 5,
            "PUNCTUALITY": 4,
            "PROFESSIONALISM": 5,
            "COMMUNICATION": 4,
        }
        scores.update(overrides)
        return scores
