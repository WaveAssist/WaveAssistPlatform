import json
import uuid

from django.http import JsonResponse
from django.shortcuts import render
from .models import *
from .Utils.responseParser import ResponseParser
import pandas as pd
from io import StringIO as StringIO
from .Utils.constants import *
import WaveAssistApiApp.Utils.utils as utils
import WaveAssistApiApp.Utils.validator as validator
from WaveAssistApi.celery import app
from celery import chain, group
from kombu.serialization import dumps
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from datetime import datetime
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from WaveAssistApiApp.data_views import set_data_for_key
from django.test import Client
from celery.exceptions import TimeoutError

import json
client = Client()

##ToDo: Runs API pending.
##ToDo: Logs pending.


def generate_dag_image(request):
    success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=ADMIN_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    all_nodes = project_object.nodes_set.filter(is_enabled=True)
    starting_nodes = all_nodes.filter(is_starting_node=True, is_enabled=True)

    ##Additional Check. Already done during node save.
    dag_dict = {}
    for start_node in starting_nodes:
        success, node_list, message = utils.check_dag(start_node, all_nodes)
        dag_dict[start_node] = node_list
        if not success:
            return ResponseParser.getParsedErrorMessage(message)

    image_stream = utils.generate_dag_visualization(dag_dict)
    file_name = 'API/' + str(uuid.uuid4()) + '.png' ##Better name if needed.
    success, s3_key = utils.upload_file_to_s3(image_stream, file_name, 1)

    if success:
        output_dict =  {"status": "success", "s3_key": s3_key}
        return ResponseParser.getParsedSuccessMessage(output_dict, '200', 'Successfully uploaded image to S3')
    else:
        return ResponseParser.getParsedErrorMessage('Failed to upload image to S3')


def deploy_project(request): ##TCW
    #### ------ Validations Start -------- ####
    ##Check of write access to project.
    success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=ADMIN_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    success, message, user_object, data_run_object = validator.validate_user_and_data_run(request, ADMIN_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    all_nodes = project_object.nodes_set.filter(is_enabled=True)
    starting_nodes = all_nodes.filter(
        is_starting_node=True,
        is_enabled=True
    ).exclude(schedule_type='none')

    queue_name = 'queue_' + str(user_object.uid)

    #Check if there are any starting nodes
    if len(starting_nodes) == 0:
        return ResponseParser.getParsedErrorMessage('No enabled starting nodes found in the project to Deploy..')

    ##Check if the version is unique
    version = request.POST.get('version', '1.0.0')
    all_deployments = Deployments.objects.filter(project_object=project_object, version=version, data_run_object=data_run_object)
    if len(all_deployments) > 0:
        return ResponseParser.getParsedErrorMessage('Version already exists for the project. Please provide a unique version.')

    ##Additional Check. Already done during node save.
    dag_dict = {}
    for start_node in starting_nodes:
        success, node_list, message = utils.check_dag(start_node, all_nodes)
        dag_dict[start_node] = node_list
        if not success:
            return ResponseParser.getParsedErrorMessage(message)

    #### ------ Validations End -------- ####

    ##Stopping all previous Deployments of the project.
    all_deployments = Deployments.objects.filter(project_object=project_object, is_running=True, data_run_object=data_run_object)
    for deployment in all_deployments:
        try:
            utils.stop_deployment(deployment)
        except Exception as e:
            return ResponseParser.getParsedErrorMessage('Error in stopping the already running project: ' + str(e))


    ##Creating a fresh new deployment
    try:
        with transaction.atomic():
            deployment_key = "Deployment_" + version + '_' + data_run_object.data_run_key
            deployment_object = Deployments.objects.create(
                project_object=project_object,
                data_run_object=data_run_object,
                is_running=True,
                version=version,
                key = deployment_key
            )
            deployment_object.save()

            ##Create DAGs for the run, iterate through dag_dict
            for start_node, node_list in dag_dict.items():
                ##Create DAG object
                dag_key = "DAG_" + str(project_object.project_key) + "_" + start_node.node_key + '_' + deployment_key
                dag_object = DAG.objects.create(
                    key = dag_key,
                    start_node = start_node,
                    is_running = True,
                    interval_schedule = start_node.interval_schedule,
                    crontab_schedule = start_node.crontab_schedule,
                    parent_deployment = deployment_object
                )
                dag_object.save()
                dag_object.node_array.set(node_list)
                dag_object.save()

                data_dict, dependency_dict = utils.get_data_and_dependencies_for_dag(project_object, node_list)
                dag_kwargs = json.dumps({
                    'dependencies_dict': dependency_dict,
                    'data_dict': data_dict,
                    'collection_key': data_run_object.data_run_key,
                    'dag_key': dag_key,
                })

                periodic_task = PeriodicTask.objects.create(
                    interval= start_node.interval_schedule,  # Link the schedule
                    crontab= start_node.crontab_schedule,  # Link the schedule
                    name=dag_key,  # Name of the periodic task
                    task=DAG_TASK,  # Use 'celery.chain' for chaining tasks
                    kwargs=dag_kwargs,  # Serialize the workflow
                    one_off=False,  # If True, the task will run only once
                    enabled=True,  # Whether this task is enabled,
                    queue =queue_name
                )
                periodic_task.save()
                dag_object.periodic_task = periodic_task
                dag_object.save()
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Error in deploying the project: ' + str(e))

    ##Schedule email
    try:
        knock_data = {
            'project_name': project_object.name,
            'version_code': version,
            'deployment_key': deployment_object.key,
        }
        utils.run_knock_workflow(str(user_object.uid), 'deployed', knock_data)
    except:
        pass

    output_dict = {'deployment': deployment_object.get_dict()}
    return ResponseParser.getParsedSuccessMessage(output_dict, '200', 'Successfully deployed the project')



def stop_deployment(request): ##TCW
    success, message, user_object, deployment_object = validator.validate_user_and_deployment(request, ADMIN_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)
    try:
        utils.stop_deployment(deployment_object)
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Error in stopping the project: ' + str(e))

    output_dict = {'deployment': deployment_object.get_dict()}

    return ResponseParser.getParsedSuccessMessage(output_dict, '200', 'Successfully stopped the deployment.')




def run_code(request: object) -> JsonResponse:
    success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=ADMIN_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    project_key = project_object.project_key
    collection_key = project_key + '_default'
    node_key = str(uuid.uuid4())
    code_to_run = request.POST.get('code_to_run', '')
    task_dict = {
        'project_key': project_key,
        'node_key': node_key,
        'code_to_run': code_to_run,
        'task_key': node_key,
    }

    task_kwargs = {
        'task_dict': task_dict,
        'collection_key': collection_key,
        'task_key': node_key,
    }

    queue_name = 'queue_' + str(user_object.uid)
    task_run = app.send_task(RUN_TASK, kwargs=task_kwargs, queue=queue_name)
    try:
        timeout = int(request.POST.get('timeout', 10))
        result = task_run.get(timeout=timeout)
        output_dict = {'task_id': task_run.id, 'result': result}
    except TimeoutError:
        output_dict = {'task_id': task_run.id, 'result': "Running"}

    return ResponseParser.getParsedSuccessMessage(output_dict, '200', 'Successfully ran the code')


def run_dag(request): ##TCW
    ##Inputs are uid, project_key, data_run_key & start_node_key
    success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=ADMIN_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    success, message, user_object, data_run_object = validator.validate_user_and_data_run(request, ADMIN_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    start_node_key = request.POST.get('start_node_key', None)
    try:
        start_node = Nodes.objects.get(node_key=start_node_key, project_object=project_object, is_enabled=True, is_starting_node=True)
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Error in fetching the start node, or invalid start node: ' + str(e))

    all_nodes = project_object.nodes_set.filter(is_enabled=True)
    success, node_list, message = utils.check_dag(start_node, all_nodes)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    #### ------ Validations End -------- ####

    ##Create DAG object
    dag_key = "DAG_" + str(project_object.project_key) + '_' + start_node.node_key + '_test_run_' + data_run_object.data_run_key + '_' + str(datetime.now())
    dag_object = DAG.objects.create(
        key = dag_key,
        start_node = start_node,
        is_running = True,
    )
    dag_object.save()
    dag_object.node_array.set(node_list)
    dag_object.save()

    data_dict, dependency_dict = utils.get_data_and_dependencies_for_dag(project_object, node_list)
    dag_kwargs = {
        'dependencies_dict': dependency_dict,
        'data_dict': data_dict,
        'collection_key': data_run_object.data_run_key,
        'dag_key': dag_key,
    }
    queue_name = 'queue_' + str(user_object.uid)
    print("Sending task: " + str(dag_kwargs) + ", queue: " + queue_name)
    result = app.send_task(DAG_TASK, kwargs=dag_kwargs, queue=queue_name)
    # result = app.send_task(DAG_TASK, kwargs=dag_kwargs)

    output_dict = {'dag': dag_object.get_dict()}
    output_dict['run_id'] = result.id

    return ResponseParser.getParsedSuccessMessage(output_dict, '200', 'Successfully started the DAG')


@csrf_exempt
def webhook(request, uid, project_key, start_node_key, data_run_key):
    if request.method != 'POST':
        return ResponseParser.getParsedErrorMessage("Invalid request method. Only POST is allowed.")

    ##Store json to variable
    try:
        body = json.loads(request.body)
        payload = {
            'uid': uid,
            'project_key': project_key,
            'data_run_key': data_run_key,
            'data': body,
            'data_key': start_node_key + '_webhook_data',
            'data_type': 'json',
        }
        response = client.post('/data/set_data_for_key/', data=json.dumps(payload), content_type='application/json')
    except Exception as e:
        pass

    ##Need to retrieve the JSON and call the set_data_for_key API
    data = request.POST.copy()
    data.update({
        'uid':            str(uid),
        'project_key':    project_key,
        'start_node_key': start_node_key,
        'data_run_key':   data_run_key,
    })
    request.POST = data
    return run_dag(request)


@csrf_exempt
def email_webhook(request):
    """Handles inbound emails from Postmark's Parse Webhook."""
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    try:
        try:
            payload_json = json.loads(request.body.decode())
        except Exception:
            return JsonResponse({"error": "Invalid JSON payload"}, status=400)

        to_addr = payload_json.get("To", "")
        local_part = to_addr.split("@")[0]
        data = utils.decode_email_webhook_token(local_part)
        print("Decoded data from email token:", data)
        if not data:
            return ResponseParser.getParsedErrorMessage("Invalid email format or token.")

        uid, project_id, node_id, env_id = data.values()
        try:
            project = Project.objects.get(id=project_id)
            data_run = DataRuns.objects.get(id=env_id, project_object=project)
            node = Nodes.objects.get(id=node_id, project_object=project, is_enabled=True, is_starting_node=True)
        except:
            return ResponseParser.getParsedErrorMessage("Project, DataRun, or Node not found.")

        payload = {
            'uid': uid,
            'project_key': project.project_key,
            'data_run_key': data_run.data_run_key,
            'data': {
                'subject': payload_json.get("Subject", ""),
                'text': payload_json.get("TextBody", ""),
                'html': payload_json.get("HtmlBody", ""),
                'from': payload_json.get("From", ""),
            },
            'data_key': f"{node.node_key}_webhook_data",
            'data_type': 'json',
        }

        Client().post(
            '/data/set_data_for_key/',
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Prepare for DAG execution
        post_data = {
            'uid': uid,
            'project_key': project.project_key,
            'start_node_key': node.node_key,
            'data_run_key': data_run.data_run_key,
        }
        request.POST = post_data
        return run_dag(request)

    except Exception as e:
        return JsonResponse({"error": f"Exception: {str(e)}"}, status=500)
