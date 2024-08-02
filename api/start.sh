#!/bin/sh
# Run Django migrations
python manage.py migrate

# Start Celery beat
celery -A WaveAssistApi beat --loglevel=info &

# Start Celery Flower
celery -A WaveAssistApi flower --port=5555 --basic_auth=wave:REMOVED_CREDENTIAL &

# Start Gunicorn
gunicorn --bind 0.0.0.0:8000 WaveAssistApi.wsgi:application
