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
from django.contrib import admin

from .models import Project, TimeEntry


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "is_archived", "hourly_rate", "created_at")
    list_filter = ("is_archived",)
    search_fields = ("name", "description")


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ("project", "date", "status", "start_time", "end_time", "duration_minutes")
    list_filter = ("project", "status", "date")
    search_fields = ("description",)
    date_hierarchy = "date"
