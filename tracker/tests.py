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
"""Tests for the time tracker.

Run with: python manage.py test tracker
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from tracker.models import Project, TimeEntry

User = get_user_model()


def _make_user(username="tester", password="pass-word-1234"):
    return User.objects.create_user(username=username, password=password)


class ProjectModelTests(TestCase):
    def test_str_and_defaults(self):
        p = Project.objects.create(name="Demo")
        self.assertEqual(str(p), "Demo")
        self.assertEqual(p.color, "#0d6efd")
        self.assertFalse(p.is_archived)

    def test_invalid_color_raises(self):
        p = Project(name="Bad", color="not-a-color")
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_totals_with_no_entries(self):
        p = Project.objects.create(name="Empty")
        self.assertEqual(p.total_minutes(), 0)
        self.assertEqual(p.total_hours(), Decimal("0.00"))
        self.assertIsNone(p.total_cost())

    def test_totals_aggregate_completed_entries(self):
        p = Project.objects.create(name="Sum", hourly_rate=Decimal("60.00"))
        now = timezone.now()
        TimeEntry.objects.create(project=p, start_time=now - timedelta(hours=2), end_time=now, date=now.date())
        TimeEntry.objects.create(
            project=p,
            start_time=now - timedelta(minutes=30),
            end_time=now,
            date=now.date(),
        )
        self.assertEqual(p.total_minutes(), 150)
        self.assertEqual(p.total_hours(), Decimal("2.50"))
        self.assertEqual(p.total_cost(), Decimal("150.00"))

    def test_running_entry_excluded_from_totals(self):
        p = Project.objects.create(name="Running")
        TimeEntry.objects.create(project=p, start_time=timezone.now(), date=timezone.localdate())
        self.assertEqual(p.total_minutes(), 0)
        self.assertIsNotNone(p.active_timer)


class TimeEntryModelTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="EntryTests")

    def test_duration_auto_calculated_from_times(self):
        now = timezone.now()
        e = TimeEntry.objects.create(
            project=self.project,
            start_time=now - timedelta(minutes=75),
            end_time=now,
            date=now.date(),
        )
        self.assertEqual(e.duration_minutes, 75)

    def test_end_before_start_raises(self):
        now = timezone.now()
        e = TimeEntry(project=self.project, start_time=now, end_time=now - timedelta(minutes=5))
        with self.assertRaises(ValidationError):
            e.full_clean()


class AuthGateTests(TestCase):
    """All tracker views must redirect anonymous users to the login page."""

    PROTECTED = [
        "tracker:dashboard",
        "tracker:project_list",
        "tracker:project_create",
        "tracker:timeentry_create",
        "tracker:report_form",
    ]

    def test_anonymous_user_is_redirected(self):
        c = Client()
        for name in self.PROTECTED:
            resp = c.get(reverse(name))
            self.assertEqual(resp.status_code, 302, f"{name} did not redirect")
            self.assertIn("/login/", resp.url, f"{name} did not redirect to login")


class TimerFlowTests(TestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.login(username="tester", password="pass-word-1234")
        self.project = Project.objects.create(name="Flow")

    def test_start_then_stop_creates_completed_entry(self):
        # Start
        resp = self.client.post(reverse("tracker:timer_start", args=[self.project.id]))
        self.assertEqual(resp.status_code, 302)
        running = TimeEntry.objects.filter(project=self.project, end_time__isnull=True).first()
        self.assertIsNotNone(running)
        # Stop
        resp = self.client.post(reverse("tracker:timer_stop", args=[running.id]))
        self.assertEqual(resp.status_code, 302)
        running.refresh_from_db()
        self.assertIsNotNone(running.end_time)

    def test_starting_second_timer_stops_first(self):
        a = Project.objects.create(name="A")
        b = Project.objects.create(name="B")
        self.client.post(reverse("tracker:timer_start", args=[a.id]))
        self.client.post(reverse("tracker:timer_start", args=[b.id]))
        # A is stopped, B is running
        self.assertFalse(TimeEntry.objects.filter(project=a, end_time__isnull=True).exists())
        self.assertTrue(TimeEntry.objects.filter(project=b, end_time__isnull=True).exists())

    def test_open_redirect_is_blocked(self):
        """The `next` parameter must not redirect to an external host."""
        resp = self.client.post(
            reverse("tracker:timer_start", args=[self.project.id]),
            {"next": "https://evil.example.com/steal"},
        )
        self.assertEqual(resp.status_code, 302)
        # Should fall back to dashboard, NOT redirect to the attacker
        self.assertNotIn("evil.example.com", resp.url)


class ReportTests(TestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.login(username="tester", password="pass-word-1234")
        self.project = Project.objects.create(name="Reportable", hourly_rate=Decimal("100.00"))
        now = timezone.now()
        TimeEntry.objects.create(
            project=self.project,
            start_time=now - timedelta(hours=1),
            end_time=now,
            date=now.date(),
        )

    def test_report_form_renders(self):
        resp = self.client.get(reverse("tracker:report_form"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Generate Report")

    def test_pdf_export_returns_pdf(self):
        resp = self.client.get(reverse("tracker:report_pdf"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        # PDF magic header
        self.assertTrue(resp.content.startswith(b"%PDF-"))

    def test_csv_export_contains_data(self):
        resp = self.client.get(reverse("tracker:report_csv"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")
        body = resp.content.decode()
        self.assertIn("Reportable", body)
        self.assertIn("GRAND TOTAL", body)
