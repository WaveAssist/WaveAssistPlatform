#!/bin/sh
# Run Django migrations
python manage.py migrate

# Start Celery beat
celery -A WaveAssistApi beat --loglevel=info &

# Start Celery Flower
celery -A WaveAssistApi flower --port=5555 --basic_auth=admin:admin &

# Start Gunicorn
gunicorn --timeout 120 --bind 0.0.0.0:8000 WaveAssistApi.wsgi:application --workers 1
