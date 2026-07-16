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


class InviteCaregiverForm(StyledForm):
    phone = forms.CharField(
        max_length=20, label="شماره تلفن مراقب",
        error_messages={"required": "شماره تلفن مراقب الزامی است."},
    )


class OrganizationProfileForm(StyledForm):
    name = forms.CharField(max_length=255, label="نام سازمان", error_messages={"required": "نام سازمان الزامی است."})
    description = forms.CharField(widget=forms.Textarea, label="توضیحات", required=False, max_length=2000)
    city = forms.CharField(max_length=100, label="شهر", required=False)
    phone = forms.CharField(max_length=20, label="تلفن", required=False)
    address = forms.CharField(widget=forms.Textarea, label="آدرس", required=False)
    company_type = forms.CharField(max_length=100, label="نوع فعالیت", required=False)
    team_size = forms.CharField(max_length=20, label="اندازه تیم", required=False)


class OrganizationServicesForm(StyledForm):
    service_category_ids = forms.MultipleChoiceField(label="خدمات", required=False, choices=())

    def __init__(self, *args, service_category_choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service_category_ids"].choices = service_category_choices


class OrganizationImageUploadForm(StyledForm):
    image = forms.ImageField(label="تصویر", error_messages={"required": "لطفاً یک تصویر انتخاب کنید."})


class OrganizationDocumentUploadForm(StyledForm):
    file = forms.FileField(label="فایل", error_messages={"required": "لطفاً یک فایل انتخاب کنید."})
