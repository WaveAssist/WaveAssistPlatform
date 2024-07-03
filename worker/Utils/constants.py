import os
DEBUG = True
S_SYSTEM_VERSION = 'V1.0 - WaveAssistEngineDocker'
LOG_NUMBER = 10
CWD_PATH = os.getcwd()
PROJECT_LOGS_PATH = os.path.join(CWD_PATH, 'Logs','project_logs.log')
BASE_URL = "https://assistapi.wavepredict.com"
TIMEOUT_DURATION = 300
INTEGRATION_SUFFIX = "_integrations"

##Keys:
PD_DATA_KEY = 'PDData'
IO_DATA_KEY = 'IODataKey'
DATA_KEY = "DATA"
DB_NAME = "WaveAssist"
CONNECTION_STRING = "REMOVED_CREDENTIAL"
INTEGRATIONS_SUFFIX_KEY = "_integrations"
RABBIT_HOST = 'rabbitmq'
RABBIT_PORT = 5672
RABBIT_QUEUE = 'waveassist_shared_queue'
RABBIT_USER = 'waveassist'
RABBIT_PASSWORD = 'REMOVED_CREDENTIAL'
