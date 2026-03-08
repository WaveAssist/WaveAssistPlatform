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
from knockapi import Knock

knock_client = Knock(api_key=PROD_KNOCK_KEY)
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


def run_knock_workflow(uid: str, workflow_key, data=None):
    try:
        knock_client.workflows.trigger(
            key=workflow_key, recipients=[uid], actor=uid, data=data
        )
    except Exception as e:
        print("Error in run_knock_start_workflow:", str(e))


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


def create_openrouter_token(uid, grant_usd=2):
    """Create an OpenRouter API token for the given user."""
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
        return data.get("key") or data.get("token")
    except Exception as e:
        print("Error creating openrouter token:", str(e))
        return None


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


def get_email_template_credits_limit_reached(
    assistant_name: str,
    required_credits: float,
    credits_remaining: float,
    plan_name: str = "",
) -> str:
    is_paid_plan = str(plan_name).lower() in ("plus", "pro")

    if is_paid_plan:
        cta_label = "Add Credits"
        cta_url = FRONTEND_URL
        plan_message = (
            f"Your <strong>{plan_name.capitalize()} plan</strong> credits have run out. "
            f"Top up your credits from the dashboard to keep <strong>{assistant_name}</strong> running."
        )
    else:
        cta_label = "Upgrade Plan"
        cta_url = "https://waveassist.io/pricing"
        plan_message = (
            f"Your free credits have run out. Upgrade to <strong>Plus</strong> or <strong>Pro</strong> "
            f"to get monthly credits and keep <strong>{assistant_name}</strong> running."
        )

    return f"""<!doctype html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="x-apple-disable-message-reformatting" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="color-scheme" content="light" />
    <meta name="supported-color-schemes" content="light" />
    <title>{assistant_name} - Credit Limit Reached</title>
    <!--[if mso]>
    <noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript>
    <![endif]-->
    <style>
        :root {{ color-scheme: light; supported-color-schemes: light; }}
        body, table, td, p, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
        table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
        img {{ border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; }}
        body {{ margin: 0 !important; padding: 0 !important; width: 100% !important; background-color: #f3f4f6 !important; }}
        .outer-bg {{ background-color: #f3f4f6 !important; }}
        .inner-card {{ background-color: #ffffff !important; }}
        .card-border {{ border-color: #e5e7eb !important; }}
        .heading-text {{ color: #0f172a !important; }}
        .body-text {{ color: #a1a1aa !important; }}
        .muted-text {{ color: #6b7280 !important; }}
        .footer-text {{ color: #9ca3af !important; }}
        .cta-btn {{ background-color: #1ed66c !important; color: #000000 !important; }}
        .secondary-link {{ color: #4b5563 !important; }}
        @media screen and (max-width: 600px) {{
            .content-padding {{ padding-left: 24px !important; padding-right: 24px !important; }}
            .outer-padding {{ padding: 16px !important; }}
            .heading-text {{ font-size: 22px !important; }}
            .cta-btn {{ padding: 16px 40px !important; }}
        }}
    </style>
</head>
<body bgcolor="#f3f4f6" style="margin:0;padding:0;background-color:#f3f4f6 !important;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" class="outer-bg" bgcolor="#f3f4f6" style="background-color:#f3f4f6 !important;">
        <tr>
            <td align="center" style="padding:48px 20px;" class="outer-padding">

                <!-- Inner card -->
                <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
                    style="max-width:520px;background-color:#ffffff;border:1px solid #e5e7eb;border-radius:12px;"
                    class="inner-card card-border">

                    <!-- Logo -->
                    <tr>
                        <td align="center" style="padding:48px 40px 0 40px;" class="content-padding">
                            <img src="https://waveassist.io/images/logo/WaveAssist-W.png" alt="WaveAssist" width="80"
                                style="display:block;max-width:80px;height:auto;margin:0 auto;" />
                        </td>
                    </tr>

                    <!-- Heading -->
                    <tr>
                        <td align="center" style="padding:32px 40px 0 40px;" class="content-padding">
                            <h1 class="heading-text" style="margin:0;font-size:26px;font-weight:700;color:#0f172a;letter-spacing:-0.03em;line-height:1.2;">
                                {assistant_name} needs more credits
                            </h1>
                        </td>
                    </tr>

                    <!-- Divider accent -->
                    <tr>
                        <td align="center" style="padding:24px 40px 0 40px;">
                            <div style="width:40px;height:3px;background-color:#1ed66c;border-radius:2px;"></div>
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td style="padding:24px 40px 0 40px;" class="content-padding">
                            <p class="body-text" style="margin:0;font-size:15px;color:#a1a1aa;line-height:1.7;">
                                {plan_message}
                            </p>
                        </td>
                    </tr>

                    <!-- Credit details box -->
                    <tr>
                        <td style="padding:24px 40px 0 40px;" class="content-padding">
                            <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
                                style="background-color:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;">
                                <tr>
                                    <td style="padding:16px 20px;">
                                        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                                            <tr>
                                                <td style="font-size:13px;color:#6b7280;padding-bottom:10px;">Credits required</td>
                                                <td align="right" style="font-size:13px;font-weight:600;color:#0f172a;padding-bottom:10px;">${required_credits:.2f}</td>
                                            </tr>
                                            <tr>
                                                <td style="font-size:13px;color:#6b7280;border-top:1px solid #e5e7eb;padding-top:10px;">Credits remaining</td>
                                                <td align="right" style="font-size:13px;font-weight:600;color:#ef4444;border-top:1px solid #e5e7eb;padding-top:10px;">${credits_remaining:.2f}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Primary CTA -->
                    <tr>
                        <td align="center" style="padding:36px 40px 0 40px;">
                            <!--[if mso]>
                            <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word"
                                href="{cta_url}" style="height:52px;v-text-anchor:middle;width:200px;"
                                arcsize="15%" fillcolor="#1ED66C" stroke="f">
                                <w:anchorlock/>
                                <center style="color:#000000;font-family:sans-serif;font-size:15px;font-weight:bold;">{cta_label}</center>
                            </v:roundrect>
                            <![endif]-->
                            <!--[if !mso]><!-->
                            <a href="{cta_url}" target="_blank" class="cta-btn"
                               style="display:inline-block;padding:16px 48px;background-color:#1ed66c;color:#000000;font-size:15px;font-weight:700;text-decoration:none;border-radius:8px;letter-spacing:-0.01em;">
                                {cta_label}
                            </a>
                            <!--<![endif]-->
                        </td>
                    </tr>

                    <!-- Secondary -->
                    <tr>
                        <td align="center" style="padding:20px 40px 48px 40px;">
                            <p style="margin:0;font-size:13px;">
                                <span class="muted-text" style="color:#71717a;">Questions? </span>
                                <a href="mailto:support@waveassist.io" target="_blank" class="secondary-link"
                                   style="color:#a1a1aa;text-decoration:underline;">Contact support</a>
                            </p>
                        </td>
                    </tr>

                </table>
                <!-- End inner card -->

                <!-- Footer -->
                <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width:520px;">
                    <tr>
                        <td align="center" style="padding:28px 20px 0 20px;">
                            <p class="footer-text" style="margin:0 0 8px 0;font-size:11px;color:#52525b;line-height:1.5;letter-spacing:0.02em;">
                                WaveAssist. Reliable AI Assistants as your Digital Workforce.
                            </p>
                            <p class="footer-text" style="margin:0;font-size:11px;color:#52525b;line-height:1.5;">
                                &copy; {datetime.now().year} WaveAssist. All rights reserved.
                            </p>
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
    Returns dict with keys: limit, usage, limit_remaining (all floats).
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
        return {
            "limit": float(data["limit"]),
            "usage": float(data["usage"]),
            "limit_remaining": float(data["limit_remaining"]),
        }

    result = _call()
    # If 0 is returned on first attempt, retry once — could be a stale/cached response
    if result["limit_remaining"] == 0:
        result = _call()
    return result
