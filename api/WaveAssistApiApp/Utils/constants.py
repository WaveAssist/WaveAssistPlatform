import os


WORKER_TOKEN = "REMOVED_CREDENTIAL"
PD_DATA_KEY = 'PDData'
IO_DATA_KEY = 'IODataKey'
DB_NAME = "WaveAssist"

BROKER_DOMAIN = os.getenv('BROKER_DOMAIN', 'b-83686e9f-2c14-4878-91eb-96a9c4e00b8e.mq.us-east-1.amazonaws.com')

DATA_KEY = "DATA"
DATA_TYPE_KEY = "DATA_TYPE"
INTEGRATIONS_SUFFIX_KEY = "_integrations"

ZERODHA_API_KEY = "ZERODHA_API_KEY"
ZERODHA_API_SECRET_KEY = "ZERODHA_API_SECRET"
ZERODHA_ACCESS_TOKEN_KEY = "ZERODHA_ACCESS_TOKEN_KEY"


AWSS3_ACCESS_KEY = "AWSS3_ACCESS_KEY"
AWSS3_SECRET = "AWSS3_SECRET"

# Gmail SMTP credentials
MAILER_LOGIN_EMAIL = 'kakshil.shah@waveassist.io'
MAILER_LOGIN_EMAIL_PASSWORD = '***REDACTED-CREDENTIAL***'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

TEMPORARY_CREATE_USER_KEY = 'REMOVED_CREDENTIAL'


ADMIN_GTE = 3
WRITE_GTE = 2
READ_GTE = 1

# GitHub credentials for accessing private repositories
GITHUB_USERNAME = 'WaveAssist'
GITHUB_TOKEN = 'REMOVED_CREDENTIAL'


DAG_TASK = 'celery_worker.run_dag'
RUN_TASK = 'celery_worker.run_task'

AWSS3_ACCESS_KEY_VALUE = os.getenv('AWS_ACCESS_KEY_ID','REMOVED_CREDENTIAL')
AWSS3_SECRET_KEY_VALUE = os.getenv('AWS_SECRET_ACCESS_KEY','REMOVED_CREDENTIAL')

OPENROUTER_PROVISIONING_KEY = os.getenv('OPENROUTER_PROVISIONING_KEY', 'REMOVED_CREDENTIAL')

LOKI_URL = os.getenv('LOKI_URL', 'http://localhost:3100')
# LOKI_URL = 'http://34.196.124.60:3100'
LOGS_LIMIT = 500

IDENTITY_USERNAME = 'kakshil.shah@wavepredict.com'
IDENTITY_PASSWORD = 'REMOVED_CREDENTIAL'

TEST_KNOCK_KEY = 'REMOVED_CREDENTIAL'
PROD_KNOCK_KEY = 'REMOVED_CREDENTIAL'

FETCH_INSTALL_PACKAGES_CODE = '''
def run_task():
    import subprocess
    import sys
    def list_installed_packages():
            result = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
            return result
    result = list_installed_packages()
    list_result = result.split('\\n')
    ##Get the package names and versions, and convert to a dictionary
    list_output = []
    for item in list_result:
        if item:
            package_name, package_version = item.split("==")
            if package_version and package_name:
                list_output.append({"package_name": package_name, "package_version": package_version})
    return list_output
    '''


FETCH_UNINSTALL_PACKAGES_CODE = '''
    def run_task():
    import subprocess
    import sys
    library_name = "${package_name}"
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", library_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False
    '''



GET_STARTED_DATA = {
            'action': 'PERFORM_GET_STARTED'
}


# SendGrid settings
SEND_GRID_KEY = "REMOVED_CREDENTIAL"
DEFAULT_FROM_EMAIL = "WaveAssist Updates <updates@waveassist.io>"


DEFAULT_NODES_ARRAY = [
    {'name': 'SampleNode1', 'is_starting_node': '1', 'is_enabled': '1'},
    {'name': 'SampleNode2', 'is_starting_node': '0', 'is_enabled': '1', 'run_after_nodes_csv': 'samplenode1'},
]


CUSTOM_EVENT_KEY = 'wa-task-event'
TASK_STARTED = 'STARTED'
TASK_COMPLETED = 'COMPLETED'
TASK_FAILED = 'FAILED'
