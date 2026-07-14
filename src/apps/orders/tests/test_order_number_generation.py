"""Order-number generation collision safety — BG-002 regression tests.

BG-002: `_generate_order_number()` draws a random per-day suffix, so two
same-day orders can collide; before the fix a collision surfaced as an
IntegrityError to the caller (the seed walkthrough failed this way both in
full regression and in isolation). The fix keeps the database unique
constraint as the arbiter and retries generation a bounded number of times
inside a savepoint. These tests force collisions deterministically by
patching the generator — never by relying on randomness.
"""

import threading
import uuid
from unittest import mock

from django.apps import apps as django_apps
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.kernel.models import Tenant
from apps.orders.models import (
    ORDER_NUMBER_MAX_ATTEMPTS,
    CatalogStatus,
    Order,
    OrderSource,
    OrderStatus,
    ServiceCategory,
    _generate_order_number,
)


def _unique_number():
    return f"ORD-00000000-{uuid.uuid4().hex[:6]}"


class _OrderFixtureMixin:
    def _build_fixture(self):
        self.tenant = Tenant.objects.create(
            slug=f"ordnum-{uuid.uuid4().hex[:8]}", name="Order Number Test Tenant"
        )
        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug=f"home-care-{uuid.uuid4().hex[:6]}",
            status=CatalogStatus.ACTIVE,
        )

    def _create_order(self):
        return Order.objects.create(
            tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
            service_category=self.category, description="Need home care",
            city="tehran", address="Some address", phone="09120000000",
        )


class OrderNumberGenerationTest(_OrderFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()

    def test_generated_number_matches_public_format(self):
        order = self._create_order()
        today = timezone.now().strftime("%Y%m%d")
        self.assertRegex(order.order_number, rf"^ORD-{today}-\d{{6}}$")

    def test_generator_output_matches_public_format(self):
        number = _generate_order_number()
        self.assertRegex(number, r"^ORD-\d{8}-\d{6}$")
        self.assertLessEqual(len(number), 30)  # CharField(max_length=30)

    def test_forced_collision_retries_to_unique_number(self):
        existing = self._create_order()
        fallback = _unique_number()
        with mock.patch(
            "apps.orders.models._generate_order_number",
            side_effect=[existing.order_number, fallback],
        ) as generator:
            order = self._create_order()
        self.assertEqual(order.order_number, fallback)
        self.assertEqual(generator.call_count, 2)

    def test_collision_does_not_overwrite_existing_order(self):
        existing = self._create_order()
        original_number = existing.order_number
        original_description = existing.description
        with mock.patch(
            "apps.orders.models._generate_order_number",
            side_effect=[original_number, _unique_number()],
        ):
            self._create_order()
        existing.refresh_from_db()
        self.assertEqual(existing.order_number, original_number)
        self.assertEqual(existing.description, original_description)
        self.assertEqual(Order.objects.count(), 2)

    def test_retry_is_bounded(self):
        existing = self._create_order()
        with mock.patch(
            "apps.orders.models._generate_order_number",
            return_value=existing.order_number,
        ) as generator:
            with self.assertRaises(IntegrityError):
                self._create_order()
        self.assertEqual(generator.call_count, ORDER_NUMBER_MAX_ATTEMPTS)
        self.assertEqual(Order.objects.count(), 1)

    def test_explicit_duplicate_number_is_never_retried(self):
        existing = self._create_order()
        with mock.patch("apps.orders.models._generate_order_number") as generator:
            with self.assertRaises(IntegrityError):
                Order.objects.create(
                    tenant=self.tenant, source=OrderSource.OPERATOR, status=OrderStatus.NEW,
                    service_category=self.category, description="dup",
                    city="tehran", address="Some address", phone="09120000000",
                    order_number=existing.order_number,
                )
        generator.assert_not_called()

    def test_collision_retry_does_not_poison_callers_atomic_block(self):
        # Order-creation services run inside @transaction.atomic; a rejected
        # insert must roll back only its own savepoint, leaving the caller's
        # transaction usable (the pre-fix behavior aborted it).
        existing = self._create_order()
        with transaction.atomic():
            with mock.patch(
                "apps.orders.models._generate_order_number",
                side_effect=[existing.order_number, _unique_number()],
            ):
                self._create_order()
            self.assertEqual(Order.objects.count(), 2)  # queries still work


class OrderNumberConcurrencyTest(_OrderFixtureMixin, TransactionTestCase):
    """Mirrors apps.booking.tests.test_concurrency: TransactionTestCase with
    real, separately committed transactions on separate connections, and
    available_apps=all installed apps so the post-test flush can TRUNCATE
    with cascade."""

    available_apps = [app_config.name for app_config in django_apps.get_app_configs()]

    def setUp(self):
        self._build_fixture()

    def test_concurrent_creation_with_forced_collision_yields_unique_numbers(self):
        duplicate = "ORD-00000000-000000"
        thread_state = threading.local()

        def _colliding_generator():
            # First draw in every thread is the same number; retries fall
            # back to unique values — forcing the cross-connection collision.
            if not getattr(thread_state, "collided", False):
                thread_state.collided = True
                return duplicate
            return _unique_number()

        barrier = threading.Barrier(2)
        errors = []

        def _attempt():
            try:
                barrier.wait(timeout=10)
                self._create_order()
            except Exception as exc:  # noqa: BLE001 — recorded for assertion
                errors.append(exc)
            finally:
                connection.close()

        with mock.patch(
            "apps.orders.models._generate_order_number",
            side_effect=_colliding_generator,
        ):
            threads = [threading.Thread(target=_attempt) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=30)

        self.assertEqual(errors, [])
        numbers = list(Order.objects.values_list("order_number", flat=True))
        self.assertEqual(len(numbers), 2)
        self.assertEqual(len(set(numbers)), 2, f"duplicate order numbers: {numbers}")
        self.assertIn(duplicate, numbers)
