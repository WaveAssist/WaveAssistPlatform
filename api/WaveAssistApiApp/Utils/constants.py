import os


WORKER_TOKEN = os.getenv('WORKER_TOKEN', '')  # swept: value from env, see .env
PD_DATA_KEY = 'PDData'
IO_DATA_KEY = 'IODataKey'
DB_NAME = "WaveAssist"

BROKER_DOMAIN = os.getenv('BROKER_DOMAIN', 'b-83686e9f-2c14-4878-91eb-96a9c4e00b8e.mq.us-east-1.amazonaws.com')

DATA_KEY = "DATA"
DATA_TYPE_KEY = "DATA_TYPE"
INTEGRATIONS_SUFFIX_KEY = "_integrations"

SHARED_OPERATOR_QUEUE = 'queue_7a5804de-f037-4c0d-aaa0-fa5211d7afd7'

ZERODHA_API_KEY = os.getenv('ZERODHA_API_KEY', '')  # swept: value from env, see .env
ZERODHA_API_SECRET_KEY = os.getenv('ZERODHA_API_SECRET_KEY', '')  # swept: value from env, see .env
ZERODHA_ACCESS_TOKEN_KEY = os.getenv('ZERODHA_ACCESS_TOKEN_KEY', '')  # swept: value from env, see .env


AWSS3_ACCESS_KEY = os.getenv('AWSS3_ACCESS_KEY', '')  # swept: value from env, see .env
AWSS3_SECRET = os.getenv('AWSS3_SECRET', '')  # swept: value from env, see .env

# Gmail SMTP credentials
MAILER_LOGIN_EMAIL = os.getenv('MAILER_LOGIN_EMAIL', '')  # swept: value from env, see .env
MAILER_LOGIN_EMAIL_PASSWORD = os.getenv('MAILER_LOGIN_EMAIL_PASSWORD', '')  # swept: value from env, see .env
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

TEMPORARY_CREATE_USER_KEY = os.getenv('TEMPORARY_CREATE_USER_KEY', '')  # swept: value from env, see .env


ADMIN_GTE = 3
WRITE_GTE = 2
READ_GTE = 1

# GitHub credentials for accessing private repositories
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME', '')  # swept: value from env, see .env
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')  # swept: value from env, see .env


DAG_TASK = 'celery_worker.run_dag'
RUN_TASK = 'celery_worker.run_task'

AWSS3_ACCESS_KEY_VALUE = os.getenv('AWS_ACCESS_KEY_ID', '')  # swept: value from env, see .env
AWSS3_SECRET_KEY_VALUE = os.getenv('AWS_SECRET_ACCESS_KEY', '')  # swept: value from env, see .env

JWT_SECRET = os.getenv('JWT_SECRET', '')  # swept: value from env, see .env

OPENROUTER_PROVISIONING_KEY = os.getenv('OPENROUTER_PROVISIONING_KEY', '')  # swept: value from env, see .env

LOKI_URL = os.getenv('LOKI_URL', 'http://localhost:3100')
# LOKI_URL = 'http://34.196.124.60:3100'
LOGS_LIMIT = 500

IDENTITY_USERNAME = os.getenv('IDENTITY_USERNAME', '')  # swept: value from env, see .env
IDENTITY_PASSWORD = os.getenv('IDENTITY_PASSWORD', '')  # swept: value from env, see .env

POSTMARK_API_TOKEN = os.getenv('POSTMARK_API_TOKEN', '')  # swept: value from env, see .env

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
    import waveassist
    waveassist.init()
    waveassist.store_data('installed_packages', list_output)
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
SEND_GRID_KEY = os.getenv('SEND_GRID_KEY', '')  # swept: value from env, see .env

# Brand-aware transactional sender. Both gitzoid.com and waveassist.ai are verified senders in
# Postmark (DKIM + Return-Path), so each brand sends from its own domain. DEFAULT_FROM_EMAIL is the
# WaveAssist fallback used when a product is unknown/absent; resolve via utils.get_from_email().
DEFAULT_FROM_EMAIL = "WaveAssist <updates@waveassist.ai>"
FROM_EMAIL_BY_PRODUCT = {
    "waveassist": DEFAULT_FROM_EMAIL,
    "gitzoid": "GitZoid <updates@gitzoid.com>",
}


DEFAULT_NODES_ARRAY = [
    {'name': 'SampleNode1', 'is_starting_node': '1', 'is_enabled': '1'},
    {'name': 'SampleNode2', 'is_starting_node': '0', 'is_enabled': '1', 'run_after_nodes_csv': 'samplenode1'},
]


CUSTOM_EVENT_KEY = 'wa-task-event'
TASK_STARTED = 'STARTED'
TASK_COMPLETED = 'COMPLETED'
TASK_FAILED = 'FAILED'


FRONTEND_URL = "https://app.waveassist.io"
# GitZoid runs on its own domain — buyers return here after checkout. Overridable via env.
GITZOID_FRONTEND_URL = "https://app.gitzoid.com"
# GitZoid Firebase project id — lets the API verify GitZoid login tokens using Google's public
# certs, so no service-account key is needed (the org may forbid SA-key creation).
GITZOID_FIREBASE_PROJECT_ID = "gitzoid-dashboard"

# DoDo Payments — defaults when env vars are not set (override via .env)
DODO_DEFAULT_BASE_URL = "https://live.dodopayments.com"
DODO_DEFAULT_API_KEY = os.getenv('DODO_DEFAULT_API_KEY', '')  # swept: value from env, see .env
DODO_DEFAULT_CREDITS_PRODUCT_ID = "pdt_0NaUMxiHUGKVnbT58MTW4"
DODO_DEFAULT_PLAN_PLUS_PRODUCT_ID = "pdt_0NaUN5Yb442s7J9ZLm7Ly"
DODO_DEFAULT_PLAN_PRO_PRODUCT_ID = "pdt_0NaUN2K3XpBUtSlBmjeMM"
# GitZoid Pro — its own DoDo product under the GitZoid brand ($19/mo).
DODO_DEFAULT_PLAN_GITZOID_PRO_PRODUCT_ID = "pdt_0NiwEuXJyydYcVkBzf0T3"
DODO_DEFAULT_WEBHOOK_SECRET = os.getenv('DODO_DEFAULT_WEBHOOK_SECRET', '')  # swept: value from env, see .env

CREDITS_CHECK_INTERVAL_DEFAULT = 300   # 5 min
CREDITS_CHECK_INTERVAL_FAST = 30       # 30 sec after payment

# WaveAssist credits = OpenRouter credits * this multiplier.
# Gives WaveAssist a 20% margin on every credit dollar.
WAVEASSIST_CREDIT_MULTIPLIER = 1.25

# ---- Multi-brand (GitZoid trial) --------------------------------------------
# Recognised products. A brand param outside this set falls back to "waveassist".
VALID_PRODUCTS = {"waveassist", "gitzoid"}

# GitZoid free-trial budget, in internal action-credits (never shown to the user).
DEFAULT_TRIAL_CREDITS = 30

# Cost per successful agent action, deducted from the trial budget. Reads as roughly
# "10 PR reviews, 1 digest, 1 security scan" out of the 30-credit budget.
TRIAL_ACTION_COSTS = {
    "pr_review": 1,
    "digest": 10,
    "security_scan": 10,
}

# Drain guards for the trial (and any metered run).
# A single action gets at most this many total attempts (1 original + retries) before we
# stop retrying it, so a persistently-failing action can't loop and burn LLM cost.
TRIAL_MAX_ATTEMPTS_PER_ACTION = 2
# A GitZoid account may connect at most this many repos across all its projects:
# TRIAL_MAX_REPOS on the free trial, PRO_MAX_REPOS on GitZoid Pro.
TRIAL_MAX_REPOS = 5
PRO_MAX_REPOS = 50
# The data key the GitZoid repo-selection multiselect saves under (read by its nodes).
GITZOID_REPOS_KEY = "github_selected_resources"

# Maps a DELIVERABLE leaf node to the trial action it represents. Only these terminal nodes are
# metered — never the gate/fetch/init nodes that also run (and succeed) on every scheduled tick.
# But a deliverable node ALSO runs and "succeeds" on every tick (did_succeed only means it didn't
# raise), so success alone is NOT delivery. Metering therefore additionally skips any run the node
# marked idle via waveassist.mark_run_idle() — see metering.run_is_idle / handle_run_terminal.
# Together:
#   • an idle repo's every-2-min cycle charges nothing (post_comment ran but posted no review),
#   • a run charges each action exactly once (see the per-action idempotency in metering.py),
#   • credits track real output (a posted PR comment, a sent digest, a raised alert).
# Exact node_key match (not substring) so unrelated nodes can never collide. These are the
# leaf nodes of GitZoid's three chains (config.yaml: post_comment / send_digest / triage_and_alert).
GITZOID_METER_NODES = {
    "post_comment": "pr_review",
    "send_digest": "digest",
    "triage_and_alert": "security_scan",
}
