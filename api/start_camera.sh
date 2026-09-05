#!/bin/sh
set -eu

# Set Django settings module
export DJANGO_SETTINGS_MODULE=WaveAssistApi.settings

# Run the custom management command
exec python manage.py capture_celery_events
