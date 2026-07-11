"""Shared fixtures for Epic 06 (Marketplace Profiles & Discovery) tests.

Mirrors apps.discovery.tests.helpers.DiscoveryTestCase's own pattern: an
isolated per-test tenant (never the shared TenantService default), real
CaregiverProfile + ServiceSupplier rows created through the sanctioned
get_or_create_supplier_for_caregiver() bridge, with reviews/orders created
directly (test fixtures, not through the full order lifecycle — no
guardrail restricts direct Order/Review creation, unlike
OrderOrganizationEligibility)."""

import uuid

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models.profiles import (
    CaregiverProfile,
    CaregiverProviderType,
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
)
from apps.accounts.services.supplier_bridge import get_or_create_supplier_for_caregiver
from apps.kernel.models import Person, Tenant, UserAccount
from apps.kernel.models.supplier import AvailabilityStatus, SupplierStatus
from apps.orders.models import CatalogStatus, Order, OrderSource, OrderStatus, ServiceCategory
from apps.reviews.models import Review, ReviewModerationStatus
from apps.reviews.services.reputation_service import ReputationService


class PublicSiteTestCase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug=f"public-site-{uuid.uuid4().hex[:8]}", name="Public Site Test Tenant")
        self.category = ServiceCategory.objects.create(
            tenant=self.tenant,
            name="مراقبت روزانه",
            slug="daily-care",
            status=CatalogStatus.ACTIVE,
        )

    def _create_caregiver_supplier(
        self,
        *,
        display_name="مراقب نمونه",
        city="tehran",
        specialty="پرستار",
        bio="",
        years_experience=None,
        service_radius_km=None,
        verification_status="unverified",
        provider_type=CaregiverProviderType.INDEPENDENT,
        availability_status=AvailabilityStatus.AVAILABLE,
        supplier_status=SupplierStatus.ACTIVE,
        profile_status="active",
        service_category_ids=None,
        membership_status=OrgMembershipStatus.ACTIVE,
    ):
        phone = f"0912{uuid.uuid4().hex[:7]}"
        person = Person.objects.create(tenant=self.tenant, full_name=display_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)
        caregiver = CaregiverProfile.objects.create(
            user=user,
            person=person,
            phone=phone,
            display_name=display_name,
            city=city,
            specialty=specialty,
            bio=bio,
            years_experience=years_experience,
            service_radius_km=service_radius_km,
            verification_status=verification_status,
            provider_type=provider_type,
            status=profile_status,
        )
        supplier = get_or_create_supplier_for_caregiver(caregiver, tenant_id=self.tenant.id)
        supplier.service_categories = service_category_ids or [str(self.category.id)]
        supplier.status = supplier_status
        supplier.availability_status = availability_status
        supplier.save(update_fields=["service_categories", "status", "availability_status"])

        if provider_type == CaregiverProviderType.ORGANIZATION_AFFILIATED:
            self._create_membership(user=user, person=person, status=membership_status)

        return supplier, caregiver

    def _create_membership(self, *, user, person, status=OrgMembershipStatus.ACTIVE):
        """A real OrganizationMembership backing an ORGANIZATION_AFFILIATED
        caregiver — in production a caregiver only ever gets that
        provider_type by way of an actual membership row, so test fixtures
        must create one too (Architecture Review M2: eligibility depends on
        this membership's status, not just the caregiver's own)."""
        admin_person = Person.objects.create(tenant=self.tenant, full_name="مدیر سازمان")
        admin_user = UserAccount.objects.create_user(
            phone=f"0913{uuid.uuid4().hex[:7]}",
            person=admin_person,
            tenant=self.tenant,
        )
        organization = OrganizationProfile.objects.create(
            name="سازمان نمونه",
            code=f"org-{uuid.uuid4().hex[:8]}",
            admin_user=admin_user,
            tenant=self.tenant,
            status="active",
        )
        return OrganizationMembership.objects.create(
            organization=organization,
            user=user,
            person=person,
            role_type=OrgMembershipRole.CAREGIVER,
            status=status,
            joined_at=timezone.now(),
        )

    def _create_completed_order(self, *, supplier):
        return Order.objects.create(
            tenant=self.tenant,
            source=OrderSource.OPERATOR,
            status=OrderStatus.COMPLETED,
            service_category=self.category,
            description="سفارش تستی",
            city="tehran",
            address="تهران",
            phone="09120000000",
            assigned_supplier=supplier,
        )

    def _add_approved_review(self, *, supplier, rating="5.00", text="عالی بود"):
        reviewer_person = Person.objects.create(tenant=self.tenant, full_name="مشتری نمونه")
        Review.objects.create(
            tenant=self.tenant,
            supplier=supplier,
            reviewer_person_id=reviewer_person.id,
            overall_rating=rating,
            written_text=text,
            moderation_status=ReviewModerationStatus.APPROVED,
        )
        ReputationService.recalculate_reputation(supplier)
        return reviewer_person

    def _add_pending_review(self, *, supplier, rating="3.00", text="در انتظار بررسی"):
        reviewer_person = Person.objects.create(tenant=self.tenant, full_name="مشتری دیگر")
        return Review.objects.create(
            tenant=self.tenant,
            supplier=supplier,
            reviewer_person_id=reviewer_person.id,
            overall_rating=rating,
            written_text=text,
            moderation_status=ReviewModerationStatus.PENDING,
        )
