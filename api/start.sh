#!/bin/sh
# Run Django migrations
export DJANGO_SETTINGS_MODULE=WaveAssistApi.settings
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_RESOURCE_ATTRIBUTES=service.name=waveassist-api
export OTEL_PYTHON_EXPERIMENTAL_ENABLE_METRICS=true
export OTEL_METRIC_EXPORTER=otlp

python manage.py migrate

# Start Celery beat
celery -A WaveAssistApi beat --loglevel=info &

# Start Celery Flower
celery -A WaveAssistApi flower --port=5555 --basic_auth=admin:admin &

# Start Gunicorn
#opentelemetry-instrument gunicorn --timeout 120 --bind 0.0.0.0:8000 WaveAssistApi.wsgi:application --workers 2
gunicorn --timeout 120 --bind 0.0.0.0:8000 WaveAssistApi.wsgi:application --workers 2