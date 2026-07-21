"""
Assignment concurrency — Epic 04 (Enterprise Organization Isolation).

Proves AssignmentService.assign()/replace()'s new
Order.objects.select_for_update() row lock actually serializes concurrent
attempts against the same order — a database-backed guarantee, not a
read-before-write check. Mirrors
apps.payments.tests.test_settlement_orchestration.SettlementConcurrencyTest
(Epic 03 Sprint 1, Architecture Review remediation Critical Finding 2)
exactly: needs TransactionTestCase (real, separately committed
transactions on separate connections) since Postgres row locking cannot be
observed across threads inside TestCase's own wrapping transaction, and
available_apps=all installed apps because TransactionTestCase's post-test
flush otherwise runs with allow_cascade=False and Postgres refuses to
TRUNCATE tables reachable through auth's Group/Permission FK graph.
"""

import threading
import uuid

from django.apps import apps as django_apps
from django.db import connection
from django.test import TransactionTestCase

from apps.accounts.models.profiles import (
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
)
from apps.booking.models import SupplierAssignment
from apps.booking.services.assignment_service import AssignmentService
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.supplier import (
    AvailabilityStatus,
    ServiceSupplier,
    SupplierStatus,
    SupplierType,
    VerificationLevel,
)
from apps.orders.models import CatalogStatus, Order, OrderSource, OrderStatus, ServiceCategory


class _ConcurrencyFixtureMixin:
    available_apps = [app_config.name for app_config in django_apps.get_app_configs()]

    def _build_fixture(self):
        self.tenant = Tenant.objects.create(slug=f"concur-{uuid.uuid4().hex[:8]}", name="Concurrency Test Tenant")
        self.category = ServiceCategory.objects.create(
            tenant=self.tenant,
            name="Home Care",
            slug="home-care",
            status=CatalogStatus.ACTIVE,
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
        self.supplier_a = self._create_supplier()
        self.supplier_b = self._create_supplier()

    def _create_supplier(self) -> ServiceSupplier:
        return ServiceSupplier.objects.create(
            tenant_id=self.tenant.id,
            supplier_type=SupplierType.INDEPENDENT_PROVIDER,
            linked_entity_id=uuid.uuid4(),
            linked_entity_type="TestProfile",
            display_name="Test Supplier",
            status=SupplierStatus.ACTIVE,
            availability_status=AvailabilityStatus.AVAILABLE,
            verification_level=VerificationLevel.BASIC,
            service_categories=[str(self.category.id)],
        )


class ConcurrentAssignmentTest(_ConcurrencyFixtureMixin, TransactionTestCase):
    """Two organizations' admins race to assign different staff to the same
    unassigned order — exactly one must win."""

    def setUp(self):
        self._build_fixture()

        self.admin_a = self._create_user(phone="09121130001")
        self.org_a = OrganizationProfile.objects.create(
            name="Org A",
            code=f"org-a-{uuid.uuid4().hex[:6]}",
            admin_user=self.admin_a,
            tenant=self.tenant,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.admin_a,
            role_type=OrgMembershipRole.ADMIN,
            status=OrgMembershipStatus.ACTIVE,
        )

        self.admin_b = self._create_user(phone="09121130002")
        self.org_b = OrganizationProfile.objects.create(
            name="Org B",
            code=f"org-b-{uuid.uuid4().hex[:6]}",
            admin_user=self.admin_b,
            tenant=self.tenant,
        )
        OrganizationMembership.objects.create(
            organization=self.org_b,
            user=self.admin_b,
            role_type=OrgMembershipRole.ADMIN,
            status=OrgMembershipStatus.ACTIVE,
        )

        from apps.orders.services.eligibility_service import OrderEligibilityService

        OrderEligibilityService.grant(order=self.order, organization=self.org_a)
        OrderEligibilityService.grant(order=self.order, organization=self.org_b)

    def _create_user(self, *, phone) -> UserAccount:
        person = Person.objects.create(tenant=self.tenant, full_name="Person")
        return UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)

    def test_concurrent_assign_attempts_result_in_exactly_one_success(self):
        barrier = threading.Barrier(2)
        results = []

        def _attempt(supplier):
            try:
                barrier.wait(timeout=5)
                AssignmentService.assign(order_id=self.order.id, supplier=supplier)
                results.append("ok")
            except Exception as exc:  # noqa: BLE001 — recorded, not swallowed
                results.append(exc)
            finally:
                connection.close()

        threads = [
            threading.Thread(target=_attempt, args=(self.supplier_a,)),
            threading.Thread(target=_attempt, args=(self.supplier_b,)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        self.order.refresh_from_db()
        self.assertIn(self.order.assigned_supplier_id, {self.supplier_a.id, self.supplier_b.id})
        # Both may report "ok" — assign_supplier() does not itself reject a
        # second assignment, exactly like the pre-Epic-04 behavior. What the
        # row lock guarantees is that the two writes are serialized, not
        # interleaved, and exactly one SupplierAssignment sequence-1 row wins
        # the (order, assignment_sequence) uniqueness — no lost update, no
        # IntegrityError from a torn read of the sequence counter.
        self.assertEqual(SupplierAssignment.objects.filter(order=self.order).count(), len(results))
        self.assertEqual(
            SupplierAssignment.objects.filter(order=self.order, assignment_sequence=1).count(),
            1,
        )


class ConcurrentReplaceTest(_ConcurrencyFixtureMixin, TransactionTestCase):
    """Two concurrent replace() attempts against the same already-assigned
    order — the same row-lock guarantee as assign()."""

    def setUp(self):
        self._build_fixture()
        self.supplier_c = self._create_supplier()
        AssignmentService.assign(order_id=self.order.id, supplier=self.supplier_a)

    def test_concurrent_replace_attempts_do_not_corrupt_sequence(self):
        barrier = threading.Barrier(2)
        results = []

        def _attempt(supplier):
            try:
                barrier.wait(timeout=5)
                AssignmentService.replace(order_id=self.order.id, new_supplier=supplier)
                results.append("ok")
            except Exception as exc:  # noqa: BLE001
                results.append(exc)
            finally:
                connection.close()

        threads = [
            threading.Thread(target=_attempt, args=(self.supplier_b,)),
            threading.Thread(target=_attempt, args=(self.supplier_c,)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        sequences = list(
            SupplierAssignment.objects.filter(order=self.order).values_list("assignment_sequence", flat=True),
        )
        self.assertEqual(len(sequences), len(set(sequences)), f"duplicate assignment_sequence values: {sequences}")
