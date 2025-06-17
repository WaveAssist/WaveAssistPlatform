#!/bin/sh
# Run Django migrations
export DJANGO_SETTINGS_MODULE=WaveAssistApi.settings
## Start Celery beat
celery -A WaveAssistApi beat --loglevel=info
