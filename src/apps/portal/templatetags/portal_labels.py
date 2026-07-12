"""Template filters for Persian labels of English-only model choices —
Epic 07 (Customer Experience and Portal Completion). Reuses the same label
dicts CareRecipientPresentationService uses for the care-recipient detail
page, so the care-recipient list and request wizard show the same Persian
text instead of falling back to Django's English verbose_name."""

from django import template

from apps.portal.services.care_recipient_service import RELATIONSHIP_LABELS

register = template.Library()


@register.filter
def relationship_label(value):
    return RELATIONSHIP_LABELS.get(value, value)
