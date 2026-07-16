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


class WorkingWindowEditForm(StyledForm):
    """Sprint 2.4: edits an existing window's start/end only — day_of_week
    is fixed at creation, matching WorkingWindowForm's own add-time fields."""

    start_time = forms.TimeField(error_messages={"required": "زمان شروع الزامی است."})
    end_time = forms.TimeField(error_messages={"required": "زمان پایان الزامی است."})


class BlockedPeriodForm(StyledForm):
    start_at = forms.DateTimeField(error_messages={"required": "زمان شروع الزامی است."})
    end_at = forms.DateTimeField(error_messages={"required": "زمان پایان الزامی است."})
    reason = forms.ChoiceField(choices=BlockedPeriodReason.choices, required=False, initial=BlockedPeriodReason.OTHER)
    notes = forms.CharField(widget=forms.Textarea, required=False)


class DeclineAssignmentForm(StyledForm):
    reason = forms.CharField(widget=forms.Textarea, required=False)


class JoinCompanyCodeForm(StyledForm):
    code = forms.CharField(
        max_length=50, label="کد سازمان", error_messages={"required": "کد سازمان الزامی است."},
    )


class BasicInfoForm(StyledForm):
    display_name = forms.CharField(
        max_length=255, label="نام نمایشی", error_messages={"required": "نام نمایشی الزامی است."}
    )
    city = forms.CharField(max_length=100, label="شهر", required=False)


class ProfessionalInfoForm(StyledForm):
    bio = forms.CharField(widget=forms.Textarea, label="بیوگرافی", required=False, max_length=2000)
    specialty = forms.CharField(max_length=100, label="تخصص", required=False)
    years_experience = forms.IntegerField(label="سابقه کار (سال)", required=False, min_value=0, max_value=80)
    service_radius_km = forms.IntegerField(label="شعاع خدمت‌رسانی (کیلومتر)", required=False, min_value=0, max_value=500)
    service_category_ids = forms.MultipleChoiceField(label="خدمات", required=False, choices=())

    def __init__(self, *args, service_category_choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service_category_ids"].choices = service_category_choices


class SkillForm(StyledForm):
    name = forms.CharField(
        max_length=100, label="مهارت", error_messages={"required": "نام مهارت الزامی است."},
    )


class ExperienceForm(StyledForm):
    title = forms.CharField(
        max_length=150, label="عنوان شغلی", error_messages={"required": "عنوان شغلی الزامی است."},
    )
    organization_name = forms.CharField(max_length=255, label="نام سازمان/کارفرما", required=False)
    description = forms.CharField(widget=forms.Textarea, label="توضیحات", required=False, max_length=2000)
    start_date = forms.DateField(label="تاریخ شروع", error_messages={"required": "تاریخ شروع الزامی است."})
    end_date = forms.DateField(label="تاریخ پایان", required=False)
    is_current = forms.BooleanField(label="در حال حاضر مشغول هستم", required=False)
    is_visible = forms.BooleanField(label="نمایش در نمایه عمومی", required=False, initial=True)

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")
        is_current = cleaned.get("is_current")
        if not is_current and start_date and end_date and end_date < start_date:
            self.add_error("end_date", "تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد.")
        return cleaned


class ImageUploadForm(StyledForm):
    image = forms.ImageField(label="تصویر", error_messages={"required": "لطفاً یک تصویر انتخاب کنید."})


class GalleryUploadForm(StyledForm):
    image = forms.ImageField(label="تصویر", error_messages={"required": "لطفاً یک تصویر انتخاب کنید."})
    caption = forms.CharField(max_length=255, label="عنوان", required=False)
    alt_text = forms.CharField(max_length=255, label="متن جایگزین (دسترس‌پذیری)", required=False)


class GalleryItemEditForm(StyledForm):
    caption = forms.CharField(max_length=255, label="عنوان", required=False)
    alt_text = forms.CharField(max_length=255, label="متن جایگزین (دسترس‌پذیری)", required=False)
    is_visible = forms.BooleanField(label="نمایش در نمایه عمومی", required=False, initial=True)


class DocumentUploadForm(StyledForm):
    file = forms.FileField(label="فایل", error_messages={"required": "لطفاً یک فایل انتخاب کنید."})
