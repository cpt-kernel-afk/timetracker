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
"""Views for the time tracker.

All views require an authenticated user. Redirect targets supplied via ``?next=``
or POST ``next`` are validated against ``ALLOWED_HOSTS`` to prevent open redirects.
"""
from __future__ import annotations

import csv
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render, resolve_url
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from weasyprint import HTML

from .forms import ProjectForm, ReportFilterForm, TimeEntryForm
from .models import Project, TimeEntry


# ---------- Helpers ----------

def _safe_next(request, fallback: str = "tracker:dashboard") -> str:
    """Return a safe redirect target.

    Accepts the ``next`` parameter only when it points to the same host/scheme.
    Falls back to the named URL otherwise.
    """
    candidate = request.POST.get("next") or request.GET.get("next")
    if candidate and url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return resolve_url(fallback)


# ---------- Dashboard ----------

@login_required
def dashboard(request):
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    active_projects = Project.objects.filter(is_archived=False)

    project_stats = []
    for project in active_projects:
        project_stats.append({
            "project": project,
            "today_h": project.total_hours(since=today, until=today),
            "week_h": project.total_hours(since=week_start, until=today),
            "month_h": project.total_hours(since=month_start, until=today),
            "active_timer": project.active_timer,
        })

    running = TimeEntry.objects.filter(end_time__isnull=True).select_related("project")
    recent_entries = (
        TimeEntry.objects.filter(end_time__isnull=False)
        .select_related("project")
        .order_by("-date", "-end_time")[:10]
    )

    return render(request, "tracker/dashboard.html", {
        "project_stats": project_stats,
        "running": running,
        "recent_entries": recent_entries,
        "today": today,
    })


# ---------- Projects ----------

@login_required
def project_list(request):
    show_archived = request.GET.get("archived") == "1"
    projects = Project.objects.all() if show_archived else Project.objects.filter(is_archived=False)
    projects = projects.annotate(total_minutes_db=Sum("entries__duration_minutes"))
    return render(request, "tracker/project_list.html", {
        "projects": projects,
        "show_archived": show_archived,
    })


@login_required
def project_detail(request, pk: int):
    project = get_object_or_404(Project, pk=pk)
    entries = project.entries.all()
    return render(request, "tracker/project_detail.html", {
        "project": project,
        "entries": entries,
        "total_minutes": project.total_minutes(),
        "total_hours": project.total_hours(),
        "total_cost": project.total_cost(),
    })


@login_required
def project_create(request):
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save()
            messages.success(request, f"Project '{project.name}' created.")
            return redirect("tracker:project_detail", pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, "tracker/project_form.html", {"form": form, "title": "New Project"})


@login_required
def project_update(request, pk: int):
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, "Project updated.")
            return redirect("tracker:project_detail", pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    return render(request, "tracker/project_form.html", {
        "form": form,
        "title": f"Edit Project · {project.name}",
        "project": project,
    })


@login_required
def project_delete(request, pk: int):
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        name = project.name
        project.delete()
        messages.success(request, f"Project '{name}' deleted.")
        return redirect("tracker:project_list")
    return render(request, "tracker/project_confirm_delete.html", {"project": project})


# ---------- Time entries ----------

@login_required
def timeentry_create(request):
    initial = {}
    project_id = request.GET.get("project")
    if project_id and project_id.isdigit():
        initial["project"] = int(project_id)
    if request.method == "POST":
        form = TimeEntryForm(request.POST)
        if form.is_valid():
            entry = form.save()
            messages.success(request, "Time entry saved.")
            return redirect("tracker:project_detail", pk=entry.project_id)
    else:
        form = TimeEntryForm(initial=initial)
    return render(request, "tracker/timeentry_form.html", {"form": form, "title": "Log Time"})


@login_required
def timeentry_update(request, pk: int):
    entry = get_object_or_404(TimeEntry, pk=pk)
    if request.method == "POST":
        form = TimeEntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, "Time entry updated.")
            return redirect("tracker:project_detail", pk=entry.project_id)
    else:
        form = TimeEntryForm(instance=entry)
    return render(request, "tracker/timeentry_form.html", {
        "form": form,
        "title": "Edit Time Entry",
        "entry": entry,
    })


@login_required
def timeentry_delete(request, pk: int):
    entry = get_object_or_404(TimeEntry, pk=pk)
    if request.method == "POST":
        project_id = entry.project_id
        entry.delete()
        messages.success(request, "Time entry deleted.")
        return redirect("tracker:project_detail", pk=project_id)
    return render(request, "tracker/timeentry_confirm_delete.html", {"entry": entry})


# ---------- Live timer ----------

@login_required
@require_POST
def timer_start(request, project_id: int):
    project = get_object_or_404(Project, pk=project_id, is_archived=False)
    # Stop other running timers (single-concurrent-timer policy)
    other_running = TimeEntry.objects.filter(end_time__isnull=True).exclude(project=project)
    now = timezone.now()
    for r in other_running:
        r.end_time = now
        r.save()
        messages.info(request, f"Stopped running timer on '{r.project.name}'.")
    if not project.active_timer:
        TimeEntry.objects.create(
            project=project,
            date=timezone.localdate(),
            start_time=now,
            description=request.POST.get("description", ""),
        )
        messages.success(request, f"Timer started for '{project.name}'.")
    return redirect(_safe_next(request))


@login_required
@require_POST
def timer_stop(request, entry_id: int):
    entry = get_object_or_404(TimeEntry, pk=entry_id, end_time__isnull=True)
    entry.end_time = timezone.now()
    entry.description = request.POST.get("description", entry.description) or entry.description
    entry.save()
    messages.success(request, f"Timer stopped — logged {entry.duration_display}.")
    return redirect(_safe_next(request))


@login_required
@require_POST
def timer_cancel(request, entry_id: int):
    entry = get_object_or_404(TimeEntry, pk=entry_id, end_time__isnull=True)
    project_name = entry.project.name
    entry.delete()
    messages.warning(request, f"Running timer for '{project_name}' was discarded.")
    return redirect(_safe_next(request))


# ---------- Reports ----------

def _build_report_context(form: ReportFilterForm) -> dict:
    date_from = form.cleaned_data.get("date_from")
    date_to = form.cleaned_data.get("date_to")
    selected_projects = form.cleaned_data.get("projects")
    include_archived = form.cleaned_data.get("include_archived")

    projects_qs = Project.objects.all()
    if selected_projects:
        projects_qs = projects_qs.filter(pk__in=[p.pk for p in selected_projects])
    elif not include_archived:
        projects_qs = projects_qs.filter(is_archived=False)

    project_blocks = []
    grand_total_minutes = 0
    grand_total_cost = Decimal("0.00")
    any_costs = False

    for project in projects_qs:
        entries_qs = project.entries.filter(end_time__isnull=False)
        if date_from:
            entries_qs = entries_qs.filter(date__gte=date_from)
        if date_to:
            entries_qs = entries_qs.filter(date__lte=date_to)
        entries = list(entries_qs.order_by("date", "start_time"))
        total_minutes = sum(e.duration_minutes for e in entries)
        total_hours = (Decimal(total_minutes) / Decimal(60)).quantize(Decimal("0.01"))
        cost = None
        if project.hourly_rate is not None:
            cost = (total_hours * project.hourly_rate).quantize(Decimal("0.01"))
            grand_total_cost += cost
            any_costs = True

        project_blocks.append({
            "project": project,
            "entries": entries,
            "total_minutes": total_minutes,
            "total_hours": total_hours,
            "cost": cost,
        })
        grand_total_minutes += total_minutes

    grand_total_hours = (Decimal(grand_total_minutes) / Decimal(60)).quantize(Decimal("0.01"))

    return {
        "project_blocks": project_blocks,
        "grand_total_minutes": grand_total_minutes,
        "grand_total_hours": grand_total_hours,
        "grand_total_cost": grand_total_cost if any_costs else None,
        "any_costs": any_costs,
        "date_from": date_from,
        "date_to": date_to,
        "generated_at": timezone.now(),
    }


@login_required
def report_form(request):
    form = ReportFilterForm(request.GET)
    return render(request, "tracker/report_form.html", {"form": form})


@login_required
def report_pdf(request):
    form = ReportFilterForm(request.GET)
    if not form.is_valid():
        return redirect("tracker:report_form")
    context = _build_report_context(form)
    html_string = render_to_string("tracker/report_pdf.html", context)
    pdf_bytes = HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf()
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    filename = f"timetracker-report-{timezone.localdate().isoformat()}.pdf"
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


@login_required
def report_csv(request):
    form = ReportFilterForm(request.GET)
    if not form.is_valid():
        return redirect("tracker:report_form")
    context = _build_report_context(form)

    response = HttpResponse(content_type="text/csv")
    filename = f"timetracker-report-{timezone.localdate().isoformat()}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(["Project", "Date", "Start", "End", "Duration (minutes)", "Duration (hours)", "Description"])
    for block in context["project_blocks"]:
        for e in block["entries"]:
            hours = (Decimal(e.duration_minutes) / Decimal(60)).quantize(Decimal("0.01"))
            writer.writerow([
                block["project"].name,
                e.date.isoformat(),
                e.start_time.isoformat() if e.start_time else "",
                e.end_time.isoformat() if e.end_time else "",
                e.duration_minutes,
                hours,
                e.description.replace("\n", " "),
            ])
        writer.writerow([
            f"TOTAL · {block['project'].name}",
            "", "", "",
            block["total_minutes"],
            block["total_hours"],
            "",
        ])
    writer.writerow([])
    writer.writerow([
        "GRAND TOTAL", "", "", "",
        context["grand_total_minutes"],
        context["grand_total_hours"],
        "",
    ])
    return response
