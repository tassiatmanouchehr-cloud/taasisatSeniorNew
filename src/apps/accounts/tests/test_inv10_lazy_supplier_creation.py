"""
Core Profile-ServiceSupplier Invariant Remediation — INV-10 tests.

"A profile that has never reached ACTIVE must not obtain a ServiceSupplier
through portal navigation, profile rendering, identity resolution, or
another incidental read operation."

Independent pre-merge review of PR #18 found that the originally-shipped
design left `resolve_supplier_for_user()` (and, on the organization side,
`OrganizationProfilePresentationService.get_profile_view()`) completely
unguarded, and proved — by direct execution, not inference — that a DRAFT
`CaregiverProfile` reachable through ordinary `provider_portal` navigation
(via `_guard()`, gating every view in that app) acquired a fully **ACTIVE**
`ServiceSupplier` as a side effect. That was a genuine invariant violation,
not an approved exception: the requirement that a DRAFT owner can view
their own status page never required that identity resolution be allowed
to *create* a supplier.

Fixed by splitting identity resolution into two distinct needs
(`apps.accounts.services.provider_identity`):
  - `resolve_supplier_for_user()` — for callers that need a real, working
    supplier to act on (assignments, visits, availability, earnings) —
    now raises `AccountsError` for a non-ACTIVE profile instead of
    silently creating one.
  - `resolve_provider_context_for_user()` — for callers that only need to
    render the caller's own identity (profile/dashboard/self-management
    pages) — never creates a supplier for a non-ACTIVE profile; returns
    `supplier=None` instead.

All six lazy supplier-bridge call sites named in the approved architecture
are guarded here:
  - CaregiverProfileUpdateService.update_basic_info() / update_professional_info()
  - OrganizationProfileUpdateService.update_service_categories()
  - apps.accounts.services.provider_identity.resolve_supplier_for_user()
  - apps.accounts.services.provider_identity.resolve_provider_context_for_user()
  - apps.provider_portal.views._guard() / _guard_with_caregiver() (view-level)
  - apps.organization_portal.services.profile_service
    .OrganizationProfilePresentationService.get_profile_view()
"""

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models.profiles import CaregiverProfile, OrganizationProfile, ProfileStatus
from apps.accounts.services.caregiver_profile_service import CaregiverProfileUpdateService
from apps.accounts.services.errors import AccountsError
from apps.accounts.services.organization_profile_service import OrganizationProfileUpdateService
from apps.accounts.services.provider_identity import (
    resolve_provider_context_for_user,
    resolve_supplier_for_user,
)
from apps.accounts.services.supplier_bridge import CAREGIVER_LINKED_TYPE, ORGANIZATION_LINKED_TYPE
from apps.kernel.models import Person, UserAccount
from apps.kernel.models.supplier import ServiceSupplier
from apps.kernel.services.tenant_service import TenantService
from apps.kernel.tests.rbac_helpers import grant_permissions
from apps.orders.models import CatalogStatus, ServiceCategory


class InvTenFixtureMixin:
    def _build_fixture(self):
        self.tenant = TenantService.get_default_tenant()
        self.category = ServiceCategory.objects.create(
            tenant=self.tenant, name="Home Care", slug="home-care-inv10", status=CatalogStatus.ACTIVE,
        )

    def _create_caregiver(self, *, status, phone="09145550001", display_name="Draft Caregiver"):
        person = Person.objects.create(tenant=self.tenant, full_name=display_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)
        return CaregiverProfile.objects.create(
            user=user, person=person, phone=phone, display_name=display_name, status=status,
        )

    def _create_organization(self, *, status, phone="09145550002", code="INV10-ORG-1"):
        from apps.accounts.models.profiles import OrganizationMembership, OrgMembershipRole, OrgMembershipStatus

        person = Person.objects.create(tenant=self.tenant, full_name="Org Admin")
        admin_user = UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)
        organization = OrganizationProfile.objects.create(
            name="Draft Org", code=code, admin_user=admin_user, tenant=self.tenant, status=status,
        )
        OrganizationMembership.objects.create(
            organization=organization, user=admin_user, person=person,
            role_type=OrgMembershipRole.ADMIN, status=OrgMembershipStatus.ACTIVE,
        )
        return organization

    def _no_caregiver_supplier(self, caregiver) -> bool:
        return not ServiceSupplier.objects.filter(
            linked_entity_id=caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
        ).exists()

    def _no_organization_supplier(self, organization) -> bool:
        return not ServiceSupplier.objects.filter(
            linked_entity_id=organization.id, linked_entity_type=ORGANIZATION_LINKED_TYPE,
        ).exists()


class DraftCaregiverEditDoesNotCreateSupplierTest(InvTenFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()
        self.caregiver = self._create_caregiver(status=ProfileStatus.DRAFT)

    def test_update_basic_info_saves_fields_but_creates_no_supplier(self):
        CaregiverProfileUpdateService.update_basic_info(self.caregiver, display_name="New Name", city="tehran")

        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.display_name, "New Name")
        self.assertEqual(self.caregiver.city, "tehran")
        self.assertTrue(self._no_caregiver_supplier(self.caregiver))

    def test_update_professional_info_with_categories_creates_no_supplier(self):
        CaregiverProfileUpdateService.update_professional_info(
            self.caregiver, bio="bio", specialty="nurse", years_experience=3, service_radius_km=5,
            service_category_ids=[str(self.category.id)],
        )

        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.specialty, "nurse")
        self.assertTrue(self._no_caregiver_supplier(self.caregiver))


class ActiveCaregiverEditRemainsIdempotentlyValidTest(InvTenFixtureMixin, TestCase):
    """ACTIVE profiles keep the existing bridge-sync/repair behavior."""

    def setUp(self):
        self._build_fixture()
        self.caregiver = self._create_caregiver(status=ProfileStatus.ACTIVE)

    def test_update_basic_info_repairs_missing_supplier_for_active_caregiver(self):
        self.assertTrue(self._no_caregiver_supplier(self.caregiver))
        CaregiverProfileUpdateService.update_basic_info(self.caregiver, display_name="Active Name", city="tehran")

        supplier = ServiceSupplier.objects.get(
            linked_entity_id=self.caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
        )
        self.assertEqual(supplier.display_name, "Active Name")


class DraftOrganizationEditDoesNotCreateSupplierTest(InvTenFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()
        self.organization = self._create_organization(status=ProfileStatus.DRAFT)
        from apps.accounts.permission_keys import ORGANIZATION_PROFILE_UPDATE

        grant_permissions(self.tenant, self.organization.admin_user, [ORGANIZATION_PROFILE_UPDATE])

    def test_update_service_categories_creates_no_supplier_for_draft_organization(self):
        OrganizationProfileUpdateService.update_service_categories(
            self.organization, actor=self.organization.admin_user, service_category_ids=[str(self.category.id)],
        )
        self.assertTrue(self._no_organization_supplier(self.organization))


class ActiveOrganizationEditRemainsIdempotentlyValidTest(InvTenFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()
        self.organization = self._create_organization(status=ProfileStatus.ACTIVE)
        from apps.accounts.permission_keys import ORGANIZATION_PROFILE_UPDATE

        grant_permissions(self.tenant, self.organization.admin_user, [ORGANIZATION_PROFILE_UPDATE])

    def test_update_service_categories_repairs_missing_supplier_for_active_organization(self):
        OrganizationProfileUpdateService.update_service_categories(
            self.organization, actor=self.organization.admin_user, service_category_ids=[str(self.category.id)],
        )
        supplier = ServiceSupplier.objects.get(
            linked_entity_id=self.organization.id, linked_entity_type=ORGANIZATION_LINKED_TYPE,
        )
        self.assertEqual(supplier.service_categories, [str(self.category.id)])


class ResolveSupplierForUserServiceLayerTest(InvTenFixtureMixin, TestCase):
    """apps.accounts.services.provider_identity — the two-function split.
    Corrects the pre-merge-review-flagged defect: resolve_supplier_for_user()
    must never create a supplier for a non-ACTIVE profile;
    resolve_provider_context_for_user() must render identity without ever
    creating one either, only repairing/resolving for an ACTUALLY ACTIVE
    profile."""

    def setUp(self):
        self._build_fixture()

    def test_resolve_supplier_for_user_rejects_draft_caregiver_and_creates_no_supplier(self):
        caregiver = self._create_caregiver(status=ProfileStatus.DRAFT)
        with self.assertRaises(AccountsError):
            resolve_supplier_for_user(caregiver.user)
        self.assertTrue(self._no_caregiver_supplier(caregiver))

    def test_resolve_supplier_for_user_resolves_active_caregiver(self):
        caregiver = self._create_caregiver(status=ProfileStatus.ACTIVE, phone="09145550011")
        supplier = resolve_supplier_for_user(caregiver.user)
        self.assertIsNotNone(supplier)
        self.assertEqual(supplier.linked_entity_id, caregiver.id)

    def test_resolve_provider_context_for_draft_caregiver_has_no_supplier(self):
        caregiver = self._create_caregiver(status=ProfileStatus.DRAFT, phone="09145550012")
        context = resolve_provider_context_for_user(caregiver.user)
        self.assertEqual(context.caregiver.id, caregiver.id)
        self.assertIsNone(context.supplier)
        self.assertTrue(self._no_caregiver_supplier(caregiver))

    def test_resolve_provider_context_for_active_caregiver_resolves_supplier(self):
        caregiver = self._create_caregiver(status=ProfileStatus.ACTIVE, phone="09145550013")
        context = resolve_provider_context_for_user(caregiver.user)
        self.assertIsNotNone(context.supplier)
        self.assertEqual(context.supplier.linked_entity_id, caregiver.id)

    def test_resolve_provider_context_repairs_missing_supplier_for_active_caregiver(self):
        caregiver = self._create_caregiver(status=ProfileStatus.ACTIVE, phone="09145550014")
        self.assertTrue(self._no_caregiver_supplier(caregiver))
        context = resolve_provider_context_for_user(caregiver.user)
        self.assertIsNotNone(context.supplier)
        self.assertFalse(self._no_caregiver_supplier(caregiver))


class ProviderPortalDraftNavigationTest(InvTenFixtureMixin, TestCase):
    """View-level proof: a DRAFT caregiver navigating the real provider
    portal never acquires a ServiceSupplier, whether on the allowed
    self-view pages or on pages that genuinely require an active
    supplier (which must reject instead)."""

    def setUp(self):
        self._build_fixture()
        self.caregiver = self._create_caregiver(status=ProfileStatus.DRAFT)
        self.client.force_login(self.caregiver.user)

    def test_draft_caregiver_profile_page_renders_and_creates_no_supplier(self):
        response = self.client.get(reverse("provider_portal:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self._no_caregiver_supplier(self.caregiver))

    def test_draft_caregiver_dashboard_renders_pending_state_and_creates_no_supplier(self):
        """The dashboard is a self-view page, not a supplier-required
        action — a DRAFT caregiver lands on it (200, pending-activation
        state) rather than being redirected elsewhere, and no
        ServiceSupplier is created."""
        response = self.client.get(reverse("provider_portal:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self._no_caregiver_supplier(self.caregiver))

    def test_draft_caregiver_profile_edit_professional_renders_and_creates_no_supplier(self):
        response = self.client.get(reverse("provider_portal:profile-edit-professional"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self._no_caregiver_supplier(self.caregiver))

    def test_draft_caregiver_supplier_required_route_rejects_and_creates_no_supplier(self):
        """assignments_list_view is _guard()-gated — genuinely requires an
        ACTIVE supplier and must reject a DRAFT caregiver instead of
        silently creating one."""
        response = self.client.get(reverse("provider_portal:assignments"))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(self._no_caregiver_supplier(self.caregiver))


class ProviderPortalActiveNavigationTest(InvTenFixtureMixin, TestCase):
    """The same routes for an ACTIVE caregiver must keep resolving/
    repairing the supplier through the sanctioned bridge."""

    def setUp(self):
        self._build_fixture()
        self.caregiver = self._create_caregiver(status=ProfileStatus.ACTIVE, phone="09145550021")
        self.client.force_login(self.caregiver.user)

    def test_active_caregiver_dashboard_resolves_supplier(self):
        response = self.client.get(reverse("provider_portal:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self._no_caregiver_supplier(self.caregiver))

    def test_active_caregiver_supplier_required_route_succeeds(self):
        response = self.client.get(reverse("provider_portal:assignments"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self._no_caregiver_supplier(self.caregiver))


class OrganizationPortalDraftNavigationTest(InvTenFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()
        self.organization = self._create_organization(status=ProfileStatus.DRAFT)
        self.client.force_login(self.organization.admin_user)

    def test_draft_organization_profile_page_renders_and_creates_no_supplier(self):
        response = self.client.get(reverse("organization_portal:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self._no_organization_supplier(self.organization))


class OrganizationPortalActiveNavigationTest(InvTenFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()
        self.organization = self._create_organization(status=ProfileStatus.ACTIVE, phone="09145550022")
        self.client.force_login(self.organization.admin_user)

    def test_active_organization_profile_page_resolves_supplier(self):
        response = self.client.get(reverse("organization_portal:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self._no_organization_supplier(self.organization))
