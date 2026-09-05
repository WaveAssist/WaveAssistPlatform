#!/bin/sh
set -eu
export DJANGO_SETTINGS_MODULE=WaveAssistApi.settings
exec celery -A WaveAssistApi flower --port=5555 --basic_auth="${FLOWER_BASIC_AUTH:?set FLOWER_BASIC_AUTH}"
