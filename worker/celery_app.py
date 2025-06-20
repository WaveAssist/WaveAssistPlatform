from celery import Celery
from Utils.constants import *

# Setup Celery
app = Celery('waveassist',
             broker=REDIS_URL,
             backend=REDIS_URL)
app.conf.task_default_queue = QUEUE_NAME