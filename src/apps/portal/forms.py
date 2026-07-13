"""Forms for the customer portal — Customer Experience Phase 1."""

from django import forms

from apps.accounts.models.profiles import CaregiverGenderPreference, CareRecipientRelationship, MobilityLevel
from apps.portal.services.care_recipient_service import CAREGIVER_GENDER_LABELS, MOBILITY_LABELS, RELATIONSHIP_LABELS

# CareRecipientRelationship/MobilityLevel/CaregiverGenderPreference carry
# English-only verbose_names — localized choice tuples for the form
# widgets, reusing the same Persian labels CareRecipientPresentationService
# uses to display these values (Epic 07, Customer Portal Completion).
_RELATIONSHIP_CHOICES = [(value, RELATIONSHIP_LABELS[value]) for value in CareRecipientRelationship.values]
_MOBILITY_CHOICES = [(value, MOBILITY_LABELS[value]) for value in MobilityLevel.values]
_CAREGIVER_GENDER_CHOICES = [(value, CAREGIVER_GENDER_LABELS[value]) for value in CaregiverGenderPreference.values]

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
    relationship = forms.ChoiceField(choices=[("", "—")] + _RELATIONSHIP_CHOICES, required=False)
    phone = forms.CharField(max_length=20, required=False)
    city = forms.CharField(max_length=100, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    care_needs = forms.CharField(widget=forms.Textarea, required=False)
    medical_notes = forms.CharField(widget=forms.Textarea, required=False)
    disabilities = forms.CharField(widget=forms.Textarea, required=False)
    allergies = forms.CharField(widget=forms.Textarea, required=False)
    mobility_level = forms.ChoiceField(choices=_MOBILITY_CHOICES, required=False)
    preferred_caregiver_gender = forms.ChoiceField(choices=_CAREGIVER_GENDER_CHOICES, required=False)
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
        widget=forms.Textarea,
        error_messages={"required": "توضیحات درخواست الزامی است."},
    )


class CustomerProfileEditForm(StyledForm):
    """Shape-only validation, mirroring CareRecipientForm's convention.
    Phone/email are not editable here — phone is the OTP login identity
    (apps.accounts owns it), out of scope for this Epic."""

    display_name = forms.CharField(max_length=255, error_messages={"required": "نام و نام خانوادگی الزامی است."})
    city = forms.CharField(max_length=100, required=False)
    relation_to_elder = forms.CharField(max_length=50, required=False)
    preferred_contact_method = forms.CharField(max_length=50, required=False)
    notes = forms.CharField(widget=forms.Textarea, required=False)


class ReviewSubmitForm(StyledForm):
    """Shape-only validation. Domain rules (order must be completed, one
    review per order, score bounds) live in
    apps.reviews.services.review_submission_service.ReviewSubmissionService."""

    quality = forms.IntegerField(min_value=1, max_value=5)
    punctuality = forms.IntegerField(min_value=1, max_value=5)
    professionalism = forms.IntegerField(min_value=1, max_value=5)
    communication = forms.IntegerField(min_value=1, max_value=5)
    written_text = forms.CharField(widget=forms.Textarea, required=False, max_length=2000)


_DISPUTE_REASON_CHOICES = [
    ("SERVICE_NOT_PERFORMED", "خدمت ارائه نشد"),
    ("SERVICE_QUALITY", "کیفیت خدمت"),
    ("INCORRECT_AMOUNT", "مبلغ اشتباه"),
    ("DURATION_MISMATCH", "عدم تطابق مدت زمان"),
    ("UNAUTHORIZED_EXTRA_CHARGE", "هزینه اضافه غیرمجاز"),
    ("OTHER", "سایر"),
]


class DisputeOpenForm(StyledForm):
    """Shape-only validation — Financial Core PR-B (Section 24). Domain
    rules (ownership, amount <= disputable Escrow remainder, line
    validation) live in apps.commission.services.dispute_service
    .DisputeService.open()."""

    disputed_amount_irr = forms.IntegerField(
        min_value=1,
        error_messages={"required": "مبلغ اعتراض الزامی است."},
    )
    reason_code = forms.ChoiceField(choices=_DISPUTE_REASON_CHOICES)
    description = forms.CharField(widget=forms.Textarea, required=False, max_length=2000)
