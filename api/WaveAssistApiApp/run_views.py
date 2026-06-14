
import os
from .Utils.responseParser import ResponseParser
from .Utils.constants import *
import WaveAssistApiApp.Utils.validator as validator
from WaveAssistApiApp.models import *


def fetch_dag_runs(request):  # TCW
    ##Validate Request
    success, message, user_object, project_object = validator.validate_user_and_project(request,
                                                                                        access_level_gte=READ_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    ##Validate Request
    success, message, user_object, data_run_object = validator.validate_user_and_data_run(request,
                                                                                          access_level_gte=READ_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    dag_runs_array = DagRuns.objects.filter(
        project_object=project_object,
        data_run_object=data_run_object
    ).order_by('-created_at')[:100]

    dag_dict_array = []
    for dag_run_object in dag_runs_array:
        dag_dict = dag_run_object.get_dict()
        node_runs = NodeRuns.objects.filter(dag_run_object=dag_run_object)
        node_statuses = list(node_runs.values_list('status', flat=True))
        if not node_statuses:
            dag_status = 'PENDING'
        elif all(s == 'SUCCESS' for s in node_statuses):
            dag_status = 'SUCCESS'
        elif any(s == 'FAILED' for s in node_statuses):
            dag_status = 'FAILED'
        elif any(s == 'RETRY' for s in node_statuses):
            dag_status = 'RETRY'
        elif any(s == 'STARTED' for s in node_statuses):
            dag_status = 'STARTED'
        else:
            dag_status = 'PENDING'

        # Calculate finished_at: max of all node finished_at
        finished_times = [nr.finished_at for nr in node_runs if nr.finished_at]
        dag_finished_at = max(finished_times) if finished_times else None

        ## Calculate started_at: min of all node started_at
        started_times = [nr.started_at for nr in node_runs if nr.started_at]
        dag_started_at = min(started_times) if started_times else None

        # Add status and finished_at to dag_dict
        dag_dict['status'] = dag_status
        dag_dict['finished_at'] = dag_finished_at
        dag_dict['started_at'] = dag_started_at
        dag_dict_array.append(dag_dict)
    data_dict = {'dag_run_array': dag_dict_array}
    return ResponseParser.getParsedSuccessMessage(data_dict, '200', 'Deployments fetched successfully.')


def fetch_node_runs(request):  # TCW
    ## Validate user and project
    success, message, user_object, project_object = validator.validate_user_and_project(request,
                                                                                        access_level_gte=READ_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    ## Validate user and data run
    success, message, user_object, data_run_object = validator.validate_user_and_data_run(request,
                                                                                          access_level_gte=READ_GTE)
    if not success:
        return ResponseParser.getParsedErrorMessage(message)

    # Get DAG Run ID from request
    dag_run_id = request.POST.get('dag_run_id')
    if not dag_run_id:
        return ResponseParser.getParsedErrorMessage("dag_run_id is required.")

    try:
        dag_run_object = DagRuns.objects.get(run_id=dag_run_id)
    except DagRuns.DoesNotExist:
        return ResponseParser.getParsedErrorMessage("DAG Run not found.")

    # Fetch associated node runs
    node_runs = NodeRuns.objects.filter(dag_run_object=dag_run_object).select_related('node_object')
    node_run_array = []

    for nr in node_runs:
        node_data = nr.get_dict()
        # node_object may be NULL for runs whose Node was deleted by a project upgrade
        node_data['node_key'] = nr.node_object.node_key if nr.node_object else 'deleted_node'
        node_data['node_name'] = nr.node_object.name if nr.node_object else 'Deleted Node'
        node_run_array.append(node_data)

    data_dict = {
        'dag_run_id': dag_run_object.id,
        'node_runs': node_run_array
    }

    return ResponseParser.getParsedSuccessMessage(data_dict, '200', 'Node Runs fetched successfully.')
