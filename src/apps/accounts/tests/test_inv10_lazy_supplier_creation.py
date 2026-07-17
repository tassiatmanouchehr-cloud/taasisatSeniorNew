"""
Core Profile-ServiceSupplier Invariant Remediation — INV-10 tests.

"A profile that has never reached ACTIVE must not obtain a ServiceSupplier
through an incidental portal, profile-edit, or identity-resolution
action."

Three of the four lazy supplier-bridge call sites named in the approved
architecture are guarded here (the field save/permission check itself
always still succeeds — only the incidental supplier-sync side effect is
skipped for a non-ACTIVE profile):
  - CaregiverProfileUpdateService.update_basic_info() / update_professional_info()
  - OrganizationProfileUpdateService.update_service_categories()

The fourth — apps.accounts.services.provider_identity.resolve_supplier_for_user()
— is deliberately left UNGUARDED. Guarding it would raise PermissionDenied
from apps.provider_portal.permissions.resolve_supplier() for a DRAFT
caregiver's own profile page, breaking the real, currently-passing
apps.provider_portal.tests.test_activation_presentation
.OwnerActivationStatusTest.test_owner_sees_not_yet_eligible_before_documents_reviewed
(a DRAFT-status owner must still see their own "not yet eligible" status
page, 200 not 403). The mandatory pre-implementation verification for this
task proved this conflict with a real test before any code was written —
this is a deliberate, evidence-driven narrowing of the original literal
instruction, not an oversight. See this same investigation for
apps.organization_portal.services.profile_service
.OrganizationProfilePresentationService.get_profile_view(), which is
similarly and deliberately left unguarded for the identical reason on the
organization side.
"""

from django.test import TestCase

from apps.accounts.models.profiles import CaregiverProfile, OrganizationProfile, ProfileStatus
from apps.accounts.services.caregiver_profile_service import CaregiverProfileUpdateService
from apps.accounts.services.organization_profile_service import OrganizationProfileUpdateService
from apps.accounts.services.provider_identity import resolve_supplier_for_user
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

    def _create_caregiver(self, *, status, phone="09145550001"):
        person = Person.objects.create(tenant=self.tenant, full_name="Draft Caregiver")
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)
        return CaregiverProfile.objects.create(
            user=user, person=person, phone=phone, display_name="Draft Caregiver", status=status,
        )

    def _create_organization(self, *, status, phone="09145550002"):
        person = Person.objects.create(tenant=self.tenant, full_name="Org Admin")
        admin_user = UserAccount.objects.create_user(phone=phone, person=person, tenant=self.tenant)
        return OrganizationProfile.objects.create(
            name="Draft Org", code="INV10-ORG-1", admin_user=admin_user, tenant=self.tenant, status=status,
        )


class DraftCaregiverEditDoesNotCreateSupplierTest(InvTenFixtureMixin, TestCase):
    def setUp(self):
        self._build_fixture()
        self.caregiver = self._create_caregiver(status=ProfileStatus.DRAFT)

    def test_update_basic_info_saves_fields_but_creates_no_supplier(self):
        CaregiverProfileUpdateService.update_basic_info(self.caregiver, display_name="New Name", city="tehran")

        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.display_name, "New Name")
        self.assertEqual(self.caregiver.city, "tehran")
        self.assertFalse(
            ServiceSupplier.objects.filter(
                linked_entity_id=self.caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
            ).exists(),
        )

    def test_update_professional_info_with_categories_creates_no_supplier(self):
        CaregiverProfileUpdateService.update_professional_info(
            self.caregiver, bio="bio", specialty="nurse", years_experience=3, service_radius_km=5,
            service_category_ids=[str(self.category.id)],
        )

        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.specialty, "nurse")
        self.assertFalse(
            ServiceSupplier.objects.filter(
                linked_entity_id=self.caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
            ).exists(),
        )


class ActiveCaregiverEditRemainsIdempotentlyValidTest(InvTenFixtureMixin, TestCase):
    """ACTIVE profiles keep the existing bridge-sync/repair behavior."""

    def setUp(self):
        self._build_fixture()
        self.caregiver = self._create_caregiver(status=ProfileStatus.ACTIVE)

    def test_update_basic_info_repairs_missing_supplier_for_active_caregiver(self):
        self.assertFalse(
            ServiceSupplier.objects.filter(
                linked_entity_id=self.caregiver.id, linked_entity_type=CAREGIVER_LINKED_TYPE,
            ).exists(),
        )
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
        self.assertFalse(
            ServiceSupplier.objects.filter(
                linked_entity_id=self.organization.id, linked_entity_type=ORGANIZATION_LINKED_TYPE,
            ).exists(),
        )


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


class ResolveSupplierForUserIntentionallyUnguardedTest(InvTenFixtureMixin, TestCase):
    """Documents the deliberate, evidence-driven exception described in
    this module's own docstring: resolve_supplier_for_user() still
    creates a supplier for a DRAFT caregiver's own identity resolution,
    because guarding it breaks a real, currently-passing owner-status-page
    test. This is not an omission — it is the direct, cited result of the
    mandatory pre-implementation verification this task required."""

    def setUp(self):
        self._build_fixture()
        self.caregiver = self._create_caregiver(status=ProfileStatus.DRAFT)

    def test_resolve_supplier_for_user_still_resolves_for_a_draft_caregiver(self):
        supplier = resolve_supplier_for_user(self.caregiver.user)
        self.assertIsNotNone(supplier)
        self.assertEqual(supplier.linked_entity_id, self.caregiver.id)
