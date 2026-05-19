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
from django.urls import path

from . import views

app_name = "tracker"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # Projects
    path("projects/", views.project_list, name="project_list"),
    path("projects/new/", views.project_create, name="project_create"),
    path("projects/<int:pk>/", views.project_detail, name="project_detail"),
    path("projects/<int:pk>/edit/", views.project_update, name="project_update"),
    path("projects/<int:pk>/delete/", views.project_delete, name="project_delete"),
    # Time entries
    path("entries/new/", views.timeentry_create, name="timeentry_create"),
    path("entries/<int:pk>/edit/", views.timeentry_update, name="timeentry_update"),
    path("entries/<int:pk>/delete/", views.timeentry_delete, name="timeentry_delete"),
    # Live timer
    path("timer/start/<int:project_id>/", views.timer_start, name="timer_start"),
    path("timer/stop/<int:entry_id>/", views.timer_stop, name="timer_stop"),
    path("timer/cancel/<int:entry_id>/", views.timer_cancel, name="timer_cancel"),
    # Report
    path("report/", views.report_form, name="report_form"),
    path("report/pdf/", views.report_pdf, name="report_pdf"),
    path("report/csv/", views.report_csv, name="report_csv"),
]
