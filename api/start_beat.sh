#!/bin/sh
set -eu
# Run Django migrations
export DJANGO_SETTINGS_MODULE=WaveAssistApi.settings
## Start Celery beat
exec celery -A WaveAssistApi beat --loglevel=DEBUG
