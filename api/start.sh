#!/bin/sh
set -eu
export DJANGO_SETTINGS_MODULE=WaveAssistApi.settings
python manage.py migrate --noinput
if [ "${WA_BOOTSTRAP_ADMIN:-0}" = "1" ]; then
  python manage.py seed_admin
fi
exec gunicorn --timeout 120 --bind 0.0.0.0:8000 WaveAssistApi.wsgi:application --workers "${WEB_CONCURRENCY:-2}"
