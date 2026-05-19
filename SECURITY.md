# Security Policy

## Reporting a vulnerability

If you believe you have found a security vulnerability in Time Tracker,
please **do not** open a public GitHub issue. Instead, contact the
maintainer privately through their GitHub profile and include:

* A clear description of the issue.
* Steps to reproduce.
* The version (commit hash) you tested against.
* Any suggested mitigation, if you have one.

You should receive an initial acknowledgement within a few days. We aim
to release a patch (or publish a workaround) within 30 days of triage,
depending on severity.

## Supported versions

This project is small and moves linearly. Only the latest commit on
`main` is officially supported. If you run an older version please
update before reporting an issue.

## Hardening checklist for deployments

Time Tracker is shipped with safe defaults but a few choices are left
to the operator. Before exposing it on the internet, make sure to:

* Set a strong `DJANGO_SECRET_KEY` (the app refuses to start without one
  outside `DEBUG`).
* Set `DJANGO_DEBUG=False`.
* Restrict `DJANGO_ALLOWED_HOSTS` to the hostname(s) you actually use.
* Set `DJANGO_CSRF_TRUSTED_ORIGINS` with the full origin (incl. scheme).
* Terminate HTTPS at a reverse proxy in front of the container and set
  `DJANGO_BEHIND_HTTPS_PROXY=True`, `DJANGO_COOKIE_SECURE=True`, and
  `DJANGO_HSTS=True` once you have confirmed HTTPS works.
* Change the default Postgres password.
* Create your admin user via `manage.py createsuperuser` rather than using
  the one-shot bootstrap env vars, or remove those env vars after first
  start.
* Keep the underlying images updated: rebuild with `docker compose build
  --pull` periodically.
