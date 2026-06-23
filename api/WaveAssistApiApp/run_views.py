
import os
from pymongo import MongoClient
from .Utils.responseParser import ResponseParser
from .Utils.constants import *
from WaveAssistApi.settings import MONGO_CONNECTION_STRING
import WaveAssistApiApp.Utils.validator as validator
import WaveAssistApiApp.Utils.utils as utils
from WaveAssistApiApp.models import *

# Reused across requests (pymongo clients are thread-safe and pool internally) — the runs page polls
# every 5s, so a fresh client + TLS/topology handshake per call would be wasteful.
_mongo_client = None


def _mongo():
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGO_CONNECTION_STRING)
    return _mongo_client


def _label_for(chain_label, project_name, index, total):
    """Pure chain-label fallback: the node's chain_label if set, else the project name — suffixed
    '#index' only when the project has more than one chain. Never a raw node key."""
    label = (chain_label or "").strip()
    if label:
        return label
    pname = (project_name or "").strip() or "Run"
    return f"{pname} #{index}" if total > 1 else pname


def _chain_label_map(project_object):
    """{starting_node_id: display label} for a project, in stable id order, applying _label_for."""
    starts = list(Nodes.objects.filter(project_object=project_object,
                                       is_starting_node=True).order_by("id"))
    total = len(starts)
    pname = getattr(project_object, "name", None)
    return {n.id: _label_for(getattr(n, "chain_label", None), pname, i, total)
            for i, n in enumerate(starts, start=1)}


def _humanize_schedule(node):
    """A short cadence string for a starting node ('every 2 minutes' / a cron line), or '' if none."""
    if node is None:
        return ""
    try:
        iv = node.interval_schedule
        if iv:
            every, period = iv.every, str(iv.period)
            unit = period[:-1] if (every == 1 and period.endswith("s")) else period
            return f"every {every} {unit}"
    except Exception:
        pass
    try:
        c = node.crontab_schedule
        if c:
            return f"cron {c.minute} {c.hour} {c.day_of_month} {c.month_of_year} {c.day_of_week}"
    except Exception:
        pass
    return ""


def _idle_run_ids(db_name, data_run_key, run_ids):
    """Set of run_ids that wrote a `run_idle` flag — one batched Mongo $in query over the project's
    env collection. The per-user database is `wa_<uid>` (utils.get_database_name), NOT the literal
    DB_NAME; run-based keys are stored as `<data_key>_<run_id>`. Any Mongo error degrades to
    'none idle' (safe: a run is shown rather than wrongly hidden)."""
    idle = set()
    if not run_ids or not data_run_key or not db_name:
        return idle
    try:
        coll = _mongo()[db_name][data_run_key]
        wanted = {f"run_idle_{rid}": rid for rid in run_ids}
        for doc in coll.find({IO_DATA_KEY: {"$in": list(wanted.keys())}}, {IO_DATA_KEY: 1}):
            rid = wanted.get(doc.get(IO_DATA_KEY))
            if rid:
                idle.add(rid)
    except Exception:
        pass
    return idle


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

    # Chain labels (config or project-name fallback) + which runs are idle (one batched Mongo read).
    label_map = _chain_label_map(project_object)
    project_name = getattr(project_object, "name", None)
    idle_set = _idle_run_ids(utils.get_database_name(user_object),
                             getattr(data_run_object, "data_run_key", None),
                             [d.run_id for d in dag_runs_array if d.run_id])

    dag_dict_array = []
    for dag_run_object in dag_runs_array:
        dag_dict = dag_run_object.get_dict()
        node_runs = list(NodeRuns.objects.filter(dag_run_object=dag_run_object)
                         .select_related('node_object'))
        node_statuses = [nr.status for nr in node_runs]
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

        # finished_at = max node finished_at; started_at = min node started_at
        finished_times = [nr.finished_at for nr in node_runs if nr.finished_at]
        dag_finished_at = max(finished_times) if finished_times else None
        started_times = [nr.started_at for nr in node_runs if nr.started_at]
        dag_started_at = min(started_times) if started_times else None

        # Which chain is this run? -> the starting node among the run's nodes.
        start_node = next((nr.node_object for nr in node_runs
                           if nr.node_object and nr.node_object.is_starting_node), None)
        # label_map.get can miss for a stale/deleted starting node id → always fall back, never None.
        chain_label = (label_map.get(start_node.id) if start_node else None) or _label_for(None, project_name, 1, 1)

        # is_idle only if the assistant flagged it AND the run didn't fail (status wins).
        is_idle = (dag_run_object.run_id in idle_set) and dag_status != 'FAILED'

        dag_dict['status'] = dag_status
        dag_dict['finished_at'] = dag_finished_at
        dag_dict['started_at'] = dag_started_at
        dag_dict['chain_label'] = chain_label
        dag_dict['cadence'] = _humanize_schedule(start_node)
        dag_dict['is_idle'] = is_idle
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
