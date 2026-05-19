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
"""Django settings for the timetracker project.

Settings are configured through environment variables (loaded from .env in dev).
See .env.example for the full list of supported variables.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env if present (no-op when env vars are provided directly, e.g. in Docker)
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Core security settings
# ---------------------------------------------------------------------------
DEBUG = env_bool("DJANGO_DEBUG", False)

# SECRET_KEY: must be set explicitly outside DEBUG. We refuse to start with
# a weak default in production — fail fast is safer than a deceptive boot.
_INSECURE_DEFAULT = "django-insecure-dev-only-DO-NOT-USE-IN-PRODUCTION"
_MGMT_CMDS_OK_WITHOUT_KEY = {"makemigrations", "migrate", "collectstatic", "check", "shell", "test"}
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG or any(cmd in sys.argv for cmd in _MGMT_CMDS_OK_WITHOUT_KEY):
        SECRET_KEY = _INSECURE_DEFAULT
    else:
        raise RuntimeError(
            "DJANGO_SECRET_KEY is not set. Generate one (e.g. with "
            "`python -c 'import secrets; print(secrets.token_urlsafe(64))'`) "
            "and put it in your .env file."
        )

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()
] or (["*"] if DEBUG else ["localhost", "127.0.0.1"])

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]

# ---------------------------------------------------------------------------
# Applications and middleware
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "crispy_forms",
    "crispy_bootstrap5",
    "tracker",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database (PostgreSQL via psycopg)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "timetracker"),
        "USER": os.environ.get("POSTGRES_USER", "timetracker"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "timetracker"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": int(os.environ.get("DJANGO_DB_CONN_MAX_AGE", "60")),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# i18n / static files
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("TZ", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Forms / auth
# ---------------------------------------------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "tracker:dashboard"
LOGOUT_REDIRECT_URL = "login"

# ---------------------------------------------------------------------------
# Reverse-proxy / production hardening
# ---------------------------------------------------------------------------
# Only trust X-Forwarded-Proto when explicitly opted in. Safe when (and only when)
# a reverse proxy you control sets this header — otherwise clients can fake it.
if env_bool("DJANGO_BEHIND_HTTPS_PROXY", False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True

if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True

    # Opt-in via env: enable secure-cookie flags / HSTS only when actually behind HTTPS
    if env_bool("DJANGO_COOKIE_SECURE", False):
        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True
    if env_bool("DJANGO_HSTS", False):
        SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "31536000"))
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD = True

# ---------------------------------------------------------------------------
# Logging — log to stdout so docker/supervisord can pick it up
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{levelname} {asctime} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
