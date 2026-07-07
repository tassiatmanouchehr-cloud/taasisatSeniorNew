"""Shared fixtures for booking engine tests (not a test module itself)."""

import uuid

from django.test import TestCase

from apps.kernel.models import Tenant
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)
from apps.matching.models import EligibilityCode, MatchCandidate, MatchCandidateStatus, MatchRound, MatchRoundStatus
from apps.orders.models import CatalogStatus, Order, OrderSource, OrderStatus, ServiceCategory


class BookingTestCase(TestCase):
    """Base test case providing a tenant, a second tenant, a category, an order, and factories."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"booking-{uuid.uuid4().hex[:8]}", name="Booking Test Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"booking-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )

        self.order = Order.objects.create(
            tenant=self.tenant,
            source=OrderSource.OPERATOR,
            status=OrderStatus.NEW,
            service_category=self.category,
            description="Need home care",
            city="tehran",
            address="Some address",
            phone="09120000000",
        )

    def _create_supplier(
        self,
        *,
        tenant=None,
        supplier_type=SupplierType.INDEPENDENT_PROVIDER,
        status=SupplierStatus.ACTIVE,
        availability_status=AvailabilityStatus.AVAILABLE,
        verification_level=VerificationLevel.BASIC,
        service_categories=None,
        **kwargs,
    ) -> ServiceSupplier:
        tenant = tenant or self.tenant
        defaults = {
            "tenant_id": tenant.id,
            "supplier_type": supplier_type,
            "linked_entity_id": uuid.uuid4(),
            "linked_entity_type": "TestProfile",
            "display_name": "Test Supplier",
            "status": status,
            "availability_status": availability_status,
            "verification_level": verification_level,
            "service_categories": service_categories if service_categories is not None else [str(self.category.id)],
        }
        defaults.update(kwargs)
        return ServiceSupplier.objects.create(**defaults)

    def _create_match_candidate(self, *, supplier, order=None, eligible=True, status=None) -> MatchCandidate:
        order = order or self.order
        match_round = MatchRound.objects.create(
            tenant_id=self.tenant.id, order=order, status=MatchRoundStatus.COMPLETED,
        )
        return MatchCandidate.objects.create(
            tenant_id=self.tenant.id,
            match_round=match_round,
            supplier=supplier,
            eligible=eligible,
            eligibility_code=EligibilityCode.ELIGIBLE if eligible else EligibilityCode.SUPPLIER_NOT_ACTIVE,
            status=status or MatchCandidateStatus.RANKED,
        )
