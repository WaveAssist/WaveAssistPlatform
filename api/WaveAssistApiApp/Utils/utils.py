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
##Packages
logger = Logger()
import json
import threading
import requests

from django.db.models.functions import Lower

import json

def get_param(request, key: str, default=''):
    # Check GET params first
    if key in request.GET:
        return request.GET.get(key, default)

    # Check POST params
    if key in request.POST:
        return request.POST.get(key, default)

    # Avoid accessing body if it's a multipart/form-data request
    if request.content_type.startswith("multipart/form-data"):
        return default

    # Fallback: try JSON body
    try:
        body_data = json.loads(request.body.decode('utf-8'))
        return body_data.get(key, default)
    except (ValueError, json.JSONDecodeError):
        return default



def send_alert_email():
    def trigger():
        try:
            url = "https://api.waveassist.io/deploy/run_dag/"
            payload = {
                "uid": "2fec42dd-492b-4294-8154-d33c3ccf",
                "project_key": "notifier",
                "start_node_key": "node_notifier_notify_me",
                "data_run_key": "notifier_default"
            }
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            requests.post(url, data=payload, headers=headers)
        except Exception as e:
            print("Error in background send_alert_email:", str(e))

    threading.Thread(target=trigger).start()


def does_user_have_access_to_project(client_object, project_object, access_gte=1):
    access_count = AccessProvided.objects.filter(user_object=client_object, project_object=project_object, type=0, project_access_type__gte=access_gte).count()
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

def does_user_have_access_to_data_run(user_object, data_run_object, access_type = READ_GTE):
    # Directly querying DataRuns model with conditions that relate to AccessProvided
    data_run_array = DataRuns.objects.filter(
        accessprovided__type=1,
        accessprovided__data_run_access_type__gte=access_type,
        accessprovided__user_object=user_object
    ).distinct()

    if data_run_object in data_run_array:
        return True
    return False


def resize_image(file, max_dimension=800):
    return file

def upload_file_to_s3(file, s3_file_name, is_public=0):
    try:
        s3 = boto3.client('s3', aws_access_key_id=AWSS3_ACCESS_KEY_VALUE, aws_secret_access_key=AWSS3_SECRET_KEY_VALUE)
        if is_public == 1:
            ##Add /public/ to the file name
            s3_file_name = "public/" + s3_file_name

        s3.upload_fileobj(file, 'waveassistapps', s3_file_name)
        return True, s3_file_name
    except Exception as e:
        print("Error in upload_file_to_s3:" + str(e))
        return False, None
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
    node_dependencies = {node: set(node.run_after_nodes_array.all()) for node in all_nodes_set}
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
    all_nodes = all_nodes.prefetch_related('run_after_nodes_array')
    sub_nodes_set = get_connected_subgraph_set(start_node, all_nodes)
    success, start_node = fetch_start_node_in_node_set(sub_nodes_set)
    if not success:
        return False, [], "Issue with starting node. There needs to be exactly one enabled starting node in each DAG"
    is_cycle =  detect_cycle_in_node_set(start_node, sub_nodes_set)
    if is_cycle:
        return False, [] , "Invalid DAG: Cycle detected in the graph"
    else:
        return True, list(sub_nodes_set), "DAG is valid"


def get_code_for_node(node_object,project_key):
    node_python_code = node_object.python_code
    python_code = "def run_task():\n"
    python_code += "    " + node_python_code.replace("\n", "\n    ") + "\n\n"
    return python_code

def get_task_dict_for_node(node_object):
    task_dict = {
        "node_key": node_object.node_key,
        "project_key": node_object.project_object.project_key,
    }
    return task_dict

def get_data_and_dependencies_for_dag(project_object, node_array):
    dependency_dict = {}
    data_dict = {}
    # for each node in dag_object
    for node_object in node_array:
        node_code = get_code_for_node(node_object, project_object.project_key)
        node_task_dict = get_task_dict_for_node(node_object)
        node_task_dict["code_to_run"] = node_code
        data_dict[node_object.node_key] =  node_task_dict
        dependency_dict[node_object.node_key] = [node.node_key for node in node_object.run_after_nodes_array.all()]
    return data_dict, dependency_dict

def generate_dag_visualization(dag_dict):
    dot = Digraph(comment='DAGs Visualization')

    # Define a consistent color palette
    base_color = "#428d4f"

    for i, (start_node, node_list) in enumerate(dag_dict.items()):
        with dot.subgraph(name=f'cluster_{start_node.node_key}') as subgraph:
            subgraph.attr(color=base_color, fontname="Open Sans")
            subgraph.node(start_node.node_key, color=base_color, shape="box", style="rounded")

            # Create nodes and edges
            for node in node_list:
                subgraph.node(node.node_key, color=base_color, shape="box", style="rounded", fontname="Open Sans")
                for dep in node.run_after_nodes_array.all():
                    subgraph.edge(dep.node_key, node.node_key, color=base_color, fontname="Open Sans")

    # Render the graph to a PNG in memory
    image_stream = BytesIO()
    image_stream.write(dot.pipe(format='png'))
    image_stream.seek(0)  # Reset the stream position to the beginning
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
        response = requests.get(
            LOKI_URL + '/loki/api/v1/label/job/values'
        )
        response_dict = response.json()
        options_array = response_dict['data']
        return options_array
    except:
        return []


def fetch_loki_logs(query, start_ts, end_ts):
    logs = []
    try:
        response = requests.get(
            LOKI_URL + '/loki/api/v1/query_range',
            params={
                'query': query,
                'start': start_ts,
                'end': end_ts,
                'limit': LOGS_LIMIT,
                'direction': 'backward'  # Fetch logs in reverse order (latest logs first)
            }
        )

        response_dict = response.json()
        result_array = response_dict['data']['result']
        for result_dict in result_array:
            try:
                all_values = result_dict['values']
                for values_array in all_values:
                    try:
                        log_message = values_array[1]
                        if log_message != "":
                            log_message = re.sub(r"\[.*?]", "", log_message).strip()
                            log_dict = {
                                'log': log_message,
                                'timestamp': datetime.fromtimestamp(int(values_array[0]) / 1000000000).strftime(
                                    '%Y-%m-%d %H:%M:%S')
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
    jobs_regex = "|".join([f'{job}' for job in selected_jobs])
    query = f'{{job=~"{jobs_regex}"'

    if len(node_key_array)>0:
        # Create a regex pattern for the node keys
        nodes_regex = "|".join([f'{node}' for node in node_key_array])
        query += f', node=~"{nodes_regex}"'

    query += '}'
    return query





import pymongo
import requests
from requests.auth import HTTPDigestAuth
mongo_url = "REMOVED_CREDENTIAL"
public_key = 'nzaopldm'
private_key = 'REMOVED_CREDENTIAL'

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

    group_id = '67a20af1d579ac023d1d022d'
    # Use MongoDB Atlas API to create the user
    url = f"https://cloud.mongodb.com/api/atlas/v1.0/groups/{group_id}/databaseUsers"
    headers = {
        "Content-Type": "application/json"
    }
    user_data = {
        "databaseName": 'admin',
        "username": username,
        "password": password,
        "roles": [
            {"databaseName": db_name, "roleName": "dbAdmin"}
        ]
    }

    # Make the POST request with HTTP Digest Authentication
    response = requests.post(url, json=user_data, headers=headers, auth=HTTPDigestAuth(public_key, private_key))

    if response.status_code == 201:
        print("User created successfully.")
        print(response.json())
    else:
        print("Failed to create user:", response.json())
        return None, None


    # Generate and return the connection URL for the new user
    url = (
        f"mongodb+srv://{username}:{password}@waveassistcluster.9ju27.mongodb.net/{db_name}"
    )

    return url, db_name
def get_database_name(user_object):
    return 'wa_' + str(user_object.uid)[:20]




def generate_filter_pattern(node_key_csv, project_object):
    # Construct filter_pattern
    if node_key_csv:
        # Split CSV into a list of node keys
        node_key_array = node_key_csv.split(',')
        node_key_array = [node_key.strip() for node_key in node_key_array if node_key]

        # Construct OR conditions for node_key
        node_key_conditions = " || ".join([f'$.extra.node_key = "{node_key}"' for node_key in node_key_array])

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
                "environment": [
                    {
                        "name": "ACCOUNT_ID",
                        "value": f"{uid}"
                    }
                ],
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
                        "awslogs-stream-prefix": "ecs"
                    },
                    "secretOptions": []
                },
                "systemControls": []
            }
        ],
        "family": f"WaveAssistWorkerTasks__{uid}",
        "taskRoleArn": "arn:aws:iam::713358430452:role/ecsTaskExecutionRole",
        "executionRoleArn": "arn:aws:iam::713358430452:role/ecsTaskExecutionRole",
        "networkMode": "awsvpc",
        "volumes": [],
        "placementConstraints": [],

        "requiresCompatibilities": [
            "FARGATE"
        ],
        "cpu": "256",
        "memory": "1024",
        "runtimePlatform": {
            "cpuArchitecture": "X86_64",
            "operatingSystemFamily": "LINUX"
        },

    }
