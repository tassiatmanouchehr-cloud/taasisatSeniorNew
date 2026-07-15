"""Forms for the admin portal — Financial Core PR-B dispute resolution
(Section 24) and Phase 1.1 manual document verification."""

from django import forms


class DisputeResolveForm(forms.Form):
    customer_refund_amount_irr = forms.IntegerField(min_value=0, required=False, initial=0)
    platform_amount_irr = forms.IntegerField(min_value=0, required=False, initial=0)
    company_amount_irr = forms.IntegerField(min_value=0, required=False, initial=0)
    caregiver_amount_irr = forms.IntegerField(min_value=0, required=False, initial=0)
    reason = forms.CharField(widget=forms.Textarea, error_messages={"required": "دلیل تصمیم الزامی است."})

    def clean(self):
        cleaned = super().clean()
        for key in (
            "customer_refund_amount_irr",
            "platform_amount_irr",
            "company_amount_irr",
            "caregiver_amount_irr",
        ):
            cleaned[key] = cleaned.get(key) or 0
        return cleaned


class DocumentReviewForm(forms.Form):
    """Reason is optional at the form level — VerificationReviewService
    itself enforces "required for reject/request_correction" (the
    authoritative rule lives in the service, matching this module's own
    thin-controller docstring), since whether a reason is required
    depends on which action is chosen."""

    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CORRECTION = "request_correction"
    ACTION_CHOICES = (
        (APPROVE, "تأیید"),
        (REJECT, "رد"),
        (REQUEST_CORRECTION, "درخواست اصلاح"),
    )

    action = forms.ChoiceField(choices=ACTION_CHOICES)
    reason = forms.CharField(widget=forms.Textarea, required=False)
