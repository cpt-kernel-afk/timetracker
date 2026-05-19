# Contributing to Time Tracker

Thank you for considering a contribution! Anything from typo fixes to new
features is welcome. Please skim this short guide before opening a PR.

## Reporting bugs

1. Search the [issue tracker](https://github.com/c4pt4in/timetracker/issues)
   first — your bug may already be filed.
2. If not, open a new issue and include:
   - What you did, what happened, what you expected to happen.
   - The exact error message or screenshot.
   - Your environment: Docker version, host OS, browser.
   - Relevant log output (`docker compose logs --tail=200 web`).

## Suggesting features

Open an issue with the **enhancement** label. Describe the use case first,
the implementation idea second — the *why* is more useful than the *how*.

## Submitting changes

1. Fork the repo and create a topic branch from `main`:
   ```bash
   git checkout -b feature/short-description
   ```
2. Make your change. Keep commits focused — one logical change per commit.
3. Run the test suite locally:
   ```bash
   docker compose exec web python manage.py test tracker
   ```
   …or without Docker, against SQLite:
   ```bash
   DJANGO_SECRET_KEY=dev DJANGO_DEBUG=True \
   python manage.py test tracker --settings=test_settings
   ```
4. Add tests for new behaviour. The bar isn't 100 % coverage but new code
   paths should be exercised.
5. Run Django's system checks: `python manage.py check`
6. Push your branch and open a pull request against `main`. Describe what
   changed and why. Link related issues.

## Code style

* Python: follow PEP 8 and the project's existing style. Type hints on
  function signatures where they aid clarity.
* Django: prefer Django's built-ins (forms, ORM, auth) over reinventing.
* Templates: Bootstrap 5 utility classes, minimal inline styles.
* Keep dependencies lean — adding a package needs a justification.

## Security issues

Please **do not** open a public issue for security vulnerabilities. Email
the maintainer (see the project page on GitHub for contact info) with a
description and reproduction steps. We'll acknowledge within a few days.

## License of contributions

By contributing you agree that your contributions will be licensed under
the project's [GNU GPL v3](LICENSE).
