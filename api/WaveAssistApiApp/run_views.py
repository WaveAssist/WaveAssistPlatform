
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


# Per-chain run window: each chain contributes its own most-recent N runs so a high-frequency chain
# (e.g. a 2-min PR review) never floods out a daily/weekly chain. ~20 is plenty for cards + a feed.
RUNS_PER_CHAIN = 20


def _chain_label_map(project_object, starting_nodes=None):
    """{starting_node_id: display label} for a project, in stable id order, applying _label_for."""
    if starting_nodes is None:
        starting_nodes = list(Nodes.objects.filter(project_object=project_object,
                                                   is_starting_node=True).order_by("id"))
    total = len(starting_nodes)
    pname = getattr(project_object, "name", None)
    return {n.id: _label_for(getattr(n, "chain_label", None), pname, i, total)
            for i, n in enumerate(starting_nodes, start=1)}


_DOW = {"0": "Sun", "1": "Mon", "2": "Tue", "3": "Wed", "4": "Thu", "5": "Fri", "6": "Sat", "7": "Sun"}


def _humanize_cron(c):
    """Turn a crontab schedule into a friendly cadence for the common shapes, e.g.
    '*/2 * * * *' -> 'every 2 minutes', '0 6 * * *' -> 'daily 06:00', '30 8 * * 1' -> 'weekly Mon 08:30'.
    Falls back to the raw 5-field cron line for anything unusual."""
    mn, hr, dom = str(c.minute).strip(), str(c.hour).strip(), str(c.day_of_month).strip()
    mon, dow = str(c.month_of_year).strip(), str(c.day_of_week).strip()
    raw = f"cron {mn} {hr} {dom} {mon} {dow}"

    if mn.startswith("*/") and hr == "*" and dom == "*" and mon == "*" and dow == "*":
        n = mn[2:]
        return f"every {n} minute{'' if n == '1' else 's'}" if n.isdigit() else raw
    if hr.startswith("*/") and mn.isdigit() and dom == "*" and mon == "*" and dow == "*":
        n = hr[2:]
        return f"every {n} hour{'' if n == '1' else 's'}" if n.isdigit() else raw
    if mn.isdigit() and hr.isdigit() and mon == "*":
        t = f"{int(hr):02d}:{int(mn):02d}"
        if dom == "*" and dow == "*":
            return f"daily {t}"
        if dom == "*" and dow in _DOW:
            return f"weekly {_DOW[dow]} {t}"
        if dow == "*" and dom.isdigit():
            return f"monthly day {dom} {t}"
    return raw


def _humanize_schedule(node):
    """A short cadence string for a starting node ('every 2 minutes' / 'weekly Mon 08:30'), or ''."""
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
            return _humanize_cron(c)
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

    # Balance the window PER CHAIN: each starting node contributes its own most-recent RUNS_PER_CHAIN
    # runs (found via that node's NodeRuns), so a 2-min chain can't crowd out a daily/weekly one.
    starting_nodes = list(Nodes.objects.filter(project_object=project_object,
                                               is_starting_node=True).order_by("id"))
    label_map = _chain_label_map(project_object, starting_nodes)
    project_name = getattr(project_object, "name", None)

    dag_ids = set()
    for sn in starting_nodes:
        dag_ids.update(NodeRuns.objects.filter(
            node_object=sn, dag_run_object__data_run_object=data_run_object
        ).order_by("-created_at").values_list("dag_run_object_id", flat=True)[:RUNS_PER_CHAIN])
    dag_runs_array = list(DagRuns.objects.filter(id__in=dag_ids).order_by("-created_at"))

    # ONE query for ALL node runs across the window, grouped by dag_run — was one query per dag_run
    # on every 5s poll. Collapses up to ~(20 * chains) round-trips into 1.
    nr_by_dag = {}
    for nr in NodeRuns.objects.filter(
        dag_run_object_id__in=[d.id for d in dag_runs_array]
    ).select_related('node_object'):
        nr_by_dag.setdefault(nr.dag_run_object_id, []).append(nr)

    # Which runs are idle (one batched Mongo read).
    idle_set = _idle_run_ids(utils.get_database_name(user_object),
                             getattr(data_run_object, "data_run_key", None),
                             [d.run_id for d in dag_runs_array if d.run_id])

    dag_dict_array = []
    for dag_run_object in dag_runs_array:
        dag_dict = dag_run_object.get_dict()
        node_runs = nr_by_dag.get(dag_run_object.id, [])
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
