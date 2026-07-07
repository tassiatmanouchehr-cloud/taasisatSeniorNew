"""
Registration Service — creates Person, UserAccount, profiles, and role assignments.

Called after OTP verification succeeds. Creates all required entities
in a single transaction.
"""

import logging
import uuid

from django.db import transaction

from apps.kernel.models import Person, Role, RoleAssignment, Tenant, UserAccount

from ..models.profiles import (
    CaregiverProfile,
    CompanyAffiliationRequest,
    CustomerProfile,
    OrganizationProfile,
)

logger = logging.getLogger(__name__)


def _get_default_tenant():
    """Get or create the default tenant for this platform instance."""
    tenant, _ = Tenant.objects.get_or_create(
        slug="salmandyar",
        defaults={
            "name": "سالمندیار",
            "status": "active",
        },
    )
    return tenant


def _assign_role(*, tenant, user, role_slug):
    """Assign a role to a user by slug. Creates role if missing."""
    role = Role.objects.filter(tenant=tenant, slug=role_slug).first()
    if role:
        RoleAssignment.objects.get_or_create(
            tenant=tenant,
            user=user,
            role=role,
            defaults={"scope_type": "platform"},
        )


def _generate_org_code(name: str) -> str:
    """Generate a unique organization code from the company name."""
    # Simple: first 4 chars of name + 4 random hex digits
    prefix = name[:4].upper().replace(" ", "")
    suffix = uuid.uuid4().hex[:4].upper()
    return f"{prefix}-{suffix}"


class RegistrationService:
    """Handles account creation for all registration paths."""

    @classmethod
    @transaction.atomic
    def create_customer(cls, *, phone: str, full_name: str, city: str = "", relation_to_elder: str = ""):
        """
        Create a customer account.

        Creates: Person → UserAccount → CustomerProfile → role assignment.
        Returns: (user, profile)
        """
        tenant = _get_default_tenant()

        person = Person.objects.create(
            tenant=tenant,
            full_name=full_name,
        )

        user = UserAccount.objects.create_user(
            phone=phone,
            person=person,
            tenant=tenant,
        )

        profile = CustomerProfile.objects.create(
            user=user,
            person=person,
            phone=phone,
            display_name=full_name,
            city=city,
            relation_to_elder=relation_to_elder,
        )

        _assign_role(tenant=tenant, user=user, role_slug="customer")

        logger.info("Customer created: %s (%s)", full_name, phone)
        return user, profile

    @classmethod
    @transaction.atomic
    def create_caregiver(
        cls,
        *,
        phone: str,
        full_name: str,
        specialty: str = "",
        city: str = "",
        company_code: str = "",
        company_name: str = "",
    ):
        """
        Create a caregiver account (independent by default).

        If company_code or company_name is provided, creates a pending
        CompanyAffiliationRequest. The caregiver remains independent
        until company admin approves.

        Creates: Person → UserAccount → CaregiverProfile → role assignment
                 → (optional) CompanyAffiliationRequest

        Returns: (user, profile, affiliation_request_or_None)
        """
        tenant = _get_default_tenant()

        person = Person.objects.create(
            tenant=tenant,
            full_name=full_name,
        )

        user = UserAccount.objects.create_user(
            phone=phone,
            person=person,
            tenant=tenant,
        )

        profile = CaregiverProfile.objects.create(
            user=user,
            person=person,
            phone=phone,
            display_name=full_name,
            specialty=specialty,
            city=city,
        )

        _assign_role(tenant=tenant, user=user, role_slug="independent_caregiver")

        # Handle optional company affiliation request
        affiliation_request = None
        company_ref = company_code or company_name
        if company_ref:
            # Try to resolve organization by code
            org = OrganizationProfile.objects.filter(code__iexact=company_code).first() if company_code else None

            affiliation_request = CompanyAffiliationRequest.objects.create(
                caregiver_profile=profile,
                requested_company_name_or_code=company_ref,
                organization=org,
            )
            logger.info(
                "Affiliation request created: %s → %s (resolved=%s)",
                full_name, company_ref, org is not None,
            )

        logger.info("Caregiver created: %s (%s, %s)", full_name, phone, specialty)
        return user, profile, affiliation_request

    @classmethod
    @transaction.atomic
    def create_company_admin(
        cls,
        *,
        phone: str,
        admin_name: str,
        admin_role_title: str = "",
        company_name: str,
        company_type: str = "",
        city: str = "",
        team_size: str = "",
    ):
        """
        Create a company admin account + organization.

        Creates: Person → UserAccount → OrganizationProfile → role assignment

        Returns: (user, organization)
        """
        tenant = _get_default_tenant()

        person = Person.objects.create(
            tenant=tenant,
            full_name=admin_name,
        )

        user = UserAccount.objects.create_user(
            phone=phone,
            person=person,
            tenant=tenant,
        )

        org_code = _generate_org_code(company_name)

        organization = OrganizationProfile.objects.create(
            name=company_name,
            code=org_code,
            admin_user=user,
            company_type=company_type,
            city=city,
            phone=phone,
            team_size=team_size,
            tenant=tenant,
        )

        _assign_role(tenant=tenant, user=user, role_slug="organization_admin")

        logger.info("Company admin created: %s for org '%s' (code=%s)", admin_name, company_name, org_code)
        return user, organization
