"""
Tests proving availability (working windows + blocked periods) works
identically for an organization-type supplier as for an independent
provider — ServiceSupplier already unifies both, so no special-casing
is needed anywhere in the availability app.
"""

import datetime as dt

from django.utils import timezone

from apps.kernel.models.supplier import SupplierType

from ..services import AvailabilityMutationService, AvailabilityQueryService
from .helpers import AvailabilityTestCase


def _next_monday() -> dt.date:
    today = timezone.localdate()
    return today + dt.timedelta(days=(0 - today.weekday()) % 7)


class OrganizationSupplierAvailabilityTest(AvailabilityTestCase):
    def setUp(self):
        super().setUp()
        self.org_supplier = self._create_supplier(supplier_type=SupplierType.ORGANIZATION, display_name="Care Org")
        self.monday = _next_monday()
        AvailabilityMutationService.add_working_window(
            supplier=self.org_supplier,
            day_of_week=0,
            start_time=dt.time(8, 0),
            end_time=dt.time(20, 0),
        )

    def _aware(self, hour):
        return timezone.make_aware(dt.datetime.combine(self.monday, dt.time(hour, 0)))

    def test_organization_supplier_available_within_working_window(self):
        self.assertTrue(
            AvailabilityQueryService.is_supplier_available(
                supplier=self.org_supplier,
                start=self._aware(9),
                end=self._aware(10),
            ),
        )

    def test_organization_supplier_blocked_period_overrides_window(self):
        AvailabilityMutationService.add_blocked_period(
            supplier=self.org_supplier,
            start_at=self._aware(9),
            end_at=self._aware(11),
        )
        self.assertFalse(
            AvailabilityQueryService.is_supplier_available(
                supplier=self.org_supplier,
                start=self._aware(9),
                end=self._aware(10),
            ),
        )
