# Time Tracker

A small, self-hosted web tool to track time on personal or freelance projects.
Built with Django, PostgreSQL, and Bootstrap; ships as a single `docker compose
up` away from running.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Django 5.0](https://img.shields.io/badge/django-5.0-092e20.svg)](https://www.djangoproject.com/)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED.svg)](https://docs.docker.com/compose/)

---

## Features

- **Projects** — create, edit, archive and delete projects, each with a color
  marker and an optional hourly rate.
- **Manual time entries** — pick a date, start and end time; duration is
  computed automatically.
- **Live timer with pause/hold** — start a timer on any project from the
  dashboard, with a live JS counter. Only one timer runs at a time; starting or
  resuming another automatically puts the running one **on hold** instead of
  stopping it, so you can switch between projects with a single click and resume
  later. Each timer has pause / resume / stop controls, and worked time is
  tracked across segments (paused gaps are excluded).
- **Dashboard** — today / this week / this month totals per project, plus the
  most recent entries.
- **PDF report** — generated server-side with WeasyPrint. Filter by date range
  and project; per-project subtotals plus grand total. Optional cost calculation
  when an hourly rate is set.
- **CSV export** of the same data.
- **Authentication required** on every page; built-in login / logout / change-password.
- **Django admin** at `/admin/` as a power-user fallback.
- **Bundled offline** — Bootstrap 5 and Bootstrap Icons are vendored locally,
  no CDN required.

## Architecture

```
   Browser ──► Apache (port 80) ──► Gunicorn (127.0.0.1:8001) ──► Django
                     │
                     └─► /static/  (served straight from disk)
```

Apache and Gunicorn run in the same `web` container managed by `supervisord`.
PostgreSQL runs in a separate `db` container with a named volume for
persistence. The database schema is created automatically on first start via
Django migrations.

## Quick start

Prerequisites: Docker 24+ with the Compose plugin.

```bash
# 1. Clone
git clone https://github.com/cpt-kernel-afk/timetracker.git
cd timetracker

# 2. Configure
cp .env.example .env
# Open .env and at minimum set:
#   DJANGO_SECRET_KEY  (generate one — see below)
#   POSTGRES_PASSWORD
#   DJANGO_ALLOWED_HOSTS (your hostname or "localhost")

# Generate a SECRET_KEY:
python -c 'import secrets; print(secrets.token_urlsafe(64))'

# 3. Build and start
docker compose up -d --build

# 4. Create your admin user
docker compose exec web python manage.py createsuperuser

# 5. Open the app
#    http://localhost:8080
```

That's it. The PostgreSQL schema is created automatically on the first start.

## Configuration

All configuration lives in `.env`. See [`.env.example`](.env.example) for the
full list of variables; the most important ones:

| Variable | Required | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | yes | Cryptographic key for sessions/CSRF. Generate a fresh one. |
| `DJANGO_DEBUG` | no | Default `False`. Never `True` in production. |
| `DJANGO_ALLOWED_HOSTS` | yes | Comma-separated hostnames the app accepts. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | when using HTTPS or proxy | Full origins with scheme. |
| `DJANGO_BEHIND_HTTPS_PROXY` | when behind a TLS-terminating proxy | Trust `X-Forwarded-Proto`. |
| `DJANGO_COOKIE_SECURE` | for HTTPS deployments | Mark session/CSRF cookies as Secure. |
| `DJANGO_HSTS` | for HTTPS deployments | Enable HSTS. |
| `POSTGRES_PASSWORD` | yes | PostgreSQL password. |
| `WEB_PORT` | no | Host port (default `8080`). |
| `TZ` | no | Container time zone (default `UTC`). |

## Usage

### Live timer

From the dashboard, click **Start Timer** on any project card. The timer ticks
live; use **Pause** to put it on hold (it stops counting but stays open),
**Resume** to continue, **Stop & Save** to write the entry, or **Discard** to
throw it away. Starting or resuming a timer on another project automatically
puts the currently running one on hold, so you can hop between projects with a
single click. Held timers are listed in an **On hold** section on the
dashboard; only one timer runs at a time.

### Manual entry

Click **Log Time** in the top bar. Pick a project, set start and end times, add
a description. Duration is computed for you.

### Reports

Go to **Report** in the navbar. Optionally pick a date range and/or specific
projects, then click **Generate PDF** (opens in a new tab) or **Download CSV**.

## Behind another reverse proxy

If you put Traefik, nginx, Caddy or similar in front of this container, set:

```env
DJANGO_ALLOWED_HOSTS=timetracker.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://timetracker.example.com
DJANGO_BEHIND_HTTPS_PROXY=True
DJANGO_COOKIE_SECURE=True
DJANGO_HSTS=True
```

Make sure your outer proxy forwards `Host` and `X-Forwarded-Proto` headers.
The internal Apache trusts these and passes them on to Django.

## Development without Docker

Requirements: Python 3.12+, PostgreSQL 14+, build tools for psycopg, and the
WeasyPrint system libraries (pango, cairo, harfbuzz — see the
[WeasyPrint install docs](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html)).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # adjust POSTGRES_HOST to localhost
createdb timetracker
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Running the tests

With Docker:

```bash
docker compose exec web python manage.py test tracker
```

Without Docker (using an in-memory SQLite database via a tiny override module):

```bash
# create test_settings.py at the project root with:
#   from config.settings import *
#   DATABASES = {'default': {'ENGINE':'django.db.backends.sqlite3','NAME':':memory:'}}

DJANGO_SECRET_KEY=test DJANGO_DEBUG=True \
python manage.py test tracker --settings=test_settings
```

The current suite covers models, auth gating on every endpoint, the live timer
flow, redirect safety, and PDF/CSV report generation.

## Project layout

```
.
├── config/                 Django project (settings, urls, wsgi)
│   ├── settings.py         Env-driven configuration with hardening toggles
│   ├── urls.py             Root URL conf + auth views
│   └── wsgi.py
├── tracker/                The time tracker app
│   ├── models.py           Project & TimeEntry
│   ├── views.py            All endpoints, @login_required
│   ├── forms.py            ModelForms + ReportFilterForm
│   ├── urls.py             App URLs
│   ├── admin.py            Django admin registration
│   ├── tests.py            Test suite
│   ├── migrations/
│   └── templates/tracker/  HTML templates
├── templates/registration/ Login / password-change templates
├── static/
│   ├── bootstrap/          Bootstrap 5 CSS/JS (local copy)
│   ├── bootstrap-icons/    Bootstrap Icons (local copy)
│   └── css/style.css       Custom styles
├── docker/
│   ├── apache-django.conf  Apache vhost (reverse proxy)
│   ├── supervisord.conf    Apache + Gunicorn process management
│   └── entrypoint.sh       Wait for DB, migrate, collectstatic, run
├── Dockerfile              Apache + Gunicorn + WeasyPrint deps
├── docker-compose.yml      web + postgres
├── requirements.txt
├── manage.py
├── LICENSE                 GNU GPL v3
├── AUTHORS
├── CONTRIBUTING.md
├── SECURITY.md
└── CHANGELOG.md
```

## Data model

- **Project**: `name` (unique), `description`, `color` (validated hex),
  `hourly_rate` (optional), `is_archived`, `created_at`
- **TimeEntry**: `project` (FK, CASCADE), `date`, `start_time` (first start),
  `end_time` (final stop), `status` (`running` / `paused` / `completed`),
  `accumulated_minutes` (worked time from completed segments),
  `segment_started_at` (start of the live segment; `NULL` while paused),
  `duration_minutes` (worked total, excludes paused gaps), `description`,
  `created_at`

An open timer is a `TimeEntry` with `end_time = NULL` and a `status` of
`running` or `paused`. While running, worked time is `accumulated_minutes` plus
the live segment since `segment_started_at`; pausing banks the live segment
into `accumulated_minutes`. Stopping writes the worked total into
`duration_minutes`. At most one entry is `running` at a time.

## Troubleshooting

- **Gateway timeout in the browser, container `healthy` in `docker compose
  ps`** — Your outer reverse proxy isn't reaching the container, or isn't
  forwarding `Host`/`X-Forwarded-Proto`. Verify with a direct call:
  `curl -i http://<host>:8080/login/`
- **`Bad Request (400) — Disallowed Host`** — Add the hostname you use in
  the browser to `DJANGO_ALLOWED_HOSTS`.
- **`CSRF verification failed`** — Add the full origin (with `https://`) to
  `DJANGO_CSRF_TRUSTED_ORIGINS`.
- **`The above exception ... was the direct cause of: django.db.utils.OperationalError`** —
  Database isn't reachable. Check `docker compose logs db`.
- **Logs**:
  - `docker compose logs -f web` — Apache + Gunicorn (interleaved via supervisord)
  - `docker compose logs -f db` — PostgreSQL

## Security

- Every page requires authentication.
- CSRF, clickjacking, content-type sniffing protections enabled by default.
- Open-redirect protection on the `next` parameter (validated against the
  current host).
- HSTS and Secure-Cookie flags are **opt-in** to avoid breaking HTTP-only
  setups, but should be enabled in any internet-facing deployment — see
  [SECURITY.md](SECURITY.md).
- App refuses to start in non-DEBUG mode without an explicit `SECRET_KEY`.
- Bundled dependencies are pinned in `requirements.txt`; rebuild the image
  periodically (`docker compose build --pull`) for upstream updates.

To report a vulnerability, see [SECURITY.md](SECURITY.md).

## Contributing

Pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the
process, coding conventions, and how to run the test suite.

## Authors

- **c4pt4in** — project owner ([github.com/cpt-kernel-afk](https://github.com/cpt-kernel-afk))
- **Claude** (Anthropic AI assistant) — initial scaffold and implementation

See [AUTHORS](AUTHORS) for the full list.

## License

Time Tracker is free software, licensed under the **GNU General Public License
v3.0 or later**. See [LICENSE](LICENSE) for the full text.

```
Time Tracker — a self-hosted project time tracking web app.
Copyright (C) 2026 c4pt4in and contributors.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
```
