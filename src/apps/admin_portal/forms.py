"""Forms for the admin portal — Financial Core PR-B dispute resolution
(Section 24). The only form this module has needed so far."""

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
