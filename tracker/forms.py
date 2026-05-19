# Time Tracker — a self-hosted project time tracking web app.
# Copyright (C) 2026 c4pt4in and contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
"""Forms for the time tracker."""
from django import forms

from .models import Project, TimeEntry


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "description", "color", "hourly_rate", "is_archived"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "color": forms.TextInput(attrs={"type": "color"}),
        }


class TimeEntryForm(forms.ModelForm):
    """Manual time entry form. User enters date + start + end, duration is auto-calculated."""

    class Meta:
        model = TimeEntry
        fields = ["project", "date", "start_time", "end_time", "description"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hide archived projects from selection on new entries
        if not self.instance.pk:
            self.fields["project"].queryset = Project.objects.filter(is_archived=False)

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")
        if start and end and end <= start:
            raise forms.ValidationError("End time must be after start time.")
        if (start and not end) or (end and not start):
            raise forms.ValidationError("Provide both start and end time, or neither.")
        return cleaned


class ReportFilterForm(forms.Form):
    """Filter options for the PDF/CSV report."""

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label="From",
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label="To",
    )
    projects = forms.ModelMultipleChoiceField(
        queryset=Project.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Projects (leave empty for all)",
    )
    include_archived = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Include archived projects",
    )
