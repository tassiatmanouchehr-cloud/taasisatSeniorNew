"""Profile services — completion, elder, trusted contacts, multi-role identity."""

from ..models.profiles import CustomerProfile, CaregiverProfile, ElderProfile, TrustedContact
from .registration import assign_role


def calculate_customer_profile_completion(profile: CustomerProfile) -> int:
    """Calculate profile completion percentage (0-100)."""
    fields = [
        bool(profile.display_name),
        bool(profile.phone),
        bool(profile.city),
        bool(profile.relation_to_elder),
        bool(profile.preferred_contact_method),
        profile.elder_profiles.exists(),
    ]
    filled = sum(fields)
    return int((filled / len(fields)) * 100)


CUSTOMER_PROFILE_EDITABLE_FIELDS = (
    "display_name", "city", "relation_to_elder", "preferred_contact_method", "notes",
)


class CustomerProfileUpdateService:
    """Read-write: the customer's own editable profile fields — Epic 07
    (Customer Portal Completion), keeping apps.portal.views a thin
    controller with no direct ORM access (matches CareRecipientService.update
    and CaregiverProfileUpdateService.update_basic_info)."""

    @classmethod
    def update_basic_info(cls, customer: CustomerProfile, **fields) -> CustomerProfile:
        unknown = set(fields) - set(CUSTOMER_PROFILE_EDITABLE_FIELDS)
        if unknown:
            raise ValueError(f"Unknown customer profile field(s): {sorted(unknown)}")

        for field, value in fields.items():
            setattr(customer, field, value)
        customer.save(update_fields=[*fields.keys(), "updated_at"])
        return customer


def calculate_caregiver_profile_completion(profile: CaregiverProfile) -> int:
    """Calculate profile completion percentage (0-100)."""
    fields = [
        bool(profile.display_name),
        bool(profile.phone),
        bool(profile.city),
        bool(profile.specialty),
        bool(profile.bio),
        profile.years_experience is not None,
        profile.service_radius_km is not None,
    ]
    filled = sum(fields)
    return int((filled / len(fields)) * 100)


def create_primary_elder_profile(*, customer_profile, full_name, **kwargs):
    """Create a primary elder profile for a customer."""
    elder = ElderProfile.objects.create(
        customer_profile=customer_profile,
        full_name=full_name,
        is_primary=True,
        **kwargs,
    )
    return elder


def add_trusted_contact(*, customer_profile, full_name, phone, **kwargs):
    """Add a trusted contact for a customer."""
    contact = TrustedContact.objects.create(
        customer_profile=customer_profile,
        full_name=full_name,
        phone=phone,
        **kwargs,
    )
    return contact


# ============================================================
# Multi-role identity — Module 21A
# ============================================================
#
# One Person/UserAccount may hold several profiles at once (e.g. a
# caregiver who also books care for their own parent as a customer).
# CustomerProfile and CaregiverProfile are independent OneToOneField(user)
# tables, so nothing in the schema prevents this — the gap was that
# RegistrationService.create_customer()/create_caregiver() always create a
# brand-new Person + UserAccount. These helpers instead attach a profile
# to an *existing* account, idempotently, without ever creating a second
# Person or UserAccount for the same human.


def ensure_customer_profile(user, *, phone=None, display_name=None, **kwargs) -> CustomerProfile:
    """Idempotently attach a CustomerProfile to an existing UserAccount.
    Returns the existing profile if one is already attached."""
    existing = CustomerProfile.objects.filter(user=user).first()
    if existing:
        return existing
    if user.person is None:
        raise ValueError("UserAccount must have a Person before a profile can be attached.")
    profile = CustomerProfile.objects.create(
        user=user, person=user.person,
        phone=phone or user.phone,
        display_name=display_name or user.person.full_name,
        **kwargs,
    )
    assign_role(tenant=user.tenant, user=user, role_slug="customer")
    return profile


def ensure_caregiver_profile(user, *, phone=None, display_name=None, **kwargs) -> CaregiverProfile:
    """Idempotently attach a CaregiverProfile to an existing UserAccount.
    Returns the existing profile if one is already attached."""
    existing = CaregiverProfile.objects.filter(user=user).first()
    if existing:
        return existing
    if user.person is None:
        raise ValueError("UserAccount must have a Person before a profile can be attached.")
    profile = CaregiverProfile.objects.create(
        user=user, person=user.person,
        phone=phone or user.phone,
        display_name=display_name or user.person.full_name,
        **kwargs,
    )
    assign_role(tenant=user.tenant, user=user, role_slug="independent_caregiver")
    return profile
