"""Forms for the provider portal — Epic 02 (Marketplace Operational Experience)."""

from django import forms

from apps.availability.models import BlockedPeriodReason, DayOfWeek

_INPUT_CLASS = (
    "mt-2 block w-full rounded-2xl border border-border bg-background px-4 py-3 "
    "text-text shadow-sm focus:border-primary focus:outline-none focus:ring-2"
)


class StyledForm(forms.Form):
    """Applies the portal's shared input styling to every field widget —
    presentation only, no validation/business rules live here."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {_INPUT_CLASS}".strip()


class WorkingWindowForm(StyledForm):
    day_of_week = forms.ChoiceField(choices=DayOfWeek.choices)
    start_time = forms.TimeField(error_messages={"required": "زمان شروع الزامی است."})
    end_time = forms.TimeField(error_messages={"required": "زمان پایان الزامی است."})


class BlockedPeriodForm(StyledForm):
    start_at = forms.DateTimeField(error_messages={"required": "زمان شروع الزامی است."})
    end_at = forms.DateTimeField(error_messages={"required": "زمان پایان الزامی است."})
    reason = forms.ChoiceField(choices=BlockedPeriodReason.choices, required=False, initial=BlockedPeriodReason.OTHER)
    notes = forms.CharField(widget=forms.Textarea, required=False)


class DeclineAssignmentForm(StyledForm):
    reason = forms.CharField(widget=forms.Textarea, required=False)
