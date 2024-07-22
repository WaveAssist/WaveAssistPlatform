import json
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
import datetime

##ToDo: Runs API pending.
##ToDo: Logs pending.

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
                interval_schedule = start_node.interval_schedule

                ##Create DAG object
                dag_key = "DAG_" + start_node.node_key + '_' + deployment_key
                dag_object = DAG.objects.create(
                    key = dag_key,
                    start_node = start_node,
                    is_running = True,
                    interval_schedule = interval_schedule,
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
                    interval= interval_schedule,  # Link the schedule
                    name=dag_key,  # Name of the periodic task
                    task='celery_worker.run_dag',  # Use 'celery.chain' for chaining tasks
                    kwargs=dag_kwargs,  # Serialize the workflow
                    one_off=False,  # If True, the task will run only once
                    enabled=True  # Whether this task is enabled
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
