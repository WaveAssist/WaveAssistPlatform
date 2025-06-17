#!/bin/sh
# Run Django migrations
export DJANGO_SETTINGS_MODULE=WaveAssistApi.settings

## OpenTelemetry Configuration (Optional)
#export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
#export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
#export OTEL_RESOURCE_ATTRIBUTES=service.name=waveassist-api
#export OTEL_PYTHON_EXPERIMENTAL_ENABLE_METRICS=true
#export OTEL_METRIC_EXPORTER=otlp
#opentelemetry-instrument gunicorn --timeout 120 --bind 0.0.0.0:8000 WaveAssistApi.wsgi:application --workers 2

python manage.py migrate

# Start Gunicorn
gunicorn --timeout 120 --bind 0.0.0.0:8000 WaveAssistApi.wsgi:application --workers 1