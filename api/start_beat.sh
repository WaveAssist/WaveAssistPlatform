#!/bin/sh
# Run Django migrations
export DJANGO_SETTINGS_MODULE=WaveAssistApi.settings
## Start Celery beat
gunicorn --timeout 120 --bind 0.0.0.0:8000 WaveAssistApi.wsgi:application --workers 1 &
celery -A WaveAssistApi beat --loglevel=info
