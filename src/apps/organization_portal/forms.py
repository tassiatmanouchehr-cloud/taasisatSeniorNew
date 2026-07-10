"""Forms for the organization portal — Epic 02 (Marketplace Operational Experience)."""

from django import forms

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


class AssignStaffForm(StyledForm):
    membership_id = forms.UUIDField(error_messages={"required": "لطفاً یک نیرو انتخاب کنید."})
