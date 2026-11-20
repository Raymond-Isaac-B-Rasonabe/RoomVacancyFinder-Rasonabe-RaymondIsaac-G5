from datetime import time
from django import forms
from .models import Room, VacancyReport

class ReportForm(forms.ModelForm):
    class Meta:
        model = VacancyReport
        fields = ("room", "is_vacant", "slot_start", "slot_end", "notes")
        widgets = {
            "slot_start": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
            "slot_end": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["room"].queryset = Room.objects.filter(
            building__is_active=True, is_accessible=True
        ).select_related("building")

    def clean(self):
        data = super().clean()
        start, end = data.get("slot_start"), data.get("slot_end")
        if start and end:
            if start >= end:
                raise forms.ValidationError("Start time must be before end time.")
            if start < time(8, 0) or end > time(19, 0):
                raise forms.ValidationError("Times must be between 8:00 AM and 7:00 PM.")
        return data