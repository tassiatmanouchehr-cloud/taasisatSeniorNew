"""Accounts services."""

from .affiliations import approve_affiliation_request, create_affiliation_request, reject_affiliation_request
from .care_recipients import CareRecipientService
from .organization_identity import list_administered_organizations
from .organization_staff import OrganizationStaffService
from .organizations import create_organization_membership, find_organization_by_code_or_name
from .otp import OTPService
from .phone import normalize_phone, validate_iranian_phone
from .profiles import (
    add_trusted_contact,
    calculate_caregiver_profile_completion,
    calculate_customer_profile_completion,
    create_primary_elder_profile,
)
from .provider_identity import resolve_supplier_for_user
from .registration import RegistrationService
