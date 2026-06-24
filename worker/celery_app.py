from celery import Celery
from Utils.constants import *

# Setup Celery
app = Celery('waveassist',
             broker=REDIS_URL,
             backend=REDIS_URL)
app.conf.task_default_queue = QUEUE_NAME

# Time limits + visibility timeout. The golden rule that makes runaway/looping
# tasks impossible:  soft_time_limit < hard time_limit < visibility_timeout.
# Calibrated to allow legitimate tasks up to ~2h.
app.conf.task_soft_time_limit = 2 * 60 * 60          # 2h  -> raises SoftTimeLimitExceeded (catchable)
app.conf.task_time_limit = 2 * 60 * 60 + 15 * 60     # 2h15m -> force-kills the worker child
# Visibility timeout must stay ABOVE the hard limit so Redis never assumes the
# worker died and redelivers a task that is still legitimately running.
app.conf.broker_transport_options = {'visibility_timeout': 3 * 60 * 60}  # 3h
