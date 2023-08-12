import os
CWD_PATH = os.getcwd()
PROJECT_LOGS_PATH = os.path.join(CWD_PATH, 'Logs','project_logs.log')
BASE_URL = "https://assistapi.wavepredict.com"
TIMEOUT_DURATION = 300
LOAD_ALL_PROJECTS_URL = BASE_URL + "/load_all_projects/"
LOAD_NODE_DATA_URL = BASE_URL + "/load_node_data/"
WORKER_TOKEN = "REMOVED_CREDENTIAL"
DOWNLOAD_PROJECT_FILE_DATA_URL = BASE_URL + "/download_project_file_data/"
PROJECTS_FOLDER = os.path.join(CWD_PATH, 'Projects')
UPDATE_PROJECT_REFRESH_STATUS = BASE_URL + "/update_project_refresh_status/"
PD_DATA_KEY = 'PDData'
IO_DATA_KEY = 'IODataKey'
DATA_KEY = "DATA"
DB_NAME = "WaveAssist"
CONNECTION_STRING = "REMOVED_CREDENTIAL"