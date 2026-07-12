##PYTHON IMPORTS
import uuid

import boto3
from ..models import *

##Custom
from WaveAssistApiApp.Utils.constants import *
from WaveAssistApiApp.Utils.Logger import Logger
from collections import deque
import re
import pytz
import json
from graphviz import Digraph
from io import BytesIO
import requests
from datetime import datetime
import zipfile

logger = Logger()
import json
import threading
import requests
from django.db.models.functions import Lower
import posthog
from django.conf import settings

posthog.api_key = settings.POSTHOG_API_KEY
posthog.host = settings.POSTHOG_HOST
import json
from .constants import GITHUB_USERNAME
from django.db import transaction
from django.test import Client


def get_param(request, key: str, default=None):
    # Check GET params first
    if request.method == "GET":
        return request.GET.get(key, default)

    # Check POST params
    if key in request.POST:
        return request.POST.get(key, default)

    # Avoid accessing body if it's a multipart/form-data request
    if request.content_type.startswith("multipart/form-data"):
        return default

    # Fallback: try JSON body
    try:
        body_data = json.loads(request.body.decode("utf-8"))
        return body_data.get(key, default)
    except Exception as e:
        print(
            f"Error parsing JSON body: {str(e)}, when fetching key: {key} from request {str(request)}"
        )
        return default


def get_from_email(product: str = "waveassist") -> str:
    """Brand-aware transactional From header.

    Resolves the sender for the given Account.product. Both brands' domains are verified in
    Postmark, so each sends from its own domain. Any unknown/absent product falls back to the
    WaveAssist sender, so a bad value can never produce an unverified From that would bounce."""
    return FROM_EMAIL_BY_PRODUCT.get(product or "waveassist", DEFAULT_FROM_EMAIL)


def send_welcome_email(user_object, product: str = "waveassist"):
    """Send the brand-aware welcome email to a newly-created user.

    Runs on a background thread so signup is never blocked or failed by mail delivery, mirroring
    send_alert_email. Best-effort: Postmark first, SMTP backup on failure, and it never raises."""

    def _send():
        try:
            to_email = str(getattr(user_object, "username", "") or "").strip()
            if not to_email:
                return
            product_key = product if product in FROM_EMAIL_BY_PRODUCT else "waveassist"
            subject = "Welcome to GitZoid" if product_key == "gitzoid" else "Welcome to WaveAssist"
            html_content = get_email_template_welcome(product_key)
            from_email = get_from_email(product_key)
            try:
                from postmarker.core import PostmarkClient
                PostmarkClient(server_token=POSTMARK_API_TOKEN).emails.send(
                    From=from_email,
                    To=to_email,
                    Subject=subject,
                    HtmlBody=html_content,
                    TrackOpens=True,
                )
            except Exception as primary_error:
                # SMTP fallback lives in sdk_views; import lazily to avoid a circular import.
                from WaveAssistApiApp.sdk_views import send_email_backup
                if not send_email_backup(
                    from_email=from_email,
                    to_emails=to_email,
                    subject=subject,
                    html_content=html_content,
                ):
                    logger.error(f"Welcome email failed entirely for {to_email}: {primary_error}")
        except Exception as e:
            logger.error(f"send_welcome_email error: {e}")

    threading.Thread(target=_send).start()


def send_alert_email():
    def trigger():
        try:
            url = "https://api.waveassist.io/deploy/run_dag/"
            payload = {
                "uid": "2fec42dd-492b-4294-8154-d33c3ccf",
                "project_key": "notifier",
                "start_node_key": "node_notifier_notify_me",
                "data_run_key": "notifier_default",
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            requests.post(url, data=payload, headers=headers)
        except Exception as e:
            print("Error in background send_alert_email:", str(e))

    threading.Thread(target=trigger).start()


def does_user_have_access_to_project(client_object, project_object, access_gte=1):
    access_count = AccessProvided.objects.filter(
        user_object=client_object,
        project_object=project_object,
        type=0,
        project_access_type__gte=access_gte,
    ).count()
    if access_count > 0:
        return True
    else:
        return False


def get_collection_key(flow_object, project_object):
    return project_object.project_key + "-" + str(flow_object.id)


def does_user_have_access_to_flow(client_object, flow_object):
    flows_list = client_object.flows_set.filter(id=flow_object.id)
    if flows_list.count() > 0:
        return True
    else:
        return False


def does_user_have_access_to_data_run(
    user_object, data_run_object, access_type=READ_GTE
):
    # Directly querying DataRuns model with conditions that relate to AccessProvided
    data_run_array = DataRuns.objects.filter(
        accessprovided__type=1,
        accessprovided__data_run_access_type__gte=access_type,
        accessprovided__user_object=user_object,
    ).distinct()

    if data_run_object in data_run_array:
        return True
    return False


def resize_image(file, max_dimension=800):
    return file


def upload_file_to_s3(file, s3_file_name=None, is_public=0):
    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=AWSS3_ACCESS_KEY_VALUE,
            aws_secret_access_key=AWSS3_SECRET_KEY_VALUE,
        )
        bucket = "waveassist-bundles" if is_public == 0 else "waveassistapps"
        if is_public:
            s3_file_name = f"public/{s3_file_name}"

        # Detect if file is a path or file object
        if isinstance(file, str) and os.path.isfile(file):
            s3.upload_file(file, bucket, s3_file_name)
        else:
            s3.upload_fileobj(file, bucket, s3_file_name)

        return True, s3_file_name

    except Exception as e:
        print("❌ Error in upload_file_to_s3:", str(e))
        return False, None


def zip_directory(source_dir, output_path):
    with zipfile.ZipFile(output_path, "w") as bundle:
        for root, _, files in os.walk(source_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, source_dir)
                bundle.write(abs_path, rel_path)


def user_has_project_access(user, project_id):
    try:
        project = Project.objects.get(project_key=project_id)
        if project.accessprovided_set.filter(user_object=user).exists():
            return project
    except Project.DoesNotExist:
        pass
    return None


def get_connected_subgraph_set(start_node, all_nodes):
    visited_nodes = set()

    def explore(node):
        if node in visited_nodes:
            return
        visited_nodes.add(node)

        # Explore all nodes that this node depends on (downstream)
        for dependent in node.run_after_nodes_array.filter(is_enabled=True):
            explore(dependent)

        # Explore all nodes that depend on this node (upstream)
        for potential_upstream in all_nodes:
            if node in potential_upstream.run_after_nodes_array.filter(is_enabled=True):
                explore(potential_upstream)

    explore(start_node)
    return visited_nodes


def detect_cycle_in_node_set(start_node, all_nodes_set):
    node_dependencies = {
        node: set(node.run_after_nodes_array.all()) for node in all_nodes_set
    }
    visited = set()
    recursion_stack = set()

    def dfs(node):
        if node in recursion_stack:
            return True  # Cycle detected
        if node in visited:
            return False  # Node has been fully processed

        visited.add(node)
        recursion_stack.add(node)

        # Explore all nodes that consider the current node as a prerequisite
        for potential_dependent in all_nodes_set:
            if node in node_dependencies[potential_dependent]:
                if dfs(potential_dependent):
                    return True  # Cycle detected in the subgraph

        recursion_stack.remove(node)
        return False

    # Start the DFS from the start node
    return dfs(start_node)


def fetch_start_node_in_node_set(all_nodes_set):
    ##Check if there is only one is_starting_node assuming the input is of type set()
    starting_nodes = {node for node in all_nodes_set if node.is_starting_node}
    if len(starting_nodes) == 0:
        return False, None
    if len(starting_nodes) > 1:
        return False, None
    return True, starting_nodes.pop()


def check_dag(start_node, all_nodes):
    all_nodes = all_nodes.prefetch_related("run_after_nodes_array")
    sub_nodes_set = get_connected_subgraph_set(start_node, all_nodes)
    success, start_node = fetch_start_node_in_node_set(sub_nodes_set)
    if not success:
        return (
            False,
            [],
            "Issue with starting node. There needs to be exactly one enabled starting node in each DAG",
        )
    is_cycle = detect_cycle_in_node_set(start_node, sub_nodes_set)
    if is_cycle:
        return False, [], "Invalid DAG: Cycle detected in the graph"
    else:
        return True, list(sub_nodes_set), "DAG is valid"


def get_code_for_node(node_object, project_key):
    node_python_code = node_object.python_code
    python_code = "def run_task():\n"
    python_code += "    " + node_python_code.replace("\n", "\n    ") + "\n\n"
    return python_code


def get_task_dict_for_node(node_object, uid):
    task_dict = {
        "node_key": node_object.node_key,
        "project_key": node_object.project_object.project_key,
        "uid": uid,
    }
    return task_dict


def get_data_and_dependencies_for_dag(project_object, node_array, uid):
    dependency_dict = {}
    data_dict = {}
    # for each node in dag_object
    for node_object in node_array:
        node_code = get_code_for_node(node_object, project_object.project_key)
        node_task_dict = get_task_dict_for_node(node_object, uid)
        node_task_dict["code_to_run"] = node_code
        data_dict[node_object.node_key] = node_task_dict
        dependency_dict[node_object.node_key] = [
            node.node_key for node in node_object.run_after_nodes_array.all()
        ]
    return data_dict, dependency_dict


def fetch_account_object_for_user(user_object):
    try:
        account_object = Account.objects.get(created_by_user=user_object)
    except:
        return None
    return account_object


from graphviz import Digraph
from io import BytesIO


def generate_dag_visualization(dag_dict):
    dot = Digraph(comment="DAGs Visualization")

    # Global attributes
    dot.attr(
        bgcolor="#1F2732",
        rankdir="LR",
        fontname="Open Sans Semibold",  # semibold/bold style
        nodesep="0.8",  # reduced spacing between nodes
        ranksep="1.0",  # reduced spacing between ranks
        margin="0.4",
    )

    # Node appearance
    node_style = {
        "style": "filled,rounded",
        "fillcolor": "#408558",
        "fontcolor": "#ffffff",
        "color": "#408558",
        "fontname": "Open Sans Semibold",
        "shape": "box",
        "fontsize": "14",
        "width": "1.5",
        "height": "0.6",
        "penwidth": "1.5",
    }

    # Edge style (thicker arrows)
    edge_style = {
        "color": "#408558",
        "fontname": "Open Sans Semibold",
        "penwidth": "2.0",  # increased arrow thickness
    }

    for i, (start_node, node_list) in enumerate(dag_dict.items()):
        with dot.subgraph(name=f"cluster_{start_node.node_key}") as subgraph:
            subgraph.attr(
                style="rounded",
                color="#408558",
                fontname="Open Sans Semibold",
                margin="20",
            )

            subgraph.node(start_node.node_key, label=start_node.name, **node_style)

            for node in node_list:
                subgraph.node(node.node_key, label=node.name, **node_style)
                for dep in node.run_after_nodes_array.all():
                    subgraph.edge(dep.node_key, node.node_key, **edge_style)

    image_stream = BytesIO()
    image_stream.write(dot.pipe(format="png"))
    image_stream.seek(0)
    return image_stream


def stop_deployment(deployment_object):
    try:
        with transaction.atomic():
            deployment_object.is_running = False
            for dag in deployment_object.dag_set.all():
                dag.periodic_task.enabled = False
                dag.periodic_task.save()
                dag.is_running = False
                dag.save()
            deployment_object.save()
    except Exception as e:
        print(f"An error occurred: {e}")
        raise Exception("Could not stop the Deployment: " + str(e))


def resume_deployment(deployment_object):
    """Inverse of stop_deployment: re-enable a paused deployment and its DAG schedules."""
    try:
        with transaction.atomic():
            deployment_object.is_running = True
            for dag in deployment_object.dag_set.all():
                dag.periodic_task.enabled = True
                dag.periodic_task.save()
                dag.is_running = True
                dag.save()
            deployment_object.save()
    except Exception as e:
        print(f"An error occurred: {e}")
        raise Exception("Could not resume the Deployment: " + str(e))


def get_all_loki_jobs():
    try:
        response = requests.get(LOKI_URL + "/loki/api/v1/label/job/values")
        response_dict = response.json()
        options_array = response_dict["data"]
        return options_array
    except:
        return []


def fetch_loki_logs(query, start_ts, end_ts):
    logs = []
    try:
        response = requests.get(
            LOKI_URL + "/loki/api/v1/query_range",
            params={
                "query": query,
                "start": start_ts,
                "end": end_ts,
                "limit": LOGS_LIMIT,
                "direction": "backward",  # Fetch logs in reverse order (latest logs first)
            },
        )

        response_dict = response.json()
        result_array = response_dict["data"]["result"]
        for result_dict in result_array:
            try:
                all_values = result_dict["values"]
                for values_array in all_values:
                    try:
                        log_message = values_array[1]
                        if log_message != "":
                            log_message = re.sub(r"\[.*?]", "", log_message).strip()
                            log_dict = {
                                "log": log_message,
                                "timestamp": datetime.fromtimestamp(
                                    int(values_array[0]) / 1000000000
                                ).strftime("%Y-%m-%d %H:%M:%S"),
                            }
                            logs.append(log_dict)
                    except:
                        pass
            except:
                pass
    except:
        pass

    return logs


def build_loki_query(selected_jobs, node_key_array):
    # Create a regex pattern for the jobs
    jobs_regex = "|".join([f"{job}" for job in selected_jobs])
    query = f'{{job=~"{jobs_regex}"'

    if len(node_key_array) > 0:
        # Create a regex pattern for the node keys
        nodes_regex = "|".join([f"{node}" for node in node_key_array])
        query += f', node=~"{nodes_regex}"'

    query += "}"
    return query


import pymongo
import requests
from requests.auth import HTTPDigestAuth

mongo_url = "REMOVED_CREDENTIAL"
public_key = "nzaopldm"
private_key = "REMOVED_CREDENTIAL"


def create_mongo_url(user_object):

    # MongoDB admin credentials and connection
    mongo_client = pymongo.MongoClient(mongo_url)

    # Generate database and user details
    db_name = f"wa_{str(user_object.uid)[:20]}"
    username = str(user_object.uid)
    password = str(user_object.uid)

    # Create the database
    new_db = mongo_client[db_name]

    try:
        # Create a collection to initialize the database
        new_db.create_collection("initial_collection")
    except:
        pass

    group_id = "67a20af1d579ac023d1d022d"
    # Use MongoDB Atlas API to create the user
    url = f"https://cloud.mongodb.com/api/atlas/v1.0/groups/{group_id}/databaseUsers"
    headers = {"Content-Type": "application/json"}
    user_data = {
        "databaseName": "admin",
        "username": username,
        "password": password,
        "roles": [{"databaseName": db_name, "roleName": "dbAdmin"}],
    }

    # Make the POST request with HTTP Digest Authentication
    response = requests.post(
        url,
        json=user_data,
        headers=headers,
        auth=HTTPDigestAuth(public_key, private_key),
    )

    if response.status_code == 201:
        print("User created successfully.")
        print(response.json())
    else:
        print("Failed to create user:", response.json())
        return None, None

    # Generate and return the connection URL for the new user
    url = f"mongodb+srv://{username}:{password}@waveassistcluster.9ju27.mongodb.net/{db_name}"

    return url, db_name


def get_database_name(user_object):
    return "wa_" + str(user_object.uid)[:20]


def create_openrouter_token(uid, grant_usd=round(2 / WAVEASSIST_CREDIT_MULTIPLIER, 4)):
    """Create an OpenRouter API token for the given user.

    Returns (key, hash) tuple, or (None, None) on failure.
    The hash is used for direct PATCH requests without listing all keys.
    """
    try:
        url = "https://openrouter.ai/api/v1/keys"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_PROVISIONING_KEY}",
            "Content-Type": "application/json",
        }
        payload = {"name": f"{uid}", "label": str(uid), "limit": grant_usd}
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        inner = data.get("data", {})
        key = data.get("key") or inner.get("key") or inner.get("token")
        key_hash = inner.get("hash") or inner.get("key_hash") or ""
        return key, key_hash
    except Exception as e:
        print("Error creating openrouter token:", str(e))
        return None, None


def generate_filter_pattern(node_key_csv, project_object):
    # Construct filter_pattern
    if node_key_csv:
        # Split CSV into a list of node keys
        node_key_array = node_key_csv.split(",")
        node_key_array = [node_key.strip() for node_key in node_key_array if node_key]

        # Construct OR conditions for node_key
        node_key_conditions = " || ".join(
            [f'$.extra.node_key = "{node_key}"' for node_key in node_key_array]
        )

        # Combine project_key with OR conditions
        filter_pattern = f'{{ $.extra.project_key = "{project_object.project_key}" && ({node_key_conditions}) }}'
    else:
        filter_pattern = f'{{ $.extra.project_key = "{project_object.project_key}" }}'

    return filter_pattern


def get_task_definition(uid):
    return {
        "containerDefinitions": [
            {
                "name": "worker",
                "image": "713358430452.dkr.ecr.us-east-1.amazonaws.com/waveassist_celery_worker:latest",
                "cpu": 0,
                "portMappings": [],
                "essential": True,
                "environment": [{"name": "ACCOUNT_ID", "value": f"{uid}"}],
                "mountPoints": [],
                "volumesFrom": [],
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": "/ecs/WaveAssistWorkerTasks",
                        "mode": "non-blocking",
                        "awslogs-create-group": "true",
                        "max-buffer-size": "25m",
                        "awslogs-region": "us-east-1",
                        "awslogs-stream-prefix": "ecs",
                    },
                    "secretOptions": [],
                },
                "systemControls": [],
            }
        ],
        "family": f"WaveAssistWorkerTasks__{uid}",
        "taskRoleArn": "arn:aws:iam::713358430452:role/ecsTaskExecutionRole",
        "executionRoleArn": "arn:aws:iam::713358430452:role/ecsTaskExecutionRole",
        "networkMode": "awsvpc",
        "volumes": [],
        "placementConstraints": [],
        "requiresCompatibilities": ["FARGATE"],
        "cpu": "256",
        "memory": "1024",
        "runtimePlatform": {
            "cpuArchitecture": "X86_64",
            "operatingSystemFamily": "LINUX",
        },
    }


def get_base_package_names():
    with open("ignore_requirements.txt", "r") as f:
        lines = f.readlines()
    base_packages = set()
    for line in lines:
        if "==" in line:
            pkg = line.strip().split("==")[0].lower()
            base_packages.add(pkg)
    return base_packages


import base64
import uuid


def b64url_decode(s: str) -> str:
    pad = "=" * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s + pad).decode()


def decode_email_webhook_token(token: str) -> dict:
    """
    Decode a token of the form:
    <UUID-no-dash>.<b64(projectId)>.<b64(nodeId)>.<b64(envId)>

    Example:
        21bcd57ab350490bb8bd2b93c0c5bfa9.MTcx.Mzg3.MzM0
    """
    try:
        uuid_hex, b_project, b_node, b_env = token.split(".")
        uid = str(uuid.UUID(uuid_hex))  # adds dashes
        project_id = b64url_decode(b_project)
        node_id = b64url_decode(b_node)
        env_id = b64url_decode(b_env)
    except Exception as e:
        return None

    return {
        "uid": uid,
        "project_id": project_id,
        "node_id": node_id,
        "env_id": env_id,
    }


def get_repo_parts_from_url(repo_url):
    repo_parts = repo_url.replace(".git", "").rstrip("/").split("/")
    if len(repo_parts) >= 2:
        owner = repo_parts[-2]
        repo_name = repo_parts[-1]
    else:
        owner = GITHUB_USERNAME
        repo_name = repo_parts[-1]

    return owner, repo_name


def track_posthog(uid, event, props):
    try:
        posthog.capture(distinct_id=str(uid), event=event, properties=props or {})
    except:
        pass


def cron_to_human_readable(minute, hour, day_of_week, day_of_month, month_of_year):
    """Convert basic crontab-style fields to a human-readable string.

    Handles common patterns like "*/N" for every N units, explicit times, and named days/months.
    This is deliberately simple and aims to be friendlier than raw cron syntax, not exhaustive.
    """

    def every_n(expression, unit):
        if isinstance(expression, str) and expression.startswith("*/"):
            try:
                n = int(expression[2:])
                return f"every {n} {unit}{'' if n == 1 else 's'}"
            except Exception:
                return None
        return None

    def format_time(h, m):
        if h == "*" and m == "*":
            return "every minute"

        # Zero-pad numbers when numeric
        def to_int_safe(x):
            try:
                return int(x)
            except Exception:
                return None

        hi = to_int_safe(h)
        mi = to_int_safe(m)
        if hi is not None and mi is not None:
            return f"at {hi:02d}:{mi:02d}"
        if hi is not None and m == "*":
            return f"every minute past {hi:02d}:00"
        if h == "*" and mi is not None:
            return f"at minute {mi:02d} of every hour"
        return None

    def try_format_multiple_hours(h, m):
        # Handle comma-separated or range hours with a fixed minute
        def to_int_list(expr):
            if not isinstance(expr, str):
                expr = str(expr)
            parts = [p.strip() for p in expr.split(",")]
            out = []
            for p in parts:
                if "-" in p:
                    try:
                        start, end = p.split("-")
                        start_i = int(start)
                        end_i = int(end)
                        if start_i <= end_i:
                            out.extend(list(range(start_i, end_i + 1)))
                        else:
                            out.extend(list(range(end_i, start_i + 1)))
                    except Exception:
                        pass
                else:
                    try:
                        out.append(int(p))
                    except Exception:
                        pass
            # Deduplicate while preserving order
            seen = set()
            ordered = []
            for v in out:
                if v not in seen:
                    ordered.append(v)
                    seen.add(v)
            return ordered

        try:
            mi = int(m)
        except Exception:
            return None
        hour_list = to_int_list(h)
        if not hour_list:
            return None
        times = [f"{hh:02d}:{mi:02d}" for hh in hour_list]
        if len(times) == 1:
            return f"at {times[0]}"
        if len(times) == 2:
            return f"at {times[0]} and {times[1]}"
        return "at " + ", ".join(times[:-1]) + f" and {times[-1]}"

    def format_list_or_value(expr, name_map=None):
        # Accept comma-separated lists or ranges and keep them as-is, with simple mapping if provided
        if not isinstance(expr, str):
            expr = str(expr)
        parts = [p.strip() for p in expr.split(",")]
        if name_map:
            mapped = [name_map.get(p.lower(), p) for p in parts]
        else:
            mapped = parts
        if len(mapped) == 1:
            return mapped[0]
        if len(mapped) == 2:
            return f"{mapped[0]} and {mapped[1]}"
        return ", ".join(mapped[:-1]) + f" and {mapped[-1]}"

    day_name_map = {
        "0": "sun",
        "1": "mon",
        "2": "tue",
        "3": "wed",
        "4": "thu",
        "5": "fri",
        "6": "sat",
        "sun": "sun",
        "mon": "mon",
        "tue": "tue",
        "wed": "wed",
        "thu": "thu",
        "fri": "fri",
        "sat": "sat",
    }
    day_order = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
    month_name_map = {
        "1": "jan",
        "2": "feb",
        "3": "mar",
        "4": "apr",
        "5": "may",
        "6": "jun",
        "7": "jul",
        "8": "aug",
        "9": "sep",
        "10": "oct",
        "11": "nov",
        "12": "dec",
        "jan": "jan",
        "feb": "feb",
        "mar": "mar",
        "apr": "apr",
        "may": "may",
        "jun": "jun",
        "jul": "jul",
        "aug": "aug",
        "sep": "sep",
        "oct": "oct",
        "nov": "nov",
        "dec": "dec",
    }

    # Start building pieces
    pieces = []

    # Month
    if month_of_year != "*":
        month_text = format_list_or_value(month_of_year, month_name_map)
        pieces.append(f"in {month_text}")

    # Day of month vs day of week
    if day_of_month != "*":
        # Support every N days
        en = every_n(day_of_month, "day")
        if en:
            pieces.append(en)
        else:
            pieces.append(f"on day {day_of_month}")
    elif day_of_week != "*":
        en = every_n(day_of_week, "day")
        if en:
            pieces.append(en)
        else:
            dow_expr = str(day_of_week).lower()
            if "-" in dow_expr:
                # Range like 1-5 -> mon through fri
                try:
                    start, end = dow_expr.split("-")
                    start_name = day_name_map.get(start, start)
                    end_name = day_name_map.get(end, end)
                    # Special-case weekdays
                    if {start_name, end_name} == {"mon", "fri"} and dow_expr in (
                        "1-5",
                        "mon-fri",
                    ):
                        pieces.append("on weekdays")
                    else:
                        pieces.append(f"on {start_name} through {end_name}")
                except Exception:
                    dow_text = format_list_or_value(dow_expr, day_name_map)
                    pieces.append(f"on {dow_text}")
            else:
                dow_text = format_list_or_value(dow_expr, day_name_map)
                pieces.append(f"on {dow_text}")
    else:
        # Neither specified: every day
        pieces.append("every day")

    # Hour/Minute
    time_phrase = None
    # Handle every N hours/minutes
    hourly = every_n(hour, "hour")
    minutely = every_n(minute, "minute")
    if hourly and minutely:
        # Prefer the more specific minute interval when both present
        time_phrase = minutely
    elif hourly:
        time_phrase = hourly
    elif minutely:
        time_phrase = minutely
    else:
        # Try multiple hours with fixed minute first
        time_phrase = try_format_multiple_hours(hour, minute) or format_time(
            hour, minute
        )

    if time_phrase:
        pieces.append(time_phrase)

    # Join and tidy spacing
    sentence = " ".join(pieces)
    # Capitalize first letter
    if sentence:
        sentence = sentence[0].upper() + sentence[1:]
    return sentence or "on a schedule"


def interval_to_human_readable(every, period):
    try:
        n = int(every)
    except Exception:
        n = every
    period = (str(period) or "").lower()
    # Normalize Django Celery Beat period names
    period_map = {
        "days": "day",
        "hours": "hour",
        "minutes": "minute",
        "seconds": "second",
        "microseconds": "microsecond",
    }
    unit = period_map.get(period, period or "interval")
    plural = "" if (isinstance(n, int) and n == 1) else "s"
    return f"Every {n} {unit}{plural}"


def fetch_data_for_key_internal(
    uid, project_key, data_key, data_run_key=None, run_based=0, run_id=None
):

    try:
        client = Client()
        if data_run_key is None:
            data_run_key = project_key + "_default"

        # Prepare query parameters
        params = {
            "uid": uid,
            "project_key": project_key,
            "data_run_key": data_run_key,
            "data_key": data_key,
            "run_based": str(run_based),
        }

        # Add run_id if provided and run_based is enabled
        if run_based == 1 and run_id:
            params["run_id"] = run_id

        # Make the API call
        response = client.get("/data/fetch_data_for_key/", params)

        # Check response status
        if response.status_code != 200:
            return (
                False,
                None,
                f"API call failed with status {response.status_code}: {response.content.decode('utf-8')}",
            )

        # Parse response
        try:
            response_data = json.loads(response.content.decode("utf-8"))
        except json.JSONDecodeError as e:
            return False, None, f"Failed to parse JSON response: {str(e)}"

        # Check if the API call was successful
        if response_data.get("success") != "1":
            return False, None, response_data.get("message", "Unknown error occurred")

        # Extract data from response
        response_data_content = response_data.get("data", {})
        # The API returns {'data': actual_data, 'data_type': 'json'}, so extract the actual data
        if isinstance(response_data_content, dict) and "data" in response_data_content:
            data = response_data_content["data"]
        else:
            data = response_data_content
        return True, data, "Data fetched successfully"

    except Exception as e:
        logger.error(f"❌ Error in fetch_data_for_key_internal: {str(e)}")
        return False, None, f"Internal error: {str(e)}"


def set_data_for_key_internal(
    uid,
    project_key,
    data_key,
    data,
    data_type,
    data_run_key=None,
    run_based=0,
    run_id=None,
):
    try:
        client = Client()

        if data_run_key is None:
            data_run_key = project_key + "_default"

        # Prepare payload
        payload = {
            "uid": uid,
            "project_key": project_key,
            "data_run_key": data_run_key,
            "data_key": data_key,
            "data": data,
            "data_type": data_type,
            "run_based": str(run_based),
        }

        # Add run_id if provided and run_based is enabled
        if run_based == 1 and run_id:
            payload["run_id"] = run_id

        # Make the API call
        response = client.post(
            "/data/set_data_for_key/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        # Check response status
        if response.status_code != 200:
            return (
                False,
                f"API call failed with status {response.status_code}: {response.content.decode('utf-8')}",
            )

        # Parse response
        try:
            response_data = json.loads(response.content.decode("utf-8"))
        except json.JSONDecodeError as e:
            return False, f"Failed to parse JSON response: {str(e)}"

        # Check if the API call was successful
        if response_data.get("success") != "1":
            return False, response_data.get("message", "Unknown error occurred")

        # Extract data_key from response
        return True, "Data saved successfully"

    except Exception as e:
        logger.error(f"❌ Error in set_data_for_key_internal: {str(e)}")
        return False, f"Internal error: {str(e)}"


def get_email_template_welcome(product: str = "waveassist") -> str:
    """Brand-aware welcome email HTML sent to a newly-created account.

    Light theme (renders consistently across mail clients, including iOS Gmail which force-lightens
    dark emails), a typographic wordmark in a carbon chip so each brand's accent stays on its native
    surface, and one accent used sparingly. GitZoid copy follows the brand rules (no em dashes, no
    forbidden words) and is framed as onboarding for a user who has already signed up."""
    if product == "gitzoid":
        return _WELCOME_HTML_GITZOID
    return _WELCOME_HTML_WAVEASSIST


_WELCOME_HTML_WAVEASSIST = """<!doctype html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="x-apple-disable-message-reformatting" />
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta name="color-scheme" content="light" />
  <meta name="supported-color-schemes" content="light" />
  <title>Welcome to WaveAssist</title>
  <!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
  <style>
    :root { color-scheme: light; supported-color-schemes: light; }
    body, table, td, p, a { -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }
    table, td { mso-table-lspace: 0pt; mso-table-rspace: 0pt; }
    a { text-decoration: none; }
    body { margin: 0 !important; padding: 0 !important; width: 100% !important; background-color: #EDEEF0 !important; }
    .mono { font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace; }
    @media screen and (max-width: 600px) {
      .px { padding-left: 26px !important; padding-right: 26px !important; }
      .h1 { font-size: 27px !important; }
    }
  </style>
</head>
<body bgcolor="#EDEEF0" style="margin:0;padding:0;background-color:#EDEEF0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">Your account is live. Connect the MCP and run your first deterministic agent. $2 of runtime credit is on us.</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#EDEEF0" style="background-color:#EDEEF0;">
    <tr>
      <td align="center" style="padding:40px 20px;">

        <table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" style="width:560px;max-width:560px;background-color:#FFFFFF;border:1px solid #E3E5E9;border-radius:14px;">

          <!-- wordmark lockup (carbon chip keeps lime on its native surface) -->
          <tr>
            <td class="px" style="padding:34px 44px 0 44px;">
              <span style="display:inline-block;background-color:#0B0C0F;border-radius:8px;padding:9px 13px;">
                <span class="mono" style="font-size:17px;font-weight:700;letter-spacing:-0.5px;color:#ECEEF2;"><span style="color:#D8FF00;">/</span>waveassist</span>
              </span>
            </td>
          </tr>

          <!-- eyebrow -->
          <tr>
            <td class="px" style="padding:30px 44px 0 44px;">
              <span class="mono" style="font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#14161B;">The deterministic agent runtime</span>
            </td>
          </tr>

          <!-- h1 -->
          <tr>
            <td class="px" style="padding:12px 44px 0 44px;">
              <h1 class="h1" style="margin:0;font-size:32px;line-height:1.1;font-weight:800;letter-spacing:-0.8px;color:#0B0C0F;">You're in. Run your first agent.</h1>
            </td>
          </tr>

          <!-- body -->
          <tr>
            <td class="px" style="padding:18px 44px 0 44px;">
              <p style="margin:0;font-size:15px;line-height:1.65;color:#5A5F68;">
                Welcome to WaveAssist. Describe a recurring job in plain English, your coding agent builds it over MCP, and we run and deploy it on your schedule. The same result, every run.
              </p>
            </td>
          </tr>

          <!-- steps -->
          <tr>
            <td class="px" style="padding:28px 44px 0 44px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="padding:16px 0;border-top:1px solid #E3E5E9;">
                    <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
                      <td valign="top" width="42" class="mono" style="width:42px;font-size:13px;font-weight:700;color:#14161B;">01</td>
                      <td valign="top">
                        <div style="font-size:14px;font-weight:700;color:#0B0C0F;">Connect the MCP</div>
                        <div style="margin-top:3px;font-size:13px;line-height:1.55;color:#6B7280;">Copy your MCP token from the dashboard and connect your editor.</div>
                      </td>
                    </tr></table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:16px 0;border-top:1px solid #E3E5E9;">
                    <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
                      <td valign="top" width="42" class="mono" style="width:42px;font-size:13px;font-weight:700;color:#14161B;">02</td>
                      <td valign="top">
                        <div style="font-size:14px;font-weight:700;color:#0B0C0F;">Describe the job</div>
                        <div style="margin-top:3px;font-size:13px;line-height:1.55;color:#6B7280;">Tell your agent what to build, in plain English. It writes and tests the pipeline.</div>
                      </td>
                    </tr></table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:16px 0;border-top:1px solid #E3E5E9;border-bottom:1px solid #E3E5E9;">
                    <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
                      <td valign="top" width="42" class="mono" style="width:42px;font-size:13px;font-weight:700;color:#14161B;">03</td>
                      <td valign="top">
                        <div style="font-size:14px;font-weight:700;color:#0B0C0F;">Run on your schedule</div>
                        <div style="margin-top:3px;font-size:13px;line-height:1.55;color:#6B7280;">We host it and run it, the same way every time. $2 of runtime credit is on us.</div>
                      </td>
                    </tr></table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- CTA -->
          <tr>
            <td class="px" style="padding:30px 44px 0 44px;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td bgcolor="#D8FF00" style="background-color:#D8FF00;border-radius:9px;">
                    <a href="https://app.waveassist.io" style="display:inline-block;padding:14px 30px;font-size:14px;font-weight:700;color:#0B0C0F;letter-spacing:0.2px;">Open the dashboard &rarr;</a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- meta -->
          <tr>
            <td class="px" style="padding:26px 44px 0 44px;">
              <span class="mono" style="font-size:11px;letter-spacing:0.3px;color:#6B7280;">Deterministic by contract &nbsp;&middot;&nbsp; Built by your coding agent</span>
            </td>
          </tr>

          <!-- footer -->
          <tr>
            <td class="px" style="padding:30px 44px 36px 44px;">
              <div style="border-top:1px solid #E3E5E9;padding-top:20px;">
                <span class="mono" style="font-size:12px;font-weight:700;color:#14161B;"><span style="color:#0B0C0F;">/</span>waveassist</span>
                <p style="margin:8px 0 0 0;font-size:11px;line-height:1.7;color:#9096A0;">You're receiving this because you created a WaveAssist account.<br /><a href="https://waveassist.ai" style="color:#14161B;font-weight:700;text-decoration:underline;">waveassist.ai</a> &nbsp;&middot;&nbsp; The deterministic agent runtime</p>
              </div>
            </td>
          </tr>

        </table>

      </td>
    </tr>
  </table>
</body>
</html>"""


_WELCOME_HTML_GITZOID = """<!doctype html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="x-apple-disable-message-reformatting" />
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta name="color-scheme" content="light" />
  <meta name="supported-color-schemes" content="light" />
  <title>Welcome to GitZoid</title>
  <!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
  <style>
    :root { color-scheme: light; supported-color-schemes: light; }
    body, table, td, p, a { -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }
    table, td { mso-table-lspace: 0pt; mso-table-rspace: 0pt; }
    a { text-decoration: none; }
    body { margin: 0 !important; padding: 0 !important; width: 100% !important; background-color: #F2F3F1 !important; }
    .mono { font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace; }
    @media screen and (max-width: 600px) {
      .px { padding-left: 26px !important; padding-right: 26px !important; }
      .h1 { font-size: 27px !important; }
    }
  </style>
</head>
<body bgcolor="#F2F3F1" style="margin:0;padding:0;background-color:#F2F3F1;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">The product manager for your coding agents. GitZoid reviews every change your agents ship, inside GitHub.</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#F2F3F1" style="background-color:#F2F3F1;">
    <tr>
      <td align="center" style="padding:40px 20px;">

        <table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" style="width:560px;max-width:560px;background-color:#FFFFFF;border:1px solid #E7E6E2;border-radius:14px;">

          <!-- wordmark lockup -->
          <tr>
            <td class="px" style="padding:34px 44px 0 44px;">
              <span style="display:inline-block;background-color:#0B0E12;border-radius:8px;padding:9px 13px;">
                <span class="mono" style="font-size:17px;font-weight:700;letter-spacing:-0.5px;color:#FFFFFF;"><span style="color:#12C46A;">/</span>gitzoid</span>
              </span>
            </td>
          </tr>

          <!-- eyebrow -->
          <tr>
            <td class="px" style="padding:30px 44px 0 44px;">
              <span class="mono" style="font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#0B7E43;">Welcome to GitZoid</span>
            </td>
          </tr>

          <!-- h1: lead with the positioning -->
          <tr>
            <td class="px" style="padding:12px 44px 0 44px;">
              <h1 class="h1" style="margin:0;font-size:32px;line-height:1.12;font-weight:800;letter-spacing:-0.8px;color:#0B0B0C;">The product manager for your <span style="color:#0B7E43;">coding agents</span>.</h1>
            </td>
          </tr>

          <!-- body: what GitZoid does -->
          <tr>
            <td class="px" style="padding:18px 44px 0 44px;">
              <p style="margin:0;font-size:15px;line-height:1.65;color:#5F6773;">
                GitZoid reviews every change your agents ship, catches the risks they miss, and tells you what they did all week. Deterministic oversight, inside GitHub.
              </p>
            </td>
          </tr>

          <!-- what you get: three patrols -->
          <tr>
            <td class="px" style="padding:28px 44px 0 44px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="padding:16px 0;border-top:1px solid #E7E6E2;">
                    <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
                      <td valign="top" width="26" style="width:26px;padding-top:5px;"><div style="width:7px;height:7px;border-radius:50%;background-color:#12C46A;"></div></td>
                      <td valign="top">
                        <div class="mono" style="font-size:13px;font-weight:700;letter-spacing:0.3px;color:#0B0B0C;">PR Review</div>
                        <div style="margin-top:4px;font-size:13px;line-height:1.55;color:#5F6773;">A review comment on every pull request, inside GitHub.</div>
                      </td>
                    </tr></table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:16px 0;border-top:1px solid #E7E6E2;">
                    <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
                      <td valign="top" width="26" style="width:26px;padding-top:5px;"><div style="width:7px;height:7px;border-radius:50%;background-color:#12C46A;"></div></td>
                      <td valign="top">
                        <div class="mono" style="font-size:13px;font-weight:700;letter-spacing:0.3px;color:#0B0B0C;">Security Watch</div>
                        <div style="margin-top:4px;font-size:13px;line-height:1.55;color:#5F6773;">A weekly Repo Watch email on new risks.</div>
                      </td>
                    </tr></table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:16px 0;border-top:1px solid #E7E6E2;border-bottom:1px solid #E7E6E2;">
                    <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
                      <td valign="top" width="26" style="width:26px;padding-top:5px;"><div style="width:7px;height:7px;border-radius:50%;background-color:#12C46A;"></div></td>
                      <td valign="top">
                        <div class="mono" style="font-size:13px;font-weight:700;letter-spacing:0.3px;color:#0B0B0C;">Weekly Digest</div>
                        <div style="margin-top:4px;font-size:13px;line-height:1.55;color:#5F6773;">A Monday email on what your agents did.</div>
                      </td>
                    </tr></table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- next step -->
          <tr>
            <td class="px" style="padding:22px 44px 0 44px;">
              <p style="margin:0;font-size:14px;line-height:1.6;color:#0B0B0C;font-weight:700;">Next: connect your GitHub repos and start your first run.</p>
              <p class="mono" style="margin:8px 0 0 0;font-size:12px;line-height:1.6;color:#5F6773;">First 10 outputs are free, no card. $19 a month after, flat, up to 50 repos.</p>
            </td>
          </tr>

          <!-- CTA -->
          <tr>
            <td class="px" style="padding:24px 44px 0 44px;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td bgcolor="#12C46A" style="background-color:#12C46A;border-radius:9px;">
                    <a href="https://app.gitzoid.com" style="display:inline-block;padding:14px 30px;font-size:14px;font-weight:700;color:#0B0E12;letter-spacing:0.2px;">Connect your repos &rarr;</a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- meta -->
          <tr>
            <td class="px" style="padding:26px 44px 0 44px;">
              <span class="mono" style="font-size:11px;letter-spacing:0.3px;color:#5F6773;">Works with any coding agent &nbsp;&middot;&nbsp; GitHub-native &nbsp;&middot;&nbsp; No code retention</span>
            </td>
          </tr>

          <!-- footer -->
          <tr>
            <td class="px" style="padding:30px 44px 36px 44px;">
              <div style="border-top:1px solid #E7E6E2;padding-top:20px;">
                <span class="mono" style="font-size:12px;font-weight:700;color:#0B0B0C;"><span style="color:#12C46A;">/</span>gitzoid</span>
                <p style="margin:8px 0 0 0;font-size:11px;line-height:1.7;color:#8A8F98;">You are receiving this because you created a GitZoid account.<br /><a href="https://gitzoid.com" style="color:#0B7E43;font-weight:700;text-decoration:underline;">gitzoid.com</a> &nbsp;&middot;&nbsp; Built on the WaveAssist engine</p>
              </div>
            </td>
          </tr>

        </table>

      </td>
    </tr>
  </table>
</body>
</html>"""


def get_email_template_credits_expired() -> str:
    """WaveAssist: pay-as-you-go runtime credits ran out.

    New light brand design. WaveAssist never auto-stops (see the deployment lifecycle policy):
    an out-of-credit run just can't afford the LLM call and resumes on the next scheduled tick the
    moment the owner tops up."""
    return _CREDITS_EXPIRED_HTML_WAVEASSIST


def get_email_template_trial_ended() -> str:
    """GitZoid: the free trial has been spent.

    New light brand design, GitZoid copy rules (no em dashes, no forbidden words). CTA upgrades to
    GitZoid Pro, the single paid plan. Sent once at trial exhaustion (see check_account_credits)."""
    return _TRIAL_ENDED_HTML_GITZOID


_CREDITS_EXPIRED_HTML_WAVEASSIST = """<!doctype html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="x-apple-disable-message-reformatting" />
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta name="color-scheme" content="light" />
  <meta name="supported-color-schemes" content="light" />
  <title>Add credits to keep your assistants running</title>
  <!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
  <style>
    :root { color-scheme: light; supported-color-schemes: light; }
    body, table, td, p, a { -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }
    table, td { mso-table-lspace: 0pt; mso-table-rspace: 0pt; }
    a { text-decoration: none; }
    body { margin: 0 !important; padding: 0 !important; width: 100% !important; background-color: #EDEEF0 !important; }
    .mono { font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace; }
    @media screen and (max-width: 600px) {
      .px { padding-left: 26px !important; padding-right: 26px !important; }
      .h1 { font-size: 27px !important; }
    }
  </style>
</head>
<body bgcolor="#EDEEF0" style="margin:0;padding:0;background-color:#EDEEF0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">Your runtime credits are spent. Add credits and your assistants pick up on their next scheduled run.</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#EDEEF0" style="background-color:#EDEEF0;">
    <tr>
      <td align="center" style="padding:40px 20px;">

        <table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" style="width:560px;max-width:560px;background-color:#FFFFFF;border:1px solid #E3E5E9;border-radius:14px;">

          <!-- wordmark lockup -->
          <tr>
            <td class="px" style="padding:34px 44px 0 44px;">
              <span style="display:inline-block;background-color:#0B0C0F;border-radius:8px;padding:9px 13px;">
                <span class="mono" style="font-size:17px;font-weight:700;letter-spacing:-0.5px;color:#ECEEF2;"><span style="color:#D8FF00;">/</span>waveassist</span>
              </span>
            </td>
          </tr>

          <!-- eyebrow -->
          <tr>
            <td class="px" style="padding:30px 44px 0 44px;">
              <span class="mono" style="font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#14161B;">Action needed</span>
            </td>
          </tr>

          <!-- h1 -->
          <tr>
            <td class="px" style="padding:12px 44px 0 44px;">
              <h1 class="h1" style="margin:0;font-size:32px;line-height:1.12;font-weight:800;letter-spacing:-0.8px;color:#0B0C0F;">Your trial credits have run out.</h1>
            </td>
          </tr>

          <!-- body -->
          <tr>
            <td class="px" style="padding:18px 44px 0 44px;">
              <p style="margin:0;font-size:15px;line-height:1.65;color:#5A5F68;">
                The $2 of runtime credit that came with your account is spent, so your assistants are paused. Add credits and they pick up right where they left off, on the next scheduled run.
              </p>
            </td>
          </tr>

          <!-- CTA -->
          <tr>
            <td class="px" style="padding:28px 44px 0 44px;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td bgcolor="#D8FF00" style="background-color:#D8FF00;border-radius:9px;">
                    <a href="https://app.waveassist.io" style="display:inline-block;padding:14px 30px;font-size:14px;font-weight:700;color:#0B0C0F;letter-spacing:0.2px;">Add credits &rarr;</a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- meta -->
          <tr>
            <td class="px" style="padding:26px 44px 0 44px;">
              <span class="mono" style="font-size:11px;letter-spacing:0.3px;color:#6B7280;">Pay as you go &nbsp;&middot;&nbsp; No subscription</span>
            </td>
          </tr>

          <!-- footer -->
          <tr>
            <td class="px" style="padding:30px 44px 36px 44px;">
              <div style="border-top:1px solid #E3E5E9;padding-top:20px;">
                <span class="mono" style="font-size:12px;font-weight:700;color:#14161B;"><span style="color:#0B0C0F;">/</span>waveassist</span>
                <p style="margin:8px 0 0 0;font-size:11px;line-height:1.7;color:#9096A0;">You're receiving this because you have a WaveAssist account.<br /><a href="https://waveassist.ai" style="color:#14161B;font-weight:700;text-decoration:underline;">waveassist.ai</a> &nbsp;&middot;&nbsp; The deterministic agent runtime</p>
              </div>
            </td>
          </tr>

        </table>

      </td>
    </tr>
  </table>
</body>
</html>"""


_TRIAL_ENDED_HTML_GITZOID = """<!doctype html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="x-apple-disable-message-reformatting" />
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta name="color-scheme" content="light" />
  <meta name="supported-color-schemes" content="light" />
  <title>Your GitZoid trial has ended</title>
  <!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
  <style>
    :root { color-scheme: light; supported-color-schemes: light; }
    body, table, td, p, a { -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }
    table, td { mso-table-lspace: 0pt; mso-table-rspace: 0pt; }
    a { text-decoration: none; }
    body { margin: 0 !important; padding: 0 !important; width: 100% !important; background-color: #F2F3F1 !important; }
    .mono { font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace; }
    @media screen and (max-width: 600px) {
      .px { padding-left: 26px !important; padding-right: 26px !important; }
      .h1 { font-size: 27px !important; }
    }
  </style>
</head>
<body bgcolor="#F2F3F1" style="margin:0;padding:0;background-color:#F2F3F1;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">You have used your free outputs. Upgrade to GitZoid Pro to keep reviews, security watches, and weekly digests running.</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#F2F3F1" style="background-color:#F2F3F1;">
    <tr>
      <td align="center" style="padding:40px 20px;">

        <table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" style="width:560px;max-width:560px;background-color:#FFFFFF;border:1px solid #E7E6E2;border-radius:14px;">

          <!-- wordmark lockup -->
          <tr>
            <td class="px" style="padding:34px 44px 0 44px;">
              <span style="display:inline-block;background-color:#0B0E12;border-radius:8px;padding:9px 13px;">
                <span class="mono" style="font-size:17px;font-weight:700;letter-spacing:-0.5px;color:#FFFFFF;"><span style="color:#12C46A;">/</span>gitzoid</span>
              </span>
            </td>
          </tr>

          <!-- eyebrow -->
          <tr>
            <td class="px" style="padding:30px 44px 0 44px;">
              <span class="mono" style="font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#0B7E43;">Your trial</span>
            </td>
          </tr>

          <!-- h1 -->
          <tr>
            <td class="px" style="padding:12px 44px 0 44px;">
              <h1 class="h1" style="margin:0;font-size:32px;line-height:1.12;font-weight:800;letter-spacing:-0.8px;color:#0B0B0C;">Your GitZoid trial has ended.</h1>
            </td>
          </tr>

          <!-- body -->
          <tr>
            <td class="px" style="padding:18px 44px 0 44px;">
              <p style="margin:0;font-size:15px;line-height:1.65;color:#5F6773;">
                You have used all your free outputs, so GitZoid has paused. Upgrade to GitZoid Pro to keep PR reviews, security watches, and weekly digests running across your repos.
              </p>
            </td>
          </tr>

          <!-- price detail -->
          <tr>
            <td class="px" style="padding:20px 44px 0 44px;">
              <p class="mono" style="margin:0;font-size:12px;line-height:1.6;color:#5F6773;">$19 a month, flat, up to 50 repos. Cancel anytime.</p>
            </td>
          </tr>

          <!-- CTA -->
          <tr>
            <td class="px" style="padding:24px 44px 0 44px;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td bgcolor="#12C46A" style="background-color:#12C46A;border-radius:9px;">
                    <a href="https://app.gitzoid.com" style="display:inline-block;padding:14px 30px;font-size:14px;font-weight:700;color:#0B0E12;letter-spacing:0.2px;">Upgrade to Pro &rarr;</a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- meta -->
          <tr>
            <td class="px" style="padding:26px 44px 0 44px;">
              <span class="mono" style="font-size:11px;letter-spacing:0.3px;color:#5F6773;">PR Review &nbsp;&middot;&nbsp; Security Watch &nbsp;&middot;&nbsp; Weekly Digest</span>
            </td>
          </tr>

          <!-- footer -->
          <tr>
            <td class="px" style="padding:30px 44px 36px 44px;">
              <div style="border-top:1px solid #E7E6E2;padding-top:20px;">
                <span class="mono" style="font-size:12px;font-weight:700;color:#0B0B0C;"><span style="color:#12C46A;">/</span>gitzoid</span>
                <p style="margin:8px 0 0 0;font-size:11px;line-height:1.7;color:#8A8F98;">You are receiving this because you have a GitZoid account.<br /><a href="https://gitzoid.com" style="color:#0B7E43;font-weight:700;text-decoration:underline;">gitzoid.com</a> &nbsp;&middot;&nbsp; Built on the WaveAssist engine</p>
              </div>
            </td>
          </tr>

        </table>

      </td>
    </tr>
  </table>
</body>
</html>"""


def fetch_credits_from_openrouter(open_router_key: str) -> dict:
    """
    Fetch credit balance from OpenRouter for a given API key.
    Retries once when limit_remaining is 0 — OpenRouter sometimes returns stale 0
    even when credits exist. Raises on any failure so callers can handle it.
    Returns dict with keys: limit, usage, limit_remaining.
    `usage` is always a float. `limit` and `limit_remaining` are floats for capped keys,
    but are None for uncapped keys (an OpenRouter key with no spending limit set) — None
    means "unlimited", and every caller must handle it instead of doing arithmetic on it.
    """
    headers = {
        "Authorization": f"Bearer {open_router_key}",
        "Content-Type": "application/json",
    }

    def _call():
        response = requests.get("https://openrouter.ai/api/v1/key", headers=headers, timeout=10)
        if response.status_code != 200:
            raise Exception(f"OpenRouter API returned status {response.status_code}")
        info = response.json()
        if "data" not in info:
            raise KeyError("OpenRouter response missing 'data' key")
        data = info["data"]
        for key in ("limit", "usage", "limit_remaining"):
            if key not in data:
                raise KeyError(f"OpenRouter response missing '{key}' key")

        # OpenRouter returns limit/limit_remaining = null for uncapped keys (no spending
        # limit set); usage is still a number. Treat null as "unlimited" (None) instead of
        # crashing on float(None) — the key is valid, it simply has no cap.
        def _to_float(value):
            return float(value) if value is not None else None

        return {
            "limit": _to_float(data["limit"]),
            "usage": float(data["usage"] or 0),
            "limit_remaining": _to_float(data["limit_remaining"]),
        }

    result = _call()
    # If 0 is returned on first attempt, retry once — could be a stale/cached response
    if result["limit_remaining"] == 0:
        result = _call()
    return result
