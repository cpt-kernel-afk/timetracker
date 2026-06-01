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
"""Database models for the time tracker."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

HEX_COLOR_VALIDATOR = RegexValidator(
    regex=r"^#(?:[0-9a-fA-F]{3}){1,2}$",
    message="Color must be a hex value like #0d6efd or #abc.",
)


class Project(models.Model):
    """A project that time can be logged against."""

    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=7,
        default="#0d6efd",
        validators=[HEX_COLOR_VALIDATOR],
        help_text="Hex color (e.g. #0d6efd) used as a visual marker.",
    )
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional. If set, the report will calculate costs.",
    )
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["is_archived", "name"]

    def __str__(self) -> str:
        return self.name

    def total_minutes(self, since=None, until=None) -> int:
        """Sum of all completed time entries' duration in minutes."""
        qs = self.entries.filter(end_time__isnull=False)
        if since:
            qs = qs.filter(date__gte=since)
        if until:
            qs = qs.filter(date__lte=until)
        total = qs.aggregate(total=models.Sum("duration_minutes"))["total"]
        return int(total or 0)

    def total_hours(self, since=None, until=None) -> Decimal:
        minutes = self.total_minutes(since=since, until=until)
        return (Decimal(minutes) / Decimal(60)).quantize(Decimal("0.01"))

    def total_cost(self, since=None, until=None) -> Decimal | None:
        if self.hourly_rate is None:
            return None
        total = self.total_hours(since=since, until=until) * self.hourly_rate
        return total.quantize(Decimal("0.01"))

    @property
    def active_timer(self) -> TimeEntry | None:
        """Return the currently-running timer for this project, if any."""
        return self.entries.filter(end_time__isnull=True).order_by("-start_time").first()


class TimeEntry(models.Model):
    """A single time log entry against a project.

    A timer-managed entry is worked in one or more segments. ``status`` tracks
    its lifecycle, ``accumulated_minutes`` holds the time from completed
    segments, and ``segment_started_at`` marks the start of the currently
    running segment (``None`` while paused). ``start_time`` is the first start,
    ``end_time`` the final stop, and ``duration_minutes`` the worked total
    (excluding paused gaps). At most one entry may be ``RUNNING`` at a time.
    """

    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="entries")
    date = models.DateField(default=timezone.localdate)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Worked duration in minutes (excludes paused gaps).",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.COMPLETED,
    )
    accumulated_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Worked minutes from completed segments (before the live one).",
    )
    segment_started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Start of the currently running segment; null while paused.",
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-start_time", "-id"]
        verbose_name_plural = "Time entries"

    def __str__(self) -> str:
        return f"{self.project.name} · {self.date} · {self.duration_display}"

    def save(self, *args, **kwargs):
        # Derive duration from the span only for simple entries that never used
        # pause/resume. Timer-managed entries set duration_minutes in stop().
        if self.start_time and self.end_time and self.accumulated_minutes == 0:
            delta: timedelta = self.end_time - self.start_time
            self.duration_minutes = max(0, int(delta.total_seconds() // 60))
            if not self.date:
                self.date = timezone.localdate(self.start_time)
        super().save(*args, **kwargs)

    # ----- Timer lifecycle -----

    def _segment_minutes(self, when) -> int:
        """Minutes elapsed in the currently running segment, if any."""
        if not self.segment_started_at:
            return 0
        delta = when - self.segment_started_at
        return max(0, int(delta.total_seconds() // 60))

    def pause(self, when=None) -> None:
        """Hold a running timer: bank the live segment, stop counting."""
        if self.status != self.Status.RUNNING:
            return
        when = when or timezone.now()
        self.accumulated_minutes += self._segment_minutes(when)
        self.segment_started_at = None
        self.status = self.Status.PAUSED
        self.save(update_fields=["accumulated_minutes", "segment_started_at", "status"])

    def resume(self, when=None) -> None:
        """Make this the active timer, holding any other running one."""
        when = when or timezone.now()
        for other in TimeEntry.objects.filter(status=self.Status.RUNNING).exclude(pk=self.pk):
            other.pause(when=when)
        self.segment_started_at = when
        self.status = self.Status.RUNNING
        self.save(update_fields=["segment_started_at", "status"])

    def stop(self, when=None) -> None:
        """Finalize the session into a completed entry."""
        when = when or timezone.now()
        if self.status == self.Status.RUNNING:
            self.accumulated_minutes += self._segment_minutes(when)
            self.segment_started_at = None
        self.end_time = when
        self.duration_minutes = self.accumulated_minutes
        self.status = self.Status.COMPLETED
        self.save()

    # ----- State helpers -----

    @property
    def is_running(self) -> bool:
        return self.status == self.Status.RUNNING

    @property
    def is_paused(self) -> bool:
        return self.status == self.Status.PAUSED

    @property
    def is_open(self) -> bool:
        """Running or paused — an unfinished session shown on the dashboard."""
        return self.status in (self.Status.RUNNING, self.Status.PAUSED)

    @property
    def duration_display(self) -> str:
        minutes = self.current_duration_minutes()
        hours, mins = divmod(minutes, 60)
        return f"{hours:d}h {mins:02d}m"

    def current_duration_minutes(self) -> int:
        """Worked minutes so far: banked segments plus the live one if running."""
        if self.status == self.Status.RUNNING:
            return self.accumulated_minutes + self._segment_minutes(timezone.now())
        if self.status == self.Status.PAUSED:
            return self.accumulated_minutes
        return self.duration_minutes

    def clean(self):
        if self.start_time and self.end_time and self.end_time < self.start_time:
            raise ValidationError("End time must be after start time.")
