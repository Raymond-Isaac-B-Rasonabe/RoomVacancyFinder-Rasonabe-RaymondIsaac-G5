from datetime import time
from django import forms
from django.utils import timezone
from .models import Building, Room, VacancyReport


class SearchForm(forms.Form):
    building = forms.ModelChoiceField(
        queryset=Building.objects.filter(is_active=True),
        required=False,
        empty_label="All buildings",
    )
    floor = forms.IntegerField(required=False, min_value=0)
    room_type = forms.ChoiceField(
        choices=[("", "Any type")] + list(VacancyReport.RoomType.choices),
        required=False,
    )
    date = forms.DateField(
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
    time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
    )

class ReportForm(forms.ModelForm):
    date_mode = forms.ChoiceField(
        label="Date",
        choices=[("auto", "Today (automatic)"), ("manual", "Choose a date")],
        widget=forms.RadioSelect,
        initial="auto",
    )

    field_order = ["room", "room_type", "is_vacant", "date_mode", "date",
                   "slot_start", "slot_end", "notes"]

    class Meta:
        model = VacancyReport
        fields = ("room", "room_type", "is_vacant", "date", "slot_start", "slot_end", "notes")
        labels = {
            "room_type": "Room type",
            "is_vacant": "Room is vacant",
            "date": "Pick a date",
            "slot_start": "From",
            "slot_end": "Until",
        }
        help_texts = {"date": "Only used if you chose “Choose a date”."}
        widgets = {
            "date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "slot_start": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
            "slot_end": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].required = False
        self.fields["room"].queryset = Room.objects.filter(
            building__is_active=True, is_accessible=True
        ).select_related("building")
        if self.instance.pk:                     # editing: show the saved date
            self.initial["date_mode"] = "manual"

    def clean(self):
        data = super().clean()
        mode = data.get("date_mode")
        if mode == "auto":
            data["date"] = timezone.localdate()
        elif mode == "manual":
            day = data.get("date")
            if not day:
                self.add_error("date", "Pick a date, or choose “Today (automatic)”.")
            elif day < timezone.localdate():
                self.add_error("date", "The date can't be in the past.")

        start, end = data.get("slot_start"), data.get("slot_end")
        if start and end:
            if start >= end:
                raise forms.ValidationError("Start time must be before end time.")
            if start < time(8, 0) or end > time(19, 0):
                raise forms.ValidationError("Times must be between 8:00 AM and 7:00 PM.")
        return data