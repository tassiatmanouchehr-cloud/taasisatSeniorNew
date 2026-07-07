"""
Registration Service — creates Person, UserAccount, profiles, and role assignments.
"""

import logging
import uuid

from django.db import transaction
from django.utils import timezone

from apps.kernel.models import Person, Role, RoleAssignment, UserAccount
from apps.kernel.services.tenant_service import TenantService

from ..models.profiles import (
    CaregiverProfile,
    CompanyAffiliationRequest,
    CustomerProfile,
    OrganizationMembership,
    OrganizationProfile,
    OrgMembershipRole,
    OrgMembershipStatus,
    PlatformTeamArea,
    PlatformTeamMember,
)
from .organizations import find_organization_by_code_or_name

logger = logging.getLogger(__name__)


def _assign_role(*, tenant, user, role_slug):
    role = Role.objects.filter(tenant=tenant, slug=role_slug).first()
    if role:
        RoleAssignment.objects.get_or_create(
            tenant=tenant, user=user, role=role,
            defaults={"scope_type": "platform"},
        )


def _generate_org_code(name: str) -> str:
    prefix = name[:4].upper().replace(" ", "")
    suffix = uuid.uuid4().hex[:4].upper()
    return f"{prefix}-{suffix}"


class RegistrationService:

    @classmethod
    @transaction.atomic
    def create_customer(cls, *, phone, full_name, city="", relation_to_elder=""):
        tenant = TenantService.get_default_tenant()
        person = Person.objects.create(tenant=tenant, full_name=full_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        profile = CustomerProfile.objects.create(
            user=user, person=person, phone=phone, display_name=full_name,
            city=city, relation_to_elder=relation_to_elder,
        )
        _assign_role(tenant=tenant, user=user, role_slug="customer")
        logger.info("Customer created: %s (%s)", full_name, phone)
        return user, profile

    @classmethod
    @transaction.atomic
    def create_caregiver(cls, *, phone, full_name, specialty="", city="", company_code="", company_name=""):
        tenant = TenantService.get_default_tenant()
        person = Person.objects.create(tenant=tenant, full_name=full_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        profile = CaregiverProfile.objects.create(
            user=user, person=person, phone=phone, display_name=full_name,
            specialty=specialty, city=city,
        )
        _assign_role(tenant=tenant, user=user, role_slug="independent_caregiver")

        affiliation_request = None
        company_ref = company_code or company_name
        if company_ref:
            org = find_organization_by_code_or_name(company_ref)
            affiliation_request = CompanyAffiliationRequest.objects.create(
                caregiver_profile=profile,
                requested_company_name_or_code=company_ref,
                organization=org,
            )

        logger.info("Caregiver created: %s (%s)", full_name, phone)
        return user, profile, affiliation_request

    @classmethod
    @transaction.atomic
    def create_company_admin(cls, *, phone, admin_name, admin_role_title="", company_name, company_type="", city="", team_size=""):
        tenant = TenantService.get_default_tenant()
        person = Person.objects.create(tenant=tenant, full_name=admin_name)
        user = UserAccount.objects.create_user(phone=phone, person=person, tenant=tenant)
        org_code = _generate_org_code(company_name)

        organization = OrganizationProfile.objects.create(
            name=company_name, code=org_code, admin_user=user,
            company_type=company_type, city=city, phone=phone,
            team_size=team_size, tenant=tenant,
        )

        OrganizationMembership.objects.create(
            organization=organization, user=user, person=person,
            role_type=OrgMembershipRole.ADMIN,
            status=OrgMembershipStatus.ACTIVE,
            joined_at=timezone.now(),
        )

        _assign_role(tenant=tenant, user=user, role_slug="organization_admin")
        logger.info("Company admin created: %s for '%s' (code=%s)", admin_name, company_name, org_code)
        return user, organization
