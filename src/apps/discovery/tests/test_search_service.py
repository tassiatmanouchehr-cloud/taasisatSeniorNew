"""
Tests for SupplierSearchService.filter_suppliers(): category/type/
availability/verification filtering, city filtering via the sanctioned
bridge, explicit-range availability filtering, and no leakage of inactive/
offline/other-tenant suppliers.
"""

import datetime as dt

from django.utils import timezone

from apps.availability.services import AvailabilityMutationService
from apps.discovery.services import DiscoveryError, SupplierSearchService, normalize_query
from apps.kernel.models.supplier import AvailabilityStatus, SupplierStatus, SupplierType, VerificationLevel

from .helpers import DiscoveryTestCase


class SupplierSearchServiceTest(DiscoveryTestCase):
    def test_returns_active_supplier_in_tenant(self):
        supplier = self._create_supplier()
        query = normalize_query(tenant_id=self.tenant.id)
        self.assertEqual(SupplierSearchService.filter_suppliers(query), [supplier])

    def test_excludes_other_tenant_suppliers(self):
        self._create_supplier(tenant=self.other_tenant)
        query = normalize_query(tenant_id=self.tenant.id)
        self.assertEqual(SupplierSearchService.filter_suppliers(query), [])

    def test_excludes_inactive_suppliers(self):
        self._create_supplier(status=SupplierStatus.SUSPENDED)
        query = normalize_query(tenant_id=self.tenant.id)
        self.assertEqual(SupplierSearchService.filter_suppliers(query), [])

    def test_excludes_deactivated_suppliers(self):
        self._create_supplier(status=SupplierStatus.DEACTIVATED)
        query = normalize_query(tenant_id=self.tenant.id)
        self.assertEqual(SupplierSearchService.filter_suppliers(query), [])

    def test_filters_by_service_category(self):
        matching = self._create_supplier(service_categories=[str(self.category.id)])
        self._create_supplier(display_name="Other", service_categories=[str(self.other_category.id)])

        query = normalize_query(tenant_id=self.tenant.id, service_category_id=self.category.id)
        self.assertEqual(SupplierSearchService.filter_suppliers(query), [matching])

    def test_filters_by_supplier_type(self):
        independent = self._create_supplier(supplier_type=SupplierType.INDEPENDENT_PROVIDER)
        self._create_supplier(display_name="Org", supplier_type=SupplierType.ORGANIZATION)

        query = normalize_query(tenant_id=self.tenant.id, supplier_type=SupplierType.INDEPENDENT_PROVIDER)
        self.assertEqual(SupplierSearchService.filter_suppliers(query), [independent])

    def test_filters_by_availability_status(self):
        available = self._create_supplier(availability_status=AvailabilityStatus.AVAILABLE)
        self._create_supplier(display_name="Busy", availability_status=AvailabilityStatus.BUSY)

        query = normalize_query(tenant_id=self.tenant.id, availability_status=AvailabilityStatus.AVAILABLE)
        self.assertEqual(SupplierSearchService.filter_suppliers(query), [available])

    def test_offline_supplier_excluded_by_availability_filter(self):
        self._create_supplier(availability_status=AvailabilityStatus.OFFLINE)
        query = normalize_query(tenant_id=self.tenant.id, availability_status=AvailabilityStatus.AVAILABLE)
        self.assertEqual(SupplierSearchService.filter_suppliers(query), [])

    def test_filters_by_verification_level(self):
        premium = self._create_supplier(verification_level=VerificationLevel.PREMIUM)
        self._create_supplier(display_name="Basic", verification_level=VerificationLevel.BASIC)

        query = normalize_query(tenant_id=self.tenant.id, verification_level=VerificationLevel.PREMIUM)
        self.assertEqual(SupplierSearchService.filter_suppliers(query), [premium])

    def test_filters_by_text_against_display_name(self):
        matching = self._create_supplier(display_name="Sunshine Home Care")
        self._create_supplier(display_name="Companionship Plus")

        query = normalize_query(tenant_id=self.tenant.id, text="sunshine")
        self.assertEqual(SupplierSearchService.filter_suppliers(query), [matching])

    def test_filters_by_city_via_bridge(self):
        tehran = self._create_caregiver_supplier(display_name="Tehran Caregiver", city="Tehran")
        self._create_caregiver_supplier(display_name="Shiraz Caregiver", city="Shiraz")

        query = normalize_query(tenant_id=self.tenant.id, city="tehran")
        self.assertEqual(SupplierSearchService.filter_suppliers(query), [tehran])

    def test_city_filter_excludes_supplier_with_no_resolvable_profile(self):
        self._create_supplier()  # linked_entity_type="TestProfile" -> resolve_supplier_entity() returns None
        query = normalize_query(tenant_id=self.tenant.id, city="tehran")
        self.assertEqual(SupplierSearchService.filter_suppliers(query), [])

    def test_availability_range_filter_requires_both_bounds(self):
        from apps.discovery.services.dto import SearchQuery

        bad_query = SearchQuery(tenant_id=self.tenant.id, requested_start=timezone.now(), requested_end=None)
        with self.assertRaises(DiscoveryError):
            SupplierSearchService.filter_suppliers(bad_query)

    def test_availability_range_filter_excludes_supplier_without_working_window(self):
        supplier = self._create_supplier()
        start = timezone.make_aware(dt.datetime.combine(timezone.localdate(), dt.time(10, 0)))
        end = start + dt.timedelta(hours=1)

        query = normalize_query(tenant_id=self.tenant.id, requested_start=start, requested_end=end)
        self.assertEqual(SupplierSearchService.filter_suppliers(query), [])

    def test_availability_range_filter_includes_supplier_within_working_window(self):
        supplier = self._create_supplier()
        day = timezone.localdate()
        AvailabilityMutationService.add_working_window(
            supplier=supplier,
            day_of_week=day.weekday(),
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
        )
        start = timezone.make_aware(dt.datetime.combine(day, dt.time(10, 0)))
        end = start + dt.timedelta(hours=1)

        query = normalize_query(tenant_id=self.tenant.id, requested_start=start, requested_end=end)
        self.assertEqual(SupplierSearchService.filter_suppliers(query), [supplier])
