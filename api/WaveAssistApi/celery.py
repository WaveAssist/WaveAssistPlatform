import os
# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WaveAssistApi.settings')

from celery import Celery
from django.conf import settings

REDIS_URL = os.getenv('REDIS_URL')
if not REDIS_URL:
    raise RuntimeError("REDIS_URL is not set (no production default is baked in). Set it in this deployment's .env.")

# Configure the Django version of the Celery app to use the same broker and backend
app = Celery('WaveAssistApi',
             broker=REDIS_URL,
             backend=REDIS_URL
             )

# Load Celery settings from Django settings, the namespace 'CELERY' means all celery-related configuration keys
# should have a `CELERY_` prefix in your Django settings file
app.config_from_object(settings, namespace='CELERY')

# Set Celery to use the DatabaseScheduler from django-celery-beat
app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'
