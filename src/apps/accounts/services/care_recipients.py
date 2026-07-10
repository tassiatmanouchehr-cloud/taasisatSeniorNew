"""
Care Recipient management — Customer Experience Phase 1, extended in
Epic 02 (Marketplace Operational Experience) Customer Experience Phase 2.

"Care Recipient" is the product-facing name for apps.accounts.models
.profiles.ElderProfile — see the model's own docstring and ADR-008 for why
no new model was introduced. This service is the one place that creates,
updates, archives, and looks up ElderProfile rows on behalf of the
customer portal; nothing here bypasses ownership — every lookup is scoped
to the owning CustomerProfile, so one customer can never read or edit
another's care recipients.

Deliberately still just fields on ElderProfile, no related models yet —
future extension (medical documents, assessments, consent records,
attachments, care plans, historical-order views) is expected to arrive as
new FK-related models pointing back at ElderProfile, which this service
layer does not need to anticipate or change shape for today.

Publishes CareRecipientCreated/CareRecipientUpdated/CareRecipientArchived
(audit-only, no notification handler registered — same reasoning as the
share-link and provider-action events: publish() audits unconditionally
regardless of whether a handler exists).
"""

from django.db import transaction

from apps.kernel.events.base import (
    CARE_RECIPIENT_ARCHIVED,
    CARE_RECIPIENT_CREATED,
    CARE_RECIPIENT_UPDATED,
    DomainEvent,
)
from apps.kernel.events.publisher import publish as publish_domain_event

from .errors import AccountsError

CARE_RECIPIENT_FIELDS = (
    "full_name", "gender", "birth_date", "relationship", "phone", "city", "address",
    "care_needs", "medical_notes", "disabilities", "allergies", "mobility_level",
    "preferred_caregiver_gender", "preferred_language", "communication_notes",
    "emergency_contact_name", "emergency_contact_phone", "emergency_notes",
)


def _publish(event_type, *, customer_profile, care_recipient):
    tenant_id = customer_profile.person.tenant_id
    event = DomainEvent(
        event_type=event_type,
        tenant_id=tenant_id,
        aggregate_type="ElderProfile",
        aggregate_id=care_recipient.id,
        actor_id=customer_profile.person_id,
        payload={"customer_profile_id": str(customer_profile.id)},
    )
    transaction.on_commit(lambda: publish_domain_event(event))


class CareRecipientService:
    """Creates, updates, archives, and resolves care recipients (ElderProfile) for a CustomerProfile."""

    @classmethod
    def list_for_customer(cls, customer_profile, *, include_archived=False):
        from ..models.profiles import ProfileStatus

        queryset = customer_profile.elder_profiles.order_by("-is_primary", "full_name")
        if not include_archived:
            queryset = queryset.exclude(status=ProfileStatus.ARCHIVED)
        return queryset

    @classmethod
    def get_for_customer(cls, customer_profile, care_recipient_id):
        """Ownership-safe lookup: raises AccountsError if the care recipient
        doesn't exist or doesn't belong to this customer — never leaks
        cross-customer existence. Deliberately does not exclude archived
        rows — a customer can still view (and reactivate) an archived
        recipient by id."""
        from ..models.profiles import ElderProfile

        try:
            return customer_profile.elder_profiles.get(id=care_recipient_id)
        except ElderProfile.DoesNotExist:
            raise AccountsError("Care recipient not found.")

    @classmethod
    @transaction.atomic
    def create(cls, *, customer_profile, full_name, **fields):
        from ..models.profiles import ElderProfile

        if not full_name or not full_name.strip():
            raise AccountsError("Care recipient full name is required.")

        unknown = set(fields) - set(CARE_RECIPIENT_FIELDS)
        if unknown:
            raise AccountsError(f"Unknown care recipient field(s): {sorted(unknown)}")

        is_primary = not customer_profile.elder_profiles.exists()
        care_recipient = ElderProfile.objects.create(
            customer_profile=customer_profile, full_name=full_name, is_primary=is_primary, **fields,
        )
        _publish(CARE_RECIPIENT_CREATED, customer_profile=customer_profile, care_recipient=care_recipient)
        return care_recipient

    @classmethod
    @transaction.atomic
    def update(cls, care_recipient, **fields):
        unknown = set(fields) - set(CARE_RECIPIENT_FIELDS) - {"full_name"}
        if unknown:
            raise AccountsError(f"Unknown care recipient field(s): {sorted(unknown)}")

        for field, value in fields.items():
            setattr(care_recipient, field, value)
        care_recipient.save(update_fields=[*fields.keys(), "updated_at"])
        _publish(
            CARE_RECIPIENT_UPDATED,
            customer_profile=care_recipient.customer_profile, care_recipient=care_recipient,
        )
        return care_recipient

    @classmethod
    @transaction.atomic
    def archive(cls, care_recipient):
        """Soft-removes a care recipient from the customer's active list without
        deleting it (order history referencing it must keep working)."""
        from ..models.profiles import ProfileStatus

        care_recipient.status = ProfileStatus.ARCHIVED
        care_recipient.save(update_fields=["status", "updated_at"])
        _publish(
            CARE_RECIPIENT_ARCHIVED,
            customer_profile=care_recipient.customer_profile, care_recipient=care_recipient,
        )
        return care_recipient
