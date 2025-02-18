import os
DEBUG = True
from config import *

##Main constants
ACCOUNT_ID = os.getenv('ACCOUNT_ID', ACCOUNT_ID)
# REDIS_URL = os.getenv('REDIS_URL', 'redis://master.rediswa.lqjglu.use1.cache.amazonaws.com:6379/0')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
QUEUE_NAME = 'queue_' + ACCOUNT_ID

##Other logs
S_SYSTEM_VERSION = 'V1.0 - WaveAssistEngineDocker'
LOG_NUMBER = 10
CWD_PATH = os.getcwd()
PROJECT_LOGS_PATH = os.path.join(CWD_PATH, 'Logs','project_logs.log')
ACCOUNT_KEY = 'WaveAssist'
BASE_URL = "https://api.waveassist.io"
TIMEOUT_DURATION = 300
INTEGRATION_SUFFIX = "_integrations"

##Keys:
PD_DATA_KEY = 'PDData'
IO_DATA_KEY = 'IODataKey'
DATA_KEY = "DATA"
IS_SYSTEM_TASK= "is_system_task"


