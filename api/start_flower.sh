#!/bin/sh
export DJANGO_SETTINGS_MODULE=WaveAssistApi.settings
celery -A WaveAssistApi flower --port=5555 --basic_auth=waveassist:REMOVED_CREDENTIAL
