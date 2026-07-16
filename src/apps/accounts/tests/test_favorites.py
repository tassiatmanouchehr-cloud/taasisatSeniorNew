"""Favorite / FavoritesService — Phase 4 Sprint 4.1 (Customer Favorites
and Saved Providers).

Mirrors test_caregiver_gallery.py's fixture-mixin shape: an isolated
tenant, a customer, and a real ServiceSupplier created through the
sanctioned supplier_bridge (never a bare CaregiverProfile/OrganizationProfile
passed to FavoritesService — the domain contract targets kernel.ServiceSupplier
only, per apps.kernel.tests.test_architecture_guardrails
.ServiceSupplierProfileCouplingTest)."""

import uuid

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import CustomerProfile
from apps.accounts.models.favorites import Favorite
from apps.accounts.models.profiles import CaregiverProfile
from apps.accounts.services.errors import AccountsError
from apps.accounts.services.favorites import FavoritesService
from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_caregiver
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.supplier import SupplierStatus


class _FixtureMixin:
    def _build_fixture(self):
        self.tenant = Tenant.objects.create(slug=f"fav-{uuid.uuid4().hex[:8]}", name="Favorites Tenant")
        self.other_tenant = Tenant.objects.create(slug=f"fav-other-{uuid.uuid4().hex[:8]}", name="Other Tenant")

        self.customer = self._create_customer(tenant=self.tenant, display_name="Customer One")
        self.other_customer = self._create_customer(tenant=self.tenant, display_name="Customer Two")

        self.supplier, self.caregiver = self._create_caregiver_supplier(tenant=self.tenant)
        self.other_tenant_supplier, _ = self._create_caregiver_supplier(
            tenant=self.other_tenant, display_name="Cross Tenant Caregiver",
        )

    def _create_customer(self, *, tenant, display_name) -> CustomerProfile:
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=display_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        return CustomerProfile.objects.create(user=user, person=person, phone=phone, display_name=display_name)

    def _create_caregiver_supplier(self, *, tenant, display_name="Test Caregiver"):
        phone = f"0913{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=tenant, full_name=display_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        caregiver = CaregiverProfile.objects.create(user=user, person=person, phone=phone, display_name=display_name)
        supplier = get_or_create_supplier_for_caregiver(caregiver, tenant_id=tenant.id)
        supplier.status = SupplierStatus.ACTIVE
        supplier.save(update_fields=["status"])
        return supplier, caregiver


class FavoriteModelConstraintTest(_FixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_unique_constraint_prevents_duplicate_row(self):
        Favorite.objects.create(customer_profile=self.customer, supplier=self.supplier)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Favorite.objects.create(customer_profile=self.customer, supplier=self.supplier)

    def test_same_supplier_can_be_favorited_by_different_customers(self):
        Favorite.objects.create(customer_profile=self.customer, supplier=self.supplier)
        Favorite.objects.create(customer_profile=self.other_customer, supplier=self.supplier)
        self.assertEqual(Favorite.objects.filter(supplier=self.supplier).count(), 2)

    def test_customer_deletion_cascades_to_favorite(self):
        Favorite.objects.create(customer_profile=self.customer, supplier=self.supplier)
        self.customer.user.delete()
        self.assertEqual(Favorite.objects.filter(supplier=self.supplier).count(), 0)

    def test_supplier_deletion_cascades_to_favorite(self):
        Favorite.objects.create(customer_profile=self.customer, supplier=self.supplier)
        self.supplier.delete()
        self.assertEqual(Favorite.objects.filter(customer_profile=self.customer).count(), 0)

    def test_default_ordering_is_newest_first(self):
        first = Favorite.objects.create(customer_profile=self.customer, supplier=self.supplier)
        second_supplier, _ = self._create_caregiver_supplier(tenant=self.tenant, display_name="Second Caregiver")
        second = Favorite.objects.create(customer_profile=self.customer, supplier=second_supplier)
        ordered = list(Favorite.objects.filter(customer_profile=self.customer))
        self.assertEqual([row.id for row in ordered], [second.id, first.id])


class FavoritesServiceAddTest(_FixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_add_favorite_creates_row(self):
        favorite = FavoritesService.add_favorite(self.customer, supplier_id=self.supplier.id, tenant_id=self.tenant.id)
        self.assertEqual(favorite.customer_profile_id, self.customer.id)
        self.assertEqual(favorite.supplier_id, self.supplier.id)

    def test_duplicate_add_is_idempotent(self):
        first = FavoritesService.add_favorite(self.customer, supplier_id=self.supplier.id, tenant_id=self.tenant.id)
        second = FavoritesService.add_favorite(self.customer, supplier_id=self.supplier.id, tenant_id=self.tenant.id)
        self.assertEqual(first.id, second.id)
        self.assertEqual(Favorite.objects.filter(customer_profile=self.customer).count(), 1)

    def test_add_favorite_survives_integrity_error_race(self):
        """Simulates a raced concurrent double-add: get_or_create() itself
        raises IntegrityError past its own internal retry (the doc-required
        'do not assume get_or_create() alone is sufficient' scenario) —
        the service must still resolve to the single existing row rather
        than propagate the exception."""
        from unittest import mock

        Favorite.objects.create(customer_profile=self.customer, supplier=self.supplier)
        with mock.patch(
            "apps.accounts.services.favorites.Favorite.objects.get_or_create",
            side_effect=IntegrityError("simulated race"),
        ):
            favorite = FavoritesService.add_favorite(
                self.customer, supplier_id=self.supplier.id, tenant_id=self.tenant.id,
            )
        self.assertEqual(Favorite.objects.filter(customer_profile=self.customer).count(), 1)
        self.assertEqual(favorite.supplier_id, self.supplier.id)

    def test_add_favorite_for_unknown_supplier_raises(self):
        with self.assertRaises(AccountsError):
            FavoritesService.add_favorite(self.customer, supplier_id=uuid.uuid4(), tenant_id=self.tenant.id)

    def test_add_favorite_for_wrong_tenant_supplier_raises(self):
        with self.assertRaises(AccountsError):
            FavoritesService.add_favorite(
                self.customer, supplier_id=self.other_tenant_supplier.id, tenant_id=self.tenant.id,
            )
        self.assertEqual(Favorite.objects.filter(customer_profile=self.customer).count(), 0)

    def test_add_favorite_for_inactive_supplier_raises(self):
        self.supplier.status = SupplierStatus.SUSPENDED
        self.supplier.save(update_fields=["status"])
        with self.assertRaises(AccountsError):
            FavoritesService.add_favorite(self.customer, supplier_id=self.supplier.id, tenant_id=self.tenant.id)


class FavoritesServiceRemoveTest(_FixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_remove_favorite_deletes_row(self):
        FavoritesService.add_favorite(self.customer, supplier_id=self.supplier.id, tenant_id=self.tenant.id)
        FavoritesService.remove_favorite(self.customer, supplier_id=self.supplier.id)
        self.assertEqual(Favorite.objects.filter(customer_profile=self.customer).count(), 0)

    def test_repeated_remove_is_idempotent(self):
        FavoritesService.add_favorite(self.customer, supplier_id=self.supplier.id, tenant_id=self.tenant.id)
        FavoritesService.remove_favorite(self.customer, supplier_id=self.supplier.id)
        FavoritesService.remove_favorite(self.customer, supplier_id=self.supplier.id)  # must not raise
        self.assertEqual(Favorite.objects.filter(customer_profile=self.customer).count(), 0)

    def test_remove_of_never_favorited_supplier_is_a_noop(self):
        FavoritesService.remove_favorite(self.customer, supplier_id=self.supplier.id)  # must not raise
        self.assertEqual(Favorite.objects.filter(customer_profile=self.customer).count(), 0)

    def test_cannot_remove_another_customers_favorite(self):
        FavoritesService.add_favorite(self.customer, supplier_id=self.supplier.id, tenant_id=self.tenant.id)
        FavoritesService.remove_favorite(self.other_customer, supplier_id=self.supplier.id)
        self.assertEqual(Favorite.objects.filter(customer_profile=self.customer).count(), 1)


class FavoritesServiceReadTest(_FixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_is_favorited_true_after_add(self):
        FavoritesService.add_favorite(self.customer, supplier_id=self.supplier.id, tenant_id=self.tenant.id)
        self.assertTrue(FavoritesService.is_favorited(self.customer, supplier_id=self.supplier.id))

    def test_is_favorited_false_when_never_added(self):
        self.assertFalse(FavoritesService.is_favorited(self.customer, supplier_id=self.supplier.id))

    def test_is_favorited_is_scoped_to_the_caller(self):
        FavoritesService.add_favorite(self.customer, supplier_id=self.supplier.id, tenant_id=self.tenant.id)
        self.assertFalse(FavoritesService.is_favorited(self.other_customer, supplier_id=self.supplier.id))

    def test_list_favorites_for_customer_returns_only_own_rows_newest_first(self):
        second_supplier, _ = self._create_caregiver_supplier(tenant=self.tenant, display_name="Second Caregiver")
        FavoritesService.add_favorite(self.customer, supplier_id=self.supplier.id, tenant_id=self.tenant.id)
        FavoritesService.add_favorite(self.customer, supplier_id=second_supplier.id, tenant_id=self.tenant.id)
        FavoritesService.add_favorite(self.other_customer, supplier_id=self.supplier.id, tenant_id=self.tenant.id)

        favorites = list(FavoritesService.list_favorites_for_customer(self.customer))
        self.assertEqual([f.supplier_id for f in favorites], [second_supplier.id, self.supplier.id])

    def test_list_favorites_select_related_avoids_extra_supplier_query(self):
        FavoritesService.add_favorite(self.customer, supplier_id=self.supplier.id, tenant_id=self.tenant.id)
        favorites = list(FavoritesService.list_favorites_for_customer(self.customer))
        with self.assertNumQueries(0):
            _ = favorites[0].supplier.display_name
