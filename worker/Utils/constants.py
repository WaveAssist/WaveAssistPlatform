import os
CWD_PATH = os.getcwd()
PROJECT_LOGS_PATH = os.path.join(CWD_PATH, 'Logs','project_logs.log')
BASE_URL = "https://assistapi.wavepredict.com"
TIMEOUT_DURATION = 300
LOAD_ALL_PROJECTS_URL = BASE_URL + "/load_all_projects/"
LOAD_ALL_TEST_NODES_URL = BASE_URL + "/fetch_all_test_nodes/"
LOAD_NODE_DATA_URL = BASE_URL + "/load_node_data/"
WORKER_TOKEN = "REMOVED_CREDENTIAL"
DOWNLOAD_PROJECT_FILE_DATA_URL = BASE_URL + "/download_project_file_data/"
PROJECTS_FOLDER = os.path.join(CWD_PATH, 'Projects')
UPDATE_PROJECT_REFRESH_STATUS = BASE_URL + "/update_project_refresh_status/"
UPDATE_NODE_TEST_RESULTS_URL = BASE_URL + "/update_node_test_results/"

PD_DATA_KEY = 'PDData'
IO_DATA_KEY = 'IODataKey'
DATA_KEY = "DATA"
DB_NAME = "WaveAssist"
CONNECTION_STRING = "REMOVED_CREDENTIAL"
INTEGRATIONS_SUFFIX_KEY = "_integrations"





##Service Constants
SERVICE_DIRECTORY = "/etc/systemd/system/"
SERVICE_TEMPLATE = """
[Unit]
Description=Wave Assist {project_name} Service
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=1
User=ubuntu
WorkingDirectory=/home/ubuntu/WaveAssistEngine/WavePredictEngine/
ExecStart=/bin/bash -c 'cd /home/ubuntu/WaveAssistEngine/WavePredictEngine/ && /home/ubuntu/WaveAssistEngine/waveenv/bin/python3 run_project.py {project_name}'
MemoryMax=256M
CPUQuota=10%

[Install]
WantedBy=multi-user.target
"""