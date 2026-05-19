#!/usr/bin/env bash
# Entrypoint: prepare DB schema, collect static files, optionally create a superuser,
# then exec the supervised command.
set -e

DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"

echo "[entrypoint] Waiting for database at ${DB_HOST}:${DB_PORT}..."
for i in $(seq 1 60); do
    if nc -z "${DB_HOST}" "${DB_PORT}" 2>/dev/null; then
        echo "[entrypoint] Database is reachable."
        break
    fi
    sleep 1
    if [ "$i" = "60" ]; then
        echo "[entrypoint] Database did not become reachable in time."
        exit 1
    fi
done

echo "[entrypoint] Applying migrations (creates schema on first run)..."
python /app/manage.py migrate --noinput

echo "[entrypoint] Collecting static files..."
python /app/manage.py collectstatic --noinput

# Auto-create superuser if explicitly enabled. Only useful for first-time setup;
# for security, this should normally be set once and then removed from .env.
if [ "${DJANGO_AUTO_CREATE_SUPERUSER:-false}" = "true" ]; then
    if [ -n "${DJANGO_SUPERUSER_USERNAME}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD}" ]; then
        if [ "${DJANGO_SUPERUSER_PASSWORD}" = "admin" ] || [ "${DJANGO_SUPERUSER_PASSWORD}" = "changeme" ]; then
            echo "[entrypoint] WARNING: using a well-known default superuser password."
            echo "[entrypoint] WARNING: change it immediately after first login."
        fi
        echo "[entrypoint] Ensuring superuser '${DJANGO_SUPERUSER_USERNAME}' exists..."
        python /app/manage.py shell <<PY
from django.contrib.auth import get_user_model
User = get_user_model()
u = "${DJANGO_SUPERUSER_USERNAME}"
e = "${DJANGO_SUPERUSER_EMAIL:-admin@example.com}"
p = "${DJANGO_SUPERUSER_PASSWORD}"
if not User.objects.filter(username=u).exists():
    User.objects.create_superuser(u, e, p)
    print(f"[entrypoint] Superuser '{u}' created.")
else:
    print(f"[entrypoint] Superuser '{u}' already exists.")
PY
    fi
else
    # Helpful guidance when no users exist yet
    USER_COUNT=$(python /app/manage.py shell -c "from django.contrib.auth import get_user_model; print(get_user_model().objects.count())" 2>/dev/null | tail -1)
    if [ "${USER_COUNT}" = "0" ]; then
        echo "[entrypoint] No users yet. Create one with:"
        echo "    docker compose exec web python manage.py createsuperuser"
        echo "    (or set DJANGO_AUTO_CREATE_SUPERUSER=true for one-shot bootstrap)"
    fi
fi

# Apache needs to be able to read the collected static files
chown -R www-data:www-data /app/staticfiles 2>/dev/null || true

echo "[entrypoint] Starting: $*"
exec "$@"
