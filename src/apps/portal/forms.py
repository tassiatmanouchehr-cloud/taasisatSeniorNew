"""Forms for the customer portal — Customer Experience Phase 1."""

from django import forms

from apps.accounts.models.profiles import CaregiverGenderPreference, CareRecipientRelationship, MobilityLevel

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


class CareRecipientForm(StyledForm):
    """Shape-only validation. Domain rules (ownership, required full_name)
    live in apps.accounts.services.care_recipients.CareRecipientService."""

    full_name = forms.CharField(max_length=255, error_messages={"required": "نام و نام خانوادگی الزامی است."})
    gender = forms.CharField(max_length=20, required=False)
    birth_date = forms.DateField(required=False)
    relationship = forms.ChoiceField(choices=[("", "—")] + CareRecipientRelationship.choices, required=False)
    phone = forms.CharField(max_length=20, required=False)
    city = forms.CharField(max_length=100, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    care_needs = forms.CharField(widget=forms.Textarea, required=False)
    medical_notes = forms.CharField(widget=forms.Textarea, required=False)
    disabilities = forms.CharField(widget=forms.Textarea, required=False)
    allergies = forms.CharField(widget=forms.Textarea, required=False)
    mobility_level = forms.ChoiceField(choices=MobilityLevel.choices, required=False)
    preferred_caregiver_gender = forms.ChoiceField(choices=CaregiverGenderPreference.choices, required=False)
    preferred_language = forms.CharField(max_length=50, required=False)
    communication_notes = forms.CharField(widget=forms.Textarea, required=False)
    emergency_contact_name = forms.CharField(max_length=255, required=False)
    emergency_contact_phone = forms.CharField(max_length=20, required=False)
    emergency_notes = forms.CharField(widget=forms.Textarea, required=False)


class WizardChooseCareRecipientForm(StyledForm):
    care_recipient_id = forms.UUIDField(error_messages={"required": "لطفاً یک گیرنده خدمت انتخاب کنید."})


class WizardChooseServiceForm(StyledForm):
    service_category_id = forms.UUIDField(error_messages={"required": "لطفاً یک دسته خدمت انتخاب کنید."})
    service_type_id = forms.UUIDField(required=False)


class WizardChooseScheduleForm(StyledForm):
    requested_date = forms.DateField(required=False)
    requested_time_window = forms.CharField(max_length=100, required=False)


class WizardChooseAddressForm(StyledForm):
    city = forms.CharField(max_length=100, required=False)
    address = forms.CharField(widget=forms.Textarea, error_messages={"required": "آدرس الزامی است."})
    phone = forms.CharField(max_length=20, error_messages={"required": "شماره تماس الزامی است."})


class WizardNotesForm(StyledForm):
    description = forms.CharField(
        widget=forms.Textarea, error_messages={"required": "توضیحات درخواست الزامی است."},
    )
