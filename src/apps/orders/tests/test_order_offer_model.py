"""Tests for OrderOffer model — Phase 1 domain foundation.

Covers: model creation, constraints, indexes, state properties,
uniqueness, tenant isolation, timestamps, domain properties.
"""

from decimal import Decimal
import uuid

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)
from apps.orders.models import (
    CatalogStatus,
    OFFER_TERMINAL_STATUSES,
    Order,
    OrderOffer,
    OrderOfferStatus,
    OrderSource,
    OrderStatus,
    ServiceCategory,
)


class OrderOfferModelTest(TestCase):
    """Basic model creation and field tests."""

    def setUp(self):
        self.tenant, _ = Tenant.objects.get_or_create(
            slug="offer-test", defaults={"name": "Offer Test Tenant"}
        )
        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )
        self.order = Order.objects.create(
            tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category, description="Test order",
            city="tehran", address="Test address", phone="09120000000",
        )
        self.supplier = ServiceSupplier.objects.create(
            tenant_id=self.tenant.id, supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id="00000000-0000-0000-0000-000000000001",
            linked_entity_type="TestProfile", display_name="Test Supplier",
            status=SupplierStatus.ACTIVE, availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC,
        )
        self.person = Person.objects.create(tenant=self.tenant, full_name="Test User")
        self.user = UserAccount.objects.create_user(
            phone="09121111111", person=self.person, tenant=self.tenant,
        )

    def test_create_order_offer(self):
        offer = OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier,
            price_amount=Decimal("500000.00"), currency="IRR",
            submitted_by=self.user,
        )
        self.assertEqual(offer.status, OrderOfferStatus.SUBMITTED)
        self.assertEqual(offer.price_amount, Decimal("500000.00"))
        self.assertEqual(offer.currency, "IRR")
        self.assertIsNotNone(offer.created_at)
        self.assertIsNotNone(offer.updated_at)
        self.assertIsNone(offer.selected_by)
        self.assertIsNone(offer.selected_at)
        self.assertIsNone(offer.hold_expires_at)

    def test_uuid_primary_key(self):
        offer = OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier,
            price_amount=Decimal("100000.00"), submitted_by=self.user,
        )
        self.assertIsNotNone(offer.id)
        self.assertEqual(len(str(offer.id)), 36)

    def test_str_representation(self):
        offer = OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
        )
        self.assertIn(str(self.order.id), str(offer))
        self.assertIn(str(self.supplier.id), str(offer))
        self.assertIn("submitted", str(offer))

    def test_default_values(self):
        offer = OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
        )
        self.assertEqual(offer.currency, "IRR")
        self.assertEqual(offer.status, OrderOfferStatus.SUBMITTED)
        self.assertIsNone(offer.estimated_duration_minutes)
        self.assertEqual(offer.terms, "")
        self.assertEqual(offer.message, "")


class OrderOfferStatusTest(TestCase):
    """Status enum and property tests."""

    def setUp(self):
        self.tenant, _ = Tenant.objects.get_or_create(
            slug="status-test", defaults={"name": "Status Test Tenant"}
        )
        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )
        self.order = Order.objects.create(
            tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category, description="Test order",
            city="tehran", address="Test address", phone="09120000000",
        )
        self.supplier = ServiceSupplier.objects.create(
            tenant_id=self.tenant.id, supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id="00000000-0000-0000-0000-000000000002",
            linked_entity_type="TestProfile", display_name="Test Supplier 2",
            status=SupplierStatus.ACTIVE, availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC,
        )
        self.person = Person.objects.create(tenant=self.tenant, full_name="Status User")
        self.user = UserAccount.objects.create_user(
            phone="09122222222", person=self.person, tenant=self.tenant,
        )

    def test_all_statuses_exist(self):
        self.assertEqual(OrderOfferStatus.SUBMITTED, "submitted")
        self.assertEqual(OrderOfferStatus.SELECTED, "selected")
        self.assertEqual(OrderOfferStatus.ACCEPTED, "accepted")
        self.assertEqual(OrderOfferStatus.EXPIRED, "expired")
        self.assertEqual(OrderOfferStatus.WITHDRAWN, "withdrawn")
        self.assertEqual(OrderOfferStatus.REJECTED, "rejected")
        self.assertEqual(OrderOfferStatus.CANCELLED, "cancelled")

    def test_terminal_statuses(self):
        for status in OrderOfferStatus:
            if status in OFFER_TERMINAL_STATUSES:
                self.assertIn(status, OFFER_TERMINAL_STATUSES)
            else:
                self.assertNotIn(status, OFFER_TERMINAL_STATUSES)

    def test_is_terminal_property(self):
        offer = OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
        )
        self.assertFalse(offer.is_terminal)
        offer.status = OrderOfferStatus.ACCEPTED
        offer.save(update_fields=["status"])
        offer.refresh_from_db()
        self.assertTrue(offer.is_terminal)

    def test_is_active_property(self):
        offer = OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
        )
        self.assertTrue(offer.is_active)
        offer.status = OrderOfferStatus.SELECTED
        offer.save(update_fields=["status"])
        self.assertTrue(offer.is_active)
        offer.status = OrderOfferStatus.ACCEPTED
        offer.save(update_fields=["status"])
        self.assertFalse(offer.is_active)

    def test_hold_active_property_not_selected(self):
        offer = OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
        )
        self.assertFalse(offer.hold_active)

    def test_hold_active_property_selected_no_expiry(self):
        offer = OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
            status=OrderOfferStatus.SELECTED,
        )
        self.assertFalse(offer.hold_active)

    def test_hold_active_property_selected_with_future_expiry(self):
        offer = OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
            status=OrderOfferStatus.SELECTED,
            hold_expires_at=timezone.now() + timezone.timedelta(minutes=30),
        )
        self.assertTrue(offer.hold_active)

    def test_hold_active_property_selected_with_past_expiry(self):
        offer = OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
            status=OrderOfferStatus.SELECTED,
            hold_expires_at=timezone.now() - timezone.timedelta(minutes=1),
        )
        self.assertFalse(offer.hold_active)


class OrderOfferDomainPropertyTest(TestCase):
    """Tests for can_edit, can_withdraw, can_select domain properties."""

    def setUp(self):
        self.tenant, _ = Tenant.objects.get_or_create(
            slug="prop-test", defaults={"name": "Property Test Tenant"}
        )
        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )
        self.order = Order.objects.create(
            tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category, description="Test order",
            city="tehran", address="Test address", phone="09120000000",
        )
        self.supplier = ServiceSupplier.objects.create(
            tenant_id=self.tenant.id, supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id="00000000-0000-0000-0000-000000000010",
            linked_entity_type="TestProfile", display_name="Property Supplier",
            status=SupplierStatus.ACTIVE, availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC,
        )
        self.person = Person.objects.create(tenant=self.tenant, full_name="Property User")
        self.user = UserAccount.objects.create_user(
            phone="09126666666", person=self.person, tenant=self.tenant,
        )

    def _make_offer(self, status):
        return OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
            status=status,
        )

    def test_can_edit_submitted(self):
        offer = self._make_offer(OrderOfferStatus.SUBMITTED)
        self.assertTrue(offer.can_edit)

    def test_can_withdraw_submitted(self):
        offer = self._make_offer(OrderOfferStatus.SUBMITTED)
        self.assertTrue(offer.can_withdraw)

    def test_can_select_submitted(self):
        offer = self._make_offer(OrderOfferStatus.SUBMITTED)
        self.assertTrue(offer.can_select)

    def test_can_edit_selected(self):
        offer = self._make_offer(OrderOfferStatus.SELECTED)
        self.assertFalse(offer.can_edit)

    def test_can_withdraw_selected(self):
        offer = self._make_offer(OrderOfferStatus.SELECTED)
        self.assertFalse(offer.can_withdraw)

    def test_can_select_selected(self):
        offer = self._make_offer(OrderOfferStatus.SELECTED)
        self.assertFalse(offer.can_select)

    def test_can_edit_accepted(self):
        offer = self._make_offer(OrderOfferStatus.ACCEPTED)
        self.assertFalse(offer.can_edit)
        self.assertFalse(offer.can_withdraw)
        self.assertFalse(offer.can_select)

    def test_can_edit_expired(self):
        offer = self._make_offer(OrderOfferStatus.EXPIRED)
        self.assertFalse(offer.can_edit)
        self.assertFalse(offer.can_withdraw)
        self.assertFalse(offer.can_select)

    def test_can_edit_withdrawn(self):
        offer = self._make_offer(OrderOfferStatus.WITHDRAWN)
        self.assertFalse(offer.can_edit)
        self.assertFalse(offer.can_withdraw)
        self.assertFalse(offer.can_select)

    def test_can_edit_rejected(self):
        offer = self._make_offer(OrderOfferStatus.REJECTED)
        self.assertFalse(offer.can_edit)
        self.assertFalse(offer.can_withdraw)
        self.assertFalse(offer.can_select)

    def test_can_edit_cancelled(self):
        offer = self._make_offer(OrderOfferStatus.CANCELLED)
        self.assertFalse(offer.can_edit)
        self.assertFalse(offer.can_withdraw)
        self.assertFalse(offer.can_select)


class OrderOfferUniquenessTest(TestCase):
    """Database constraint tests — requires PostgreSQL."""

    def setUp(self):
        self.tenant, _ = Tenant.objects.get_or_create(
            slug="unique-test", defaults={"name": "Unique Test Tenant"}
        )
        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )
        self.order = Order.objects.create(
            tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category, description="Test order",
            city="tehran", address="Test address", phone="09120000000",
        )
        self.supplier_a = ServiceSupplier.objects.create(
            tenant_id=self.tenant.id, supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id="00000000-0000-0000-0000-000000000003",
            linked_entity_type="TestProfile", display_name="Supplier A",
            status=SupplierStatus.ACTIVE, availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC,
        )
        self.supplier_b = ServiceSupplier.objects.create(
            tenant_id=self.tenant.id, supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id="00000000-0000-0000-0000-000000000004",
            linked_entity_type="TestProfile", display_name="Supplier B",
            status=SupplierStatus.ACTIVE, availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC,
        )
        self.person = Person.objects.create(tenant=self.tenant, full_name="Unique User")
        self.user = UserAccount.objects.create_user(
            phone="09123333333", person=self.person, tenant=self.tenant,
        )

    def test_one_offer_per_supplier_canonical(self):
        """Only one offer per (order, supplier) — regardless of status."""
        OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier_a,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
        )
        with self.assertRaises(IntegrityError):
            OrderOffer.objects.create(
                tenant=self.tenant, order=self.order, supplier=self.supplier_a,
                price_amount=Decimal("600000.00"), submitted_by=self.user,
            )

    def test_submitted_prevents_second_offer(self):
        """SUBMITTED offer prevents second offer from same supplier."""
        OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier_a,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
            status=OrderOfferStatus.SUBMITTED,
        )
        with self.assertRaises(IntegrityError):
            OrderOffer.objects.create(
                tenant=self.tenant, order=self.order, supplier=self.supplier_a,
                price_amount=Decimal("600000.00"), submitted_by=self.user,
                status=OrderOfferStatus.SUBMITTED,
            )

    def test_selected_prevents_second_offer(self):
        """SELECTED offer prevents second offer from same supplier."""
        OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier_a,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
            status=OrderOfferStatus.SELECTED,
        )
        with self.assertRaises(IntegrityError):
            OrderOffer.objects.create(
                tenant=self.tenant, order=self.order, supplier=self.supplier_a,
                price_amount=Decimal("600000.00"), submitted_by=self.user,
                status=OrderOfferStatus.SUBMITTED,
            )

    def test_accepted_prevents_second_offer(self):
        """ACCEPTED offer prevents second offer from same supplier."""
        OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier_a,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
            status=OrderOfferStatus.ACCEPTED,
        )
        with self.assertRaises(IntegrityError):
            OrderOffer.objects.create(
                tenant=self.tenant, order=self.order, supplier=self.supplier_a,
                price_amount=Decimal("600000.00"), submitted_by=self.user,
                status=OrderOfferStatus.SUBMITTED,
            )

    def test_expired_prevents_second_offer(self):
        """EXPIRED offer prevents second offer from same supplier."""
        OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier_a,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
            status=OrderOfferStatus.EXPIRED,
        )
        with self.assertRaises(IntegrityError):
            OrderOffer.objects.create(
                tenant=self.tenant, order=self.order, supplier=self.supplier_a,
                price_amount=Decimal("600000.00"), submitted_by=self.user,
                status=OrderOfferStatus.SUBMITTED,
            )

    def test_withdrawn_prevents_second_offer(self):
        """WITHDRAWN offer prevents second offer from same supplier."""
        OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier_a,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
            status=OrderOfferStatus.WITHDRAWN,
        )
        with self.assertRaises(IntegrityError):
            OrderOffer.objects.create(
                tenant=self.tenant, order=self.order, supplier=self.supplier_a,
                price_amount=Decimal("600000.00"), submitted_by=self.user,
                status=OrderOfferStatus.SUBMITTED,
            )

    def test_rejected_prevents_second_offer(self):
        """REJECTED offer prevents second offer from same supplier."""
        OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier_a,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
            status=OrderOfferStatus.REJECTED,
        )
        with self.assertRaises(IntegrityError):
            OrderOffer.objects.create(
                tenant=self.tenant, order=self.order, supplier=self.supplier_a,
                price_amount=Decimal("600000.00"), submitted_by=self.user,
                status=OrderOfferStatus.SUBMITTED,
            )

    def test_cancelled_prevents_second_offer(self):
        """CANCELLED offer prevents second offer from same supplier."""
        OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier_a,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
            status=OrderOfferStatus.CANCELLED,
        )
        with self.assertRaises(IntegrityError):
            OrderOffer.objects.create(
                tenant=self.tenant, order=self.order, supplier=self.supplier_a,
                price_amount=Decimal("600000.00"), submitted_by=self.user,
                status=OrderOfferStatus.SUBMITTED,
            )

    def test_different_suppliers_can_submit(self):
        """Two offers from different suppliers on same order is allowed."""
        OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier_a,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
        )
        offer_b = OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier_b,
            price_amount=Decimal("600000.00"), submitted_by=self.user,
        )
        self.assertIsNotNone(offer_b.id)

    def test_same_supplier_different_orders_allowed(self):
        """Same supplier on different orders is allowed."""
        order2 = Order.objects.create(
            tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category, description="Second order",
            city="tehran", address="Test address 2", phone="09120000001",
        )
        OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier_a,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
        )
        offer2 = OrderOffer.objects.create(
            tenant=self.tenant, order=order2, supplier=self.supplier_a,
            price_amount=Decimal("700000.00"), submitted_by=self.user,
        )
        self.assertIsNotNone(offer2.id)

    def test_one_selected_per_order(self):
        """Two SELECTED offers on same order violates constraint."""
        OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier_a,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
            status=OrderOfferStatus.SELECTED,
            hold_expires_at=timezone.now() + timezone.timedelta(minutes=30),
        )
        with self.assertRaises(IntegrityError):
            OrderOffer.objects.create(
                tenant=self.tenant, order=self.order, supplier=self.supplier_b,
                price_amount=Decimal("600000.00"), submitted_by=self.user,
                status=OrderOfferStatus.SELECTED,
                hold_expires_at=timezone.now() + timezone.timedelta(minutes=30),
            )

    def test_selected_plus_submitted_allowed(self):
        """One SELECTED and one SUBMITTED on same order is allowed."""
        OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier_a,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
            status=OrderOfferStatus.SELECTED,
            hold_expires_at=timezone.now() + timezone.timedelta(minutes=30),
        )
        offer_b = OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier_b,
            price_amount=Decimal("600000.00"), submitted_by=self.user,
        )
        self.assertEqual(offer_b.status, OrderOfferStatus.SUBMITTED)

    def test_different_suppliers_each_get_one_offer(self):
        """Different suppliers can each have one offer on the same order."""
        offer_a = OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier_a,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
            status=OrderOfferStatus.ACCEPTED,
        )
        offer_b = OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier_b,
            price_amount=Decimal("600000.00"), submitted_by=self.user,
            status=OrderOfferStatus.REJECTED,
        )
        self.assertIsNotNone(offer_a.id)
        self.assertIsNotNone(offer_b.id)


class OrderOfferTenantIsolationTest(TestCase):
    """Tenant isolation tests."""

    def setUp(self):
        self.tenant_a, _ = Tenant.objects.get_or_create(
            slug="tenant-a", defaults={"name": "Tenant A"}
        )
        self.tenant_b, _ = Tenant.objects.get_or_create(
            slug="tenant-b", defaults={"name": "Tenant B"}
        )
        self.category_a = ServiceCategory.objects.create(
            tenant=self.tenant_a, name="Home Care A", slug="home-care-a", status=CatalogStatus.ACTIVE,
        )
        self.category_b = ServiceCategory.objects.create(
            tenant=self.tenant_b, name="Home Care B", slug="home-care-b", status=CatalogStatus.ACTIVE,
        )
        self.order_a = Order.objects.create(
            tenant=self.tenant_a, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category_a, description="Order A",
            city="tehran", address="Address A", phone="09120000001",
        )
        self.order_b = Order.objects.create(
            tenant=self.tenant_b, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category_b, description="Order B",
            city="shiraz", address="Address B", phone="09120000002",
        )
        self.supplier_a = ServiceSupplier.objects.create(
            tenant_id=self.tenant_a.id, supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id="00000000-0000-0000-0000-000000000005",
            linked_entity_type="TestProfile", display_name="Supplier A",
            status=SupplierStatus.ACTIVE, availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC,
        )
        self.supplier_b = ServiceSupplier.objects.create(
            tenant_id=self.tenant_b.id, supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id="00000000-0000-0000-0000-000000000006",
            linked_entity_type="TestProfile", display_name="Supplier B",
            status=SupplierStatus.ACTIVE, availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC,
        )
        self.person_a = Person.objects.create(tenant=self.tenant_a, full_name="User A")
        self.user_a = UserAccount.objects.create_user(
            phone="09124444444", person=self.person_a, tenant=self.tenant_a,
        )

    def test_tenant_scoped_manager_filters(self):
        """TenantScopedManager.for_tenant() filters offers correctly."""
        offer_a = OrderOffer.objects.create(
            tenant=self.tenant_a, order=self.order_a, supplier=self.supplier_a,
            price_amount=Decimal("500000.00"), submitted_by=self.user_a,
        )
        offer_b = OrderOffer.objects.create(
            tenant=self.tenant_b, order=self.order_b, supplier=self.supplier_b,
            price_amount=Decimal("600000.00"), submitted_by=self.user_a,
        )
        tenant_a_offers = OrderOffer.objects.for_tenant(self.tenant_a.id)
        self.assertIn(offer_a, list(tenant_a_offers))
        self.assertNotIn(offer_b, list(tenant_a_offers))


class OrderOfferTimestampTest(TestCase):
    """Timestamp behavior tests."""

    def setUp(self):
        self.tenant, _ = Tenant.objects.get_or_create(
            slug="timestamp-test", defaults={"name": "Timestamp Test Tenant"}
        )
        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug="home-care", status=CatalogStatus.ACTIVE,
        )
        self.order = Order.objects.create(
            tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category, description="Test order",
            city="tehran", address="Test address", phone="09120000000",
        )
        self.supplier = ServiceSupplier.objects.create(
            tenant_id=self.tenant.id, supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id="00000000-0000-0000-0000-000000000007",
            linked_entity_type="TestProfile", display_name="Timestamp Supplier",
            status=SupplierStatus.ACTIVE, availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC,
        )
        self.person = Person.objects.create(tenant=self.tenant, full_name="Timestamp User")
        self.user = UserAccount.objects.create_user(
            phone="09125555555", person=self.person, tenant=self.tenant,
        )

    def test_created_at_auto_set(self):
        offer = OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
        )
        self.assertIsNotNone(offer.created_at)

    def test_updated_at_auto_set(self):
        offer = OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
        )
        old_updated = offer.updated_at
        offer.price_amount = Decimal("600000.00")
        offer.save(update_fields=["price_amount"])
        offer.refresh_from_db()
        self.assertGreaterEqual(offer.updated_at, old_updated)

    def test_created_at_immutable(self):
        """created_at should not change on update."""
        offer = OrderOffer.objects.create(
            tenant=self.tenant, order=self.order, supplier=self.supplier,
            price_amount=Decimal("500000.00"), submitted_by=self.user,
        )
        old_created = offer.created_at
        offer.price_amount = Decimal("600000.00")
        offer.save(update_fields=["price_amount"])
        offer.refresh_from_db()
        self.assertEqual(offer.created_at, old_created)
