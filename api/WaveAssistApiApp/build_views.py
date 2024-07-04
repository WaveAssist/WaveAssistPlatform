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

##ToDo: Test runs logic pending.


def build_project(request): ##TCW
    ##Check of write access to project.
    success, message, user_object, project_object = validator.validate_user_and_project(request, access_level_gte=ADMIN_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    all_nodes = project_object.nodes_set.filter(is_enabled=True)
    starting_nodes = all_nodes.filter(is_starting_node=True, is_enabled=True)
    all_dags_of_project = project_object.dag_set.filter(is_enabled=True).prefetch_related('start_node')

    #Check if there are any starting nodes
    if len(starting_nodes) == 0:
        return ResponseParser.getParsedErrorMessage('No enabled starting nodes found in the project to build..')

    try:
        for start_node in starting_nodes:
            success, node_list, message = utils.check_dag(start_node, all_nodes)
            if not success:
                return ResponseParser.getParsedErrorMessage(message)
            ##Check if the DAG exists in the project
            dag_key = project_object.project_key + "-" + start_node.node_key
            ##Check if a DAG with the same key exists in all_dags_of_project, locally.
            matching_dag = next((dag for dag in all_dags_of_project if dag.dag_key == dag_key), None)

            if matching_dag:
                ##Update
                matching_dag.interval_schedule = start_node.interval_schedule
                matching_dag.node_array.set(node_list)
                matching_dag.save()

            else:
                ##Create
                dag_object = DAG.objects.create(
                    dag_key=dag_key,
                    project_object=project_object,
                    start_node=start_node,
                    interval_schedule=start_node.interval_schedule,
                    is_enabled=True
                )
                dag_object.node_array.set(node_list)
                dag_object.save()

    except Exception as e:
        return ResponseParser.getParsedErrorMessage('Error in Building: DAG creation or updation failed: ' + str(e))

    ##For those DAG's where the DAG's starting_node is not in the project's starting_nodes, delete or mark inactive.
    try:
        for dag in all_dags_of_project:
            if dag.start_node not in starting_nodes:
                dag.is_enabled = False
                dag.save()
    except:
        return ResponseParser.getParsedErrorMessage('Error in Building: Unused DAG deletion failed.')

    build_dict = {'build_status': 'build successful'}
    return ResponseParser.getParsedSuccessMessage(build_dict, '200', 'Project built successfully.')

def start_project_for_data_run(request):  ##TCW
    success, message, user_object , data_run_object = validator.validate_user_and_data_run(request, WRITE_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    project_object = data_run_object.project_object
    all_dags_of_project = project_object.dag_set.filter(is_enabled=True)

    ##For those DR's where the DR's DAG_run is not in the DAG's DagRuns, delete or mark inactive.
    all_dag_runs_of_data_run = data_run_object.dagrun_set.filter(is_enabled=True)
    for dag_run in all_dag_runs_of_data_run:
        if dag_run.dag_object not in all_dags_of_project:
            dag_run.is_enabled = False
            periodic_task = dag_run.periodic_task
            periodic_task.enabled = False
            periodic_task.save()
            dag_run.save()

    for dag_object in all_dags_of_project:
        data_dict, dependency_dict = utils.get_data_and_dependencies_for_dag(dag_object)
        dag_kwargs = json.dumps({
            'dependencies_dict': dependency_dict,
            'data_dict': data_dict,
            'collection_key': data_run_object.data_run_key
        })
        interval = dag_object.interval_schedule

        ##Check if a DAG run exists for this DAG and this data_run
        dag_run_key = dag_object.dag_key + "-" + data_run_object.data_run_key
        dag_run_object = None
        try:
            dag_run_object = DAGRun.objects.get(dag_run_key=dag_run_key, is_enabled=True)
        except:
            pass

        if dag_run_object:
            ##Update
            dag_run_object.is_running = True
            periodic_task = dag_run_object.periodic_task
            periodic_task.enabled = True
            periodic_task.interval = interval
            periodic_task.kwargs = dag_kwargs
            periodic_task.save()
            dag_run_object.save()
        else:
            ##Create
            periodic_task = PeriodicTask.objects.create(
                interval=interval,  # Link the schedule
                name=dag_run_key,  # Name of the periodic task
                task='celery_worker.run_dag',  # Use 'celery.chain' for chaining tasks
                kwargs=dag_kwargs,  # Serialize the workflow
                one_off=False,  # If True, the task will run only once
                enabled=True  # Whether this task is enabled
            )
            periodic_task.save()
            dag_run_object = DAGRun.objects.create(
                dag_run_key=dag_run_key,
                dag_object=dag_object,
                data_run_object=data_run_object,
                is_running=True,
                periodic_task = periodic_task,
                is_enabled=True
            )
            dag_run_object.save()
    return ResponseParser.getParsedSuccessMessage({}, '200', 'Successfully started the data run for your project.')

def stop_project_for_data_run(request): ##TCW
    success, message, user_object, data_run_object = validator.validate_user_and_data_run(request, WRITE_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    all_dag_runs_of_data_run = data_run_object.dagrun_set.filter(is_enabled=True)
    for dag_run in all_dag_runs_of_data_run:
        dag_run.is_running = False
        periodic_task = dag_run.periodic_task
        periodic_task.enabled = False
        periodic_task.save()
        dag_run.save()

    return ResponseParser.getParsedSuccessMessage({}, '200', 'Successfully stopped the data run for your project.')
