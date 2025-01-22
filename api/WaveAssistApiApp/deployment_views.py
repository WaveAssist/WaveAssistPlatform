import json
import uuid

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
    starting_nodes = all_nodes.filter(is_starting_node=True, is_enabled=True)

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
                dag_key = "DAG_" + start_node.node_key + '_' + deployment_key
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
                    task='celery_worker.run_dag',  # Use 'celery.chain' for chaining tasks
                    kwargs=dag_kwargs,  # Serialize the workflow
                    one_off=False,  # If True, the task will run only once
                    enabled=True,  # Whether this task is enabled,
                    queue=queue_name
                )
                periodic_task.save()
                dag_object.periodic_task = periodic_task
                dag_object.save()
    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Error in deploying the project: ' + str(e))


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
    dag_key = "DAG_" + start_node.node_key + '_test_run_' + data_run_object.data_run_key + '_' + str(datetime.now())
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

    output_dict = {'dag': dag_object.get_dict()}
    output_dict['run_id'] = result.id

    return ResponseParser.getParsedSuccessMessage(output_dict, '200', 'Successfully started the DAG')
