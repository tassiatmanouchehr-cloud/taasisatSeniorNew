"""Tests for OrderShareLink / OrderShareLinkService — Customer Experience Phase 1 Phase 6."""

import uuid

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import CustomerProfile
from apps.kernel.models import Person, Tenant, UserAccount
from apps.orders.models import CatalogStatus, Order, OrderShareLink, OrderSource, OrderStatus, ServiceCategory
from apps.orders.services.share_links import OrderShareLinkError, OrderShareLinkService


class ShareLinkTestCase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"share-{uuid.uuid4().hex[:8]}", name="Share Test Tenant")
        self.category = ServiceCategory.objects.create(
            tenant=self.tenant,
            name="Home Care",
            slug="home-care",
            status=CatalogStatus.ACTIVE,
        )
        person = Person.objects.create(tenant=self.tenant, full_name="Customer")
        self.user = UserAccount.objects.create_user(phone="09120000010", person=person, tenant=self.tenant)
        self.customer = CustomerProfile.objects.create(
            user=self.user,
            person=person,
            phone="09120000010",
            display_name="Customer",
        )
        self.order = Order.objects.create(
            tenant=self.tenant,
            source=OrderSource.PUBLIC,
            status=OrderStatus.PENDING_OPERATOR_REVIEW,
            service_category=self.category,
            customer_profile=self.customer,
            description="Need home care",
            city="tehran",
            address="Some address",
            phone="09120000010",
        )


class CreateShareLinkTest(ShareLinkTestCase):
    def test_create_generates_unique_token(self):
        link = OrderShareLinkService.create(order=self.order, created_by=self.user)
        self.assertTrue(link.token)
        self.assertEqual(link.order_id, self.order.id)
        self.assertEqual(link.tenant_id, self.tenant.id)

    def test_create_defaults_to_14_day_validity(self):
        before = timezone.now()
        link = OrderShareLinkService.create(order=self.order)
        self.assertGreater(link.expires_at, before + timezone.timedelta(days=13))
        self.assertLess(link.expires_at, before + timezone.timedelta(days=15))

    def test_two_links_for_same_order_have_different_tokens(self):
        link1 = OrderShareLinkService.create(order=self.order)
        link2 = OrderShareLinkService.create(order=self.order)
        self.assertNotEqual(link1.token, link2.token)


class ResolveShareLinkTest(ShareLinkTestCase):
    def test_resolve_returns_the_order_for_a_valid_token(self):
        link = OrderShareLinkService.create(order=self.order)
        resolved = OrderShareLinkService.resolve(link.token)
        self.assertEqual(resolved.id, self.order.id)

    def test_resolve_records_access(self):
        link = OrderShareLinkService.create(order=self.order)
        OrderShareLinkService.resolve(link.token)
        link.refresh_from_db()
        self.assertEqual(link.access_count, 1)
        self.assertIsNotNone(link.last_accessed_at)

    def test_repeated_resolves_increment_access_count_atomically(self):
        """record_access() uses F("access_count") + 1 (a DB-level atomic
        increment), not a Python read-modify-write — this covers the
        sequential case; the point of F() is safety under concurrent access,
        which a single-process unit test can't directly exercise."""
        link = OrderShareLinkService.create(order=self.order)
        for _ in range(3):
            OrderShareLinkService.resolve(link.token)
        link.refresh_from_db()
        self.assertEqual(link.access_count, 3)

    def test_resolve_raises_for_unknown_token(self):
        with self.assertRaises(OrderShareLinkError):
            OrderShareLinkService.resolve("does-not-exist")

    def test_resolve_raises_for_expired_token(self):
        link = OrderShareLinkService.create(order=self.order, valid_for=timezone.timedelta(seconds=-1))
        with self.assertRaises(OrderShareLinkError):
            OrderShareLinkService.resolve(link.token)

    def test_resolve_raises_for_revoked_token(self):
        link = OrderShareLinkService.create(order=self.order)
        link.revoke()
        with self.assertRaises(OrderShareLinkError):
            OrderShareLinkService.resolve(link.token)


class RevokeShareLinkTest(ShareLinkTestCase):
    def test_revoke_marks_link_as_revoked(self):
        link = OrderShareLinkService.create(order=self.order)
        OrderShareLinkService.revoke(order=self.order, link_id=link.id)
        link.refresh_from_db()
        self.assertIsNotNone(link.revoked_at)

    def test_revoke_raises_for_unknown_link(self):
        with self.assertRaises(OrderShareLinkError):
            OrderShareLinkService.revoke(order=self.order, link_id=uuid.uuid4())

    def test_revoke_is_scoped_to_the_given_order(self):
        other_order = Order.objects.create(
            tenant=self.tenant,
            source=OrderSource.PUBLIC,
            status=OrderStatus.PENDING_OPERATOR_REVIEW,
            service_category=self.category,
            customer_profile=self.customer,
            description="Other",
            city="tehran",
            address="Other address",
            phone="09120000010",
        )
        link = OrderShareLinkService.create(order=self.order)
        with self.assertRaises(OrderShareLinkError):
            OrderShareLinkService.revoke(order=other_order, link_id=link.id)


class ShareLinkEventPublishingTest(ShareLinkTestCase):
    """Customer Experience Phase 1 remediation: create/revoke/resolve each
    publish a DomainEvent, which unconditionally writes an AuditLog row
    (apps.kernel.events.publisher.publish) — verified end to end here
    rather than assumed. transaction.on_commit() callbacks never fire
    inside TestCase's default rollback-wrapped transaction, so each
    assertion runs inside captureOnCommitCallbacks(execute=True)."""

    def test_create_publishes_share_link_created_and_is_audited(self):
        from apps.kernel.models.audit import AuditLog

        with self.captureOnCommitCallbacks(execute=True):
            link = OrderShareLinkService.create(order=self.order, created_by=self.user)

        entry = AuditLog.objects.get(action="domain_event.ShareLinkCreated", resource_id=link.id)
        self.assertEqual(entry.resource_type, "OrderShareLink")
        self.assertEqual(entry.tenant_id, self.tenant.id)
        self.assertEqual(entry.actor_id, self.user.person_id)

    def test_create_without_created_by_has_no_actor(self):
        from apps.kernel.models.audit import AuditLog

        with self.captureOnCommitCallbacks(execute=True):
            link = OrderShareLinkService.create(order=self.order)

        entry = AuditLog.objects.get(action="domain_event.ShareLinkCreated", resource_id=link.id)
        self.assertIsNone(entry.actor_id)

    def test_resolve_publishes_share_link_accessed_and_is_audited(self):
        from apps.kernel.models.audit import AuditLog

        with self.captureOnCommitCallbacks(execute=True):
            link = OrderShareLinkService.create(order=self.order)
        with self.captureOnCommitCallbacks(execute=True):
            OrderShareLinkService.resolve(link.token)

        entry = AuditLog.objects.get(action="domain_event.ShareLinkAccessed", resource_id=link.id)
        self.assertEqual(entry.resource_type, "OrderShareLink")

    def test_revoke_publishes_share_link_revoked_and_is_audited(self):
        from apps.kernel.models.audit import AuditLog

        with self.captureOnCommitCallbacks(execute=True):
            link = OrderShareLinkService.create(order=self.order)
        with self.captureOnCommitCallbacks(execute=True):
            OrderShareLinkService.revoke(order=self.order, link_id=link.id, revoked_by=self.user)

        entry = AuditLog.objects.get(action="domain_event.ShareLinkRevoked", resource_id=link.id)
        self.assertEqual(entry.actor_id, self.user.person_id)


class ShareLinkModelTest(ShareLinkTestCase):
    def test_is_valid_true_for_fresh_link(self):
        link = OrderShareLinkService.create(order=self.order)
        self.assertTrue(link.is_valid())

    def test_is_valid_false_after_revoke(self):
        link = OrderShareLinkService.create(order=self.order)
        link.revoke()
        self.assertFalse(link.is_valid())

    def test_share_link_cascades_on_order_delete(self):
        link = OrderShareLinkService.create(order=self.order)
        link_id = link.id
        self.order.delete()
        self.assertFalse(OrderShareLink.objects.filter(id=link_id).exists())
