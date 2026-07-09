"""
Care Recipient management — Customer Experience Phase 1.

"Care Recipient" is the product-facing name for apps.accounts.models
.profiles.ElderProfile — see the model's own docstring and ADR-008 for why
no new model was introduced. This service is the one place that creates,
updates, and looks up ElderProfile rows on behalf of the customer portal;
nothing here bypasses ownership — every lookup is scoped to the owning
CustomerProfile, so one customer can never read or edit another's care
recipients.
"""

from .errors import AccountsError

CARE_RECIPIENT_FIELDS = (
    "full_name", "gender", "birth_date", "relationship", "phone", "city", "address",
    "care_needs", "medical_notes", "disabilities", "allergies", "mobility_level",
    "preferred_caregiver_gender", "preferred_language", "communication_notes",
    "emergency_contact_name", "emergency_contact_phone", "emergency_notes",
)


class CareRecipientService:
    """Creates, updates, and resolves care recipients (ElderProfile) for a CustomerProfile."""

    @classmethod
    def list_for_customer(cls, customer_profile):
        return customer_profile.elder_profiles.order_by("-is_primary", "full_name")

    @classmethod
    def get_for_customer(cls, customer_profile, care_recipient_id):
        """Ownership-safe lookup: raises AccountsError if the care recipient
        doesn't exist or doesn't belong to this customer — never leaks
        cross-customer existence."""
        from ..models.profiles import ElderProfile

        try:
            return customer_profile.elder_profiles.get(id=care_recipient_id)
        except ElderProfile.DoesNotExist:
            raise AccountsError("Care recipient not found.")

    @classmethod
    def create(cls, *, customer_profile, full_name, **fields):
        from ..models.profiles import ElderProfile

        if not full_name or not full_name.strip():
            raise AccountsError("Care recipient full name is required.")

        unknown = set(fields) - set(CARE_RECIPIENT_FIELDS)
        if unknown:
            raise AccountsError(f"Unknown care recipient field(s): {sorted(unknown)}")

        is_primary = not customer_profile.elder_profiles.exists()
        return ElderProfile.objects.create(
            customer_profile=customer_profile, full_name=full_name, is_primary=is_primary, **fields,
        )

    @classmethod
    def update(cls, care_recipient, **fields):
        unknown = set(fields) - set(CARE_RECIPIENT_FIELDS) - {"full_name"}
        if unknown:
            raise AccountsError(f"Unknown care recipient field(s): {sorted(unknown)}")

        for field, value in fields.items():
            setattr(care_recipient, field, value)
        care_recipient.save(update_fields=[*fields.keys(), "updated_at"])
        return care_recipient
