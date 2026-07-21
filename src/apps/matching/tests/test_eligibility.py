"""Tests for EligibilityService structured codes."""

from apps.kernel.models.configuration import ConfigurationKey, ConfigurationValue, ScopeLevel, ValueType
from apps.kernel.models.supplier import AvailabilityStatus, SupplierStatus, SupplierType, VerificationLevel
from apps.matching.models import EligibilityCode
from apps.matching.services.eligibility import EligibilityService

from .helpers import MatchingTestCase


class EligibilityServiceTest(MatchingTestCase):
    def test_eligible_supplier(self):
        supplier = self._create_supplier()
        result = EligibilityService.evaluate(order=self.order, supplier=supplier)
        self.assertTrue(result.eligible)
        self.assertEqual(result.code, EligibilityCode.ELIGIBLE)

    def test_wrong_tenant_code(self):
        supplier = self._create_supplier(tenant=self.other_tenant)
        result = EligibilityService.evaluate(order=self.order, supplier=supplier)
        self.assertFalse(result.eligible)
        self.assertEqual(result.code, EligibilityCode.WRONG_TENANT)
        self.assertIn("supplier_tenant_id", result.reason)
        self.assertIn("order_tenant_id", result.reason)

    def test_supplier_not_active_code(self):
        supplier = self._create_supplier(status=SupplierStatus.SUSPENDED)
        result = EligibilityService.evaluate(order=self.order, supplier=supplier)
        self.assertFalse(result.eligible)
        self.assertEqual(result.code, EligibilityCode.SUPPLIER_NOT_ACTIVE)

    def test_offline_supplier_ineligible(self):
        supplier = self._create_supplier(availability_status=AvailabilityStatus.OFFLINE)
        result = EligibilityService.evaluate(order=self.order, supplier=supplier)
        self.assertFalse(result.eligible)
        self.assertEqual(result.code, EligibilityCode.SUPPLIER_UNAVAILABLE)

    def test_on_leave_supplier_ineligible(self):
        supplier = self._create_supplier(availability_status=AvailabilityStatus.ON_LEAVE)
        result = EligibilityService.evaluate(order=self.order, supplier=supplier)
        self.assertFalse(result.eligible)
        self.assertEqual(result.code, EligibilityCode.SUPPLIER_UNAVAILABLE)

    def test_category_mismatch_code(self):
        supplier = self._create_supplier(service_categories=[str(self.other_category.id)])
        result = EligibilityService.evaluate(order=self.order, supplier=supplier)
        self.assertFalse(result.eligible)
        self.assertEqual(result.code, EligibilityCode.CATEGORY_NOT_SUPPORTED)

    def test_supplier_type_not_allowed_code(self):
        config_key = ConfigurationKey.objects.create(
            key="marketplace.supplier_model",
            owner_module="M19",
            scope_level=ScopeLevel.TENANT,
            value_type=ValueType.ENUM,
            default_value="hybrid",
            allowed_values=["independent_only", "organization_only", "hybrid"],
        )
        ConfigurationValue.objects.create(
            tenant_id=self.tenant.id,
            config_key=config_key,
            scope_type=ScopeLevel.TENANT,
            value="organization_only",
            is_active=True,
        )
        supplier = self._create_supplier(supplier_type=SupplierType.INDEPENDENT_PROVIDER)
        result = EligibilityService.evaluate(order=self.order, supplier=supplier)
        self.assertFalse(result.eligible)
        self.assertEqual(result.code, EligibilityCode.SUPPLIER_TYPE_NOT_ALLOWED)

    def test_below_verification_threshold_code(self):
        config_key = ConfigurationKey.objects.create(
            key="matching.eligibility.min_verification_level",
            owner_module="M02",
            scope_level=ScopeLevel.TENANT,
            value_type=ValueType.STRING,
            default_value="",
        )
        ConfigurationValue.objects.create(
            tenant_id=self.tenant.id,
            config_key=config_key,
            scope_type=ScopeLevel.TENANT,
            value="advanced",
            is_active=True,
        )
        supplier = self._create_supplier(verification_level=VerificationLevel.BASIC)
        result = EligibilityService.evaluate(order=self.order, supplier=supplier)
        self.assertFalse(result.eligible)
        self.assertEqual(result.code, EligibilityCode.BELOW_VERIFICATION_THRESHOLD)

    def test_verification_threshold_met_stays_eligible(self):
        config_key = ConfigurationKey.objects.create(
            key="matching.eligibility.min_verification_level",
            owner_module="M02",
            scope_level=ScopeLevel.TENANT,
            value_type=ValueType.STRING,
            default_value="",
        )
        ConfigurationValue.objects.create(
            tenant_id=self.tenant.id,
            config_key=config_key,
            scope_type=ScopeLevel.TENANT,
            value="advanced",
            is_active=True,
        )
        supplier = self._create_supplier(verification_level=VerificationLevel.PREMIUM)
        result = EligibilityService.evaluate(order=self.order, supplier=supplier)
        self.assertTrue(result.eligible)
