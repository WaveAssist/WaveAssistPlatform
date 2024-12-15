import os
# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WaveAssistApi.settings')

from celery import Celery
from django.conf import settings

BROKER_URL = os.getenv('BROKER_URL', 'amqps://waveassist:REMOVED_CREDENTIAL@b-83686e9f-2c14-4878-91eb-96a9c4e00b8e.mq.us-east-1.amazonaws.com:5671')
# BACKEND_URL = os.getenv('BACKEND_URL', BROKER_URL)

# Configure the Django version of the Celery app to use the same broker and backend
app = Celery('WaveAssistApi',
             broker=BROKER_URL
             )


# Load Celery settings from Django settings, the namespace 'CELERY' means all celery-related configuration keys
# should have a `CELERY_` prefix in your Django settings file
app.config_from_object(settings, namespace='CELERY')

# Set Celery to use the DatabaseScheduler from django-celery-beat
app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'
