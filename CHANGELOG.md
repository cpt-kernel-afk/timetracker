# Changelog

All notable changes to this project will be documented in this file. The
format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0]

### Added
- Pausable timers: multiple timer sessions can stay open at once, with exactly
  one running and the rest on hold.
- Pause / resume controls per timer, plus an **On hold** section on the
  dashboard.

### Changed
- Starting or resuming a timer now puts the currently running timer **on hold**
  (paused) instead of stopping it, so switching projects keeps prior sessions
  open. Starting a project that already has an open session resumes it rather
  than creating a duplicate.
- `TimeEntry` now tracks worked time across run/pause segments via new fields
  `status`, `accumulated_minutes` and `segment_started_at`; `duration_minutes`
  is the worked total and excludes paused gaps.

## [0.1.0] - Initial release

### Added
- Project CRUD (name, description, color, optional hourly rate, archive flag).
- Time entry CRUD with auto-calculated duration.
- Live timer with single-concurrent-timer policy and live JS counter.
- Dashboard with today / week / month totals per project.
- PDF report (WeasyPrint) with date range filter, project filter, optional
  cost calculation, per-project subtotals and a grand total.
- CSV export of the same report data.
- Built-in Django admin interface.
- Authentication required on every endpoint; built-in login / logout /
  password-change views.
- Apache + Gunicorn + supervisord container, PostgreSQL 16, docker compose.
- Bootstrap 5 and Bootstrap Icons bundled locally (no CDN).
- Test suite covering models, auth gating, timer flow, redirect safety, and
  report generation.

[Unreleased]: https://github.com/c4pt4in/timetracker/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/c4pt4in/timetracker/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/c4pt4in/timetracker/releases/tag/v0.1.0
