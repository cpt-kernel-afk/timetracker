# syntax=docker/dockerfile:1.6
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# System dependencies:
#  - apache2: web server (reverse proxy in front of gunicorn)
#  - supervisor: process manager for apache + gunicorn in one container
#  - libpq-dev / gcc: psycopg build helpers
#  - WeasyPrint runtime dependencies (pango, harfbuzz, cairo, fonts)
RUN apt-get update && apt-get install -y --no-install-recommends \
        apache2 \
        supervisor \
        gcc \
        libpq-dev \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        shared-mime-info \
        fonts-dejavu \
        fontconfig \
        netcat-openbsd \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy app
COPY . /app

# Prepare directories
RUN mkdir -p /app/staticfiles /var/log/supervisor /var/log/gunicorn \
    && chown -R www-data:www-data /app /var/log/gunicorn

# Apache config: reverse proxy to gunicorn on 127.0.0.1:8001
COPY docker/apache-django.conf /etc/apache2/sites-available/000-default.conf
RUN a2enmod proxy proxy_http headers \
    && a2dissite default-ssl 2>/dev/null || true \
    && a2ensite 000-default

# Supervisord config: runs apache + gunicorn together
COPY docker/supervisord.conf /etc/supervisor/conf.d/timetracker.conf

# Entrypoint: wait for db, migrate, collectstatic, optionally create superuser, then exec CMD
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
