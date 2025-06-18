#!/bin/sh

# Set Django settings module
export DJANGO_SETTINGS_MODULE=WaveAssistApi.settings

# Run the custom management command
python manage.py capture_celery_events
