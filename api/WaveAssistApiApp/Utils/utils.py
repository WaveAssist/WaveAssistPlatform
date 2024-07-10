##PYTHON IMPORTS
import boto3
from ..models import *
##Custom
from WaveAssistApiApp.Utils.constants import *
from WaveAssistApiApp.Utils.Logger import Logger
from collections import deque
import re
import pytz

##Packages
logger = Logger()


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




def generate_integrations_code_text(project_object):
    python_code_text = ''
    integration_array = project_object.integration_array.all()
    for integration_object in integration_array:
        python_code_text += integration_object.import_code + '\n'
    return python_code_text


def generate_integrations_function_prefix(project_object):
    python_code_text = ''
    integration_array = project_object.integration_array.all()
    for integration_object in integration_array:
        python_code_text += integration_object.function_code + '\n'
    return python_code_text


def get_code_for_node(node_object, top_code, function_code, project_key):

    node_python_code = node_object.python_code
    node_python_code = function_code + node_python_code


    python_code = top_code
    ##Input parameters
    input_data_array = node_object.input_data_key_array.all().order_by(Lower('key'))
    parameters_string = ""
    for input_data_object in input_data_array:
        parameters_string += str(input_data_object.key) + ", "
    parameters_string += 'integrations_df=None, '
    parameters_string += 'project_key="' + str(project_key) + '",'


    python_code += "def run_task(" + parameters_string + "):\n"
    python_code += "    " + node_python_code.replace("\n", "\n    ") + "\n\n"

    ##Output check for return statement.
    output_data_array = node_object.output_data_key_array.all()
    if len(output_data_array) > 0 and python_code.find("return") == -1:
        return False, "Python code does not have a return statement for node: " + node_object.node_key

    return python_code

def get_task_dict_for_node(node_object):
    task_dict = {
        "node_key": node_object.node_key,
        "project_key": node_object.project_object.project_key,
        "input_keys_array": [data_key_object.key for data_key_object in node_object.input_data_key_array.all()],
        "output_keys_array": [data_key_object.key for data_key_object in node_object.output_data_key_array.all()]
    }
    return task_dict

def get_data_and_dependencies_for_dag(project_object, node_array):

    ##Project Specific things
    function_integration_code = generate_integrations_code_text(project_object)
    function_integration_prefix_code = generate_integrations_function_prefix(project_object)

    dependency_dict = {}
    data_dict = {}
    # for each node in dag_object
    for node_object in node_array:
        node_code = get_code_for_node(node_object, function_integration_code, function_integration_prefix_code, project_object.project_key)
        node_task_dict = get_task_dict_for_node(node_object)
        node_task_dict["code_to_run"] = node_code
        data_dict[node_object.node_key] =  node_task_dict
        dependency_dict[node_object.node_key] = [node.node_key for node in node_object.run_after_nodes_array.all()]
    return data_dict, dependency_dict



def stop_published_run(published_run):
    try:
        with transaction.atomic():
            published_run.is_running = False
            for dag in published_run.dag_set.all():
                dag.periodic_task.enabled = False
                dag.periodic_task.save()
                dag.is_running = False
                dag.save()
            published_run.save()
    except Exception as e:
        print(f"An error occurred: {e}")
        raise Exception("Could not stop the PublishedRun: " + str(e))

