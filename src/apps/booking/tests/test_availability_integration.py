"""
Tests proving AssignmentService.assign()'s optional Module 10 integration:
conservative by design — availability/capacity validation only runs when
BOTH requested_start and requested_end are explicitly supplied. Every call
that omits them (all pre-existing call sites) is completely unaffected.
"""

import datetime as dt
from unittest.mock import patch

from django.utils import timezone

from apps.availability.services import AvailabilityMutationService, CapacityService
from apps.booking.models import SupplierAssignment
from apps.booking.services.assignment_service import AssignmentError, AssignmentService

from .helpers import BookingTestCase


def _next_monday() -> dt.date:
    today = timezone.localdate()
    return today + dt.timedelta(days=(0 - today.weekday()) % 7)


class AssignmentAvailabilityIntegrationTest(BookingTestCase):
    def setUp(self):
        super().setUp()
        self.supplier = self._create_supplier()
        self.monday = _next_monday()

    def _aware(self, hour):
        return timezone.make_aware(dt.datetime.combine(self.monday, dt.time(hour, 0)))

    def test_assign_without_requested_bounds_is_unaffected(self):
        """No working windows configured at all — would fail availability if checked,
        but since neither bound is supplied, the check never runs."""
        assignment = AssignmentService.assign(order_id=self.order.id, supplier=self.supplier)
        self.assertIsNotNone(assignment.pk)

    def test_assign_rejects_supplier_unavailable_for_requested_range(self):
        # No working window configured -> unavailable by default.
        with self.assertRaises(AssignmentError):
            AssignmentService.assign(
                order_id=self.order.id, supplier=self.supplier,
                requested_start=self._aware(10), requested_end=self._aware(11),
            )

        self.assertEqual(SupplierAssignment.objects.filter(order=self.order).count(), 0)
        self.order.refresh_from_db()
        self.assertIsNone(self.order.assigned_supplier_id)

    def test_assign_succeeds_when_supplier_available_for_requested_range(self):
        AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=0, start_time=dt.time(9, 0), end_time=dt.time(17, 0),
        )

        assignment = AssignmentService.assign(
            order_id=self.order.id, supplier=self.supplier,
            requested_start=self._aware(10), requested_end=self._aware(11),
        )
        self.assertIsNotNone(assignment.pk)

    def test_assign_rejects_when_capacity_exceeded(self):
        AvailabilityMutationService.add_working_window(
            supplier=self.supplier, day_of_week=0, start_time=dt.time(9, 0), end_time=dt.time(17, 0),
        )
        CapacityService.set_capacity_rule(supplier=self.supplier, max_concurrent_assignments=1)
        AssignmentService.assign(order_id=self.order.id, supplier=self.supplier)  # fills capacity, no bounds

        second_order = self._make_second_order()

        with self.assertRaises(AssignmentError):
            AssignmentService.assign(
                order_id=second_order.id, supplier=self.supplier,
                requested_start=self._aware(10), requested_end=self._aware(11),
            )

        self.assertEqual(SupplierAssignment.objects.filter(order=second_order).count(), 0)

    def test_assign_bypasses_check_when_enforcement_disabled(self):
        with patch(
            "apps.availability.services.configuration.AvailabilityConfiguration.get_enforcement_enabled",
            return_value=False,
        ):
            # No working window configured (would otherwise be unavailable) — but
            # enforcement is disabled, so the assignment must still succeed.
            assignment = AssignmentService.assign(
                order_id=self.order.id, supplier=self.supplier,
                requested_start=self._aware(10), requested_end=self._aware(11),
            )
        self.assertIsNotNone(assignment.pk)

    def _make_second_order(self):
        from apps.orders.models import Order, OrderSource, OrderStatus

        return Order.objects.create(
            tenant=self.tenant,
            source=OrderSource.OPERATOR,
            status=OrderStatus.NEW,
            service_category=self.category,
            description="Second order",
            city="tehran",
            address="Some other address",
            phone="09120000001",
        )
