"""Profile services — completion, elder, trusted contacts."""

from ..models.profiles import CustomerProfile, CaregiverProfile, ElderProfile, TrustedContact


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
