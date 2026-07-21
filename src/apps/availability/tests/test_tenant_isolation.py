"""Tests proving availability records are tenant-scoped."""

import datetime as dt

from apps.availability.models import AvailabilityBlockedPeriod, CapacityRule, ProviderWorkingWindow
from apps.availability.services import AvailabilityMutationService, CapacityService

from .helpers import AvailabilityTestCase


class AvailabilityTenantIsolationTest(AvailabilityTestCase):
    def setUp(self):
        super().setUp()
        self.supplier = self._create_supplier(tenant=self.tenant)
        self.other_supplier = self._create_supplier(tenant=self.other_tenant)

    def test_working_window_tenant_matches_supplier_tenant(self):
        window = AvailabilityMutationService.add_working_window(
            supplier=self.supplier,
            day_of_week=0,
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
        )
        self.assertEqual(window.tenant_id, self.supplier.tenant_id)

    def test_for_tenant_scopes_working_windows(self):
        AvailabilityMutationService.add_working_window(
            supplier=self.supplier,
            day_of_week=0,
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
        )
        AvailabilityMutationService.add_working_window(
            supplier=self.other_supplier,
            day_of_week=0,
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
        )

        self.assertEqual(ProviderWorkingWindow.objects.for_tenant(self.tenant.id).count(), 1)
        self.assertEqual(ProviderWorkingWindow.objects.for_tenant(self.other_tenant.id).count(), 1)

    def test_for_tenant_scopes_blocked_periods(self):
        from django.utils import timezone

        start = timezone.now()
        AvailabilityMutationService.add_blocked_period(
            supplier=self.supplier,
            start_at=start,
            end_at=start + timezone.timedelta(hours=1),
        )

        self.assertEqual(AvailabilityBlockedPeriod.objects.for_tenant(self.tenant.id).count(), 1)
        self.assertEqual(AvailabilityBlockedPeriod.objects.for_tenant(self.other_tenant.id).count(), 0)

    def test_for_tenant_scopes_capacity_rules(self):
        CapacityService.set_capacity_rule(supplier=self.supplier, max_concurrent_assignments=2)

        self.assertEqual(CapacityRule.objects.for_tenant(self.tenant.id).count(), 1)
        self.assertEqual(CapacityRule.objects.for_tenant(self.other_tenant.id).count(), 0)
