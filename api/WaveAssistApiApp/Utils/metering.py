"""Server-side trial metering, usage-ledger writes, and drain guards (Phase 0).

These are pure helpers so the Celery event listener (capture_celery_events) and the SDK
endpoints share one implementation that can be unit-tested directly, without a running
worker. Everything here is defensive: metering must never break run recording, so callers
wrap these in try/except and they also guard internally and return quietly on bad input.
"""

import logging

from django.db import IntegrityError, transaction

from ..models import Account, AccessProvided, UsageLedger, Deployments
from .constants import (
    TRIAL_ACTION_COSTS,
    GITZOID_METER_NODES,
    IO_DATA_KEY,
)
from . import utils, runtime_flags

logger = logging.getLogger(__name__)

# Plans that mean "still free / on trial". A GitZoid account leaves the trial the moment
# it lands on a paid plan (plan_name is what payments set — NOT is_premium).
_FREE_PLANS = {None, "", "starter"}


def account_is_on_trial(account):
    """True for a GitZoid account that hasn't upgraded to a paid plan yet."""
    return runtime_flags.billing_enabled and account.product == "gitzoid" and (account.plan_name in _FREE_PLANS)


def trial_blocks_run(account):
    """True when a GitZoid trial account has spent its budget and must be blocked from
    running until it upgrades. Always False for WaveAssist and paid accounts, so it can
    never block a non-trial run."""
    if not account or not account_is_on_trial(account):
        return False
    remaining = (account.trial_credits_limit or 0) - (account.trial_credits_used or 0)
    return remaining <= 0


def map_node_to_action_type(node_key, chain_label=None):
    """Map a DELIVERABLE leaf node's key to its trial action_type, or None.

    Exact node_key lookup against GITZOID_METER_NODES — only the terminal nodes that
    represent delivered work are metered. Gate/fetch/init nodes (which succeed on every
    scheduled tick, including idle repos) return None and are never charged. chain_label
    is intentionally ignored: it's shared by every node in a chain, so matching on it would
    bill the whole chain. Kept as an accepted arg for call-site compatibility.
    """
    return GITZOID_METER_NODES.get(str(node_key or "").strip())


def resolve_account_for_project(project):
    """Best-effort owning Account for a project, via its admin AccessProvided row.

    GitZoid projects have a single owner, so this is unambiguous in practice. Returns
    None if no admin/owner or account can be found.
    """
    access = (
        AccessProvided.objects.filter(
            project_object=project, type=0, project_access_type__gte=3
        )
        .select_related("user_object")
        .first()
    )
    if not access or not getattr(access, "user_object", None):
        return None
    return Account.objects.filter(created_by_user=access.user_object).first()


def meter_trial_success(account, action_type, *, project_key="", run_id="", node_key=""):
    """Deduct a successful trial action from the budget, idempotently.

    Writes a negative UsageLedger row (source="trial") AND increments
    ``account.trial_credits_used`` in one transaction. Idempotent per (run_id, node_key):
    a retried/re-delivered event for the same node won't double-charge. No-ops when the
    account is not a trialling GitZoid account or the action is unknown.

    Returns the credits charged (0 if it no-op'd or was a duplicate).
    """
    if not account or not account_is_on_trial(account):
        return 0
    cost = TRIAL_ACTION_COSTS.get(action_type)
    if not cost:
        return 0

    # Idempotent per (run_id, action_type): one run charges each action at most once, even
    # if the event is re-delivered or a chain somehow completes the deliverable node twice.
    idem = f"trial:{run_id}:{action_type}"
    try:
        with transaction.atomic():
            UsageLedger.objects.create(
                account=account,
                project_key=project_key or "",
                run_id=run_id or "",
                node_key=node_key or "",
                source="trial",
                amount=-float(cost),
                billable=True,
                idempotency_key=idem,
            )
            # Re-read under the lock and bump the running total.
            acc = Account.objects.select_for_update().get(pk=account.pk)
            acc.trial_credits_used = (acc.trial_credits_used or 0) + float(cost)
            acc.save(update_fields=["trial_credits_used"])
            account.trial_credits_used = acc.trial_credits_used
        return cost
    except IntegrityError:
        # Duplicate (run_id, node_key) — already metered. Idempotent no-op.
        return 0


def stop_trial_deployments(project):
    """Disable a spent GitZoid trial's schedule so the worker is freed.

    When a trial hits 0 credits its runs can only ever be gated (they can't succeed until
    the account upgrades), yet the celery-beat PeriodicTask would otherwise keep firing
    every tick forever. Stopping the deployment disables that schedule. Idempotent — only
    running deployments are touched, so repeated calls are no-ops. Best-effort: a failure
    here must never break the credit-check response that calls it.
    """
    for deployment in Deployments.objects.filter(project_object=project, is_running=True):
        try:
            utils.stop_deployment(deployment)
        except Exception as e:
            logger.warning("Trial stop: stop_deployment failed: %s", e)


def resume_account_deployments(account):
    """Re-enable an account's stopped deployments after it lands on a paid plan.

    Mirror of stop_trial_deployments: once a GitZoid account upgrades to Pro, a schedule
    that was paused when the trial ran out should run again. Resolves the account's owned
    projects via its admin AccessProvided rows and resumes their stopped deployments.
    Best-effort so a payment webhook can never fail on this. Note: this resumes ANY stopped
    deployment the account owns, not only ones paused by trial exhaustion — acceptable while
    a GitZoid account owns a single deployment.
    """
    owner = getattr(account, "created_by_user", None)
    if owner is None:
        return
    project_ids = list(
        AccessProvided.objects.filter(
            user_object=owner, type=0, project_access_type__gte=3
        ).values_list("project_object_id", flat=True)
    )
    if not project_ids:
        return
    for deployment in Deployments.objects.filter(
        project_object_id__in=project_ids, is_running=False
    ):
        try:
            utils.resume_deployment(deployment)
        except Exception as e:
            logger.warning("Resume: resume_deployment failed: %s", e)


_mongo_client = None


def _mongo():
    """Lazily-created MongoClient for reading a run's run-scoped flags from the per-user store.
    Lazy on purpose: importing this module — and the pure unit tests that pass ``is_idle``
    explicitly — must never require pymongo or open a Mongo connection."""
    global _mongo_client
    if _mongo_client is None:
        from pymongo import MongoClient
        from WaveAssistApi.settings import MONGO_CONNECTION_STRING
        _mongo_client = MongoClient(MONGO_CONNECTION_STRING)
    return _mongo_client


def run_is_idle(account, data_run, run_id):
    """True if this run recorded a ``run_idle`` flag → it executed but delivered no billable work,
    so it must NOT be metered.

    A deliverable node "succeeds" (did_succeed=True means the code didn't raise) on EVERY scheduled
    tick, including idle ones where it shipped nothing — no new PR to review, a silent security
    scan, an off-week digest — and signalled that by calling ``waveassist.mark_run_idle()``. That
    writes ``run_idle_<run_id>`` into the per-user store (``wa_<uid>[<data_run_key>]``) BEFORE the
    node's TASK_COMPLETED event fires, so the flag is already visible when metering runs. Mirrors
    the batched read in ``run_views._idle_run_ids`` but for a single run.

    Fails OPEN toward not charging: any error, or a run we can't resolve, returns True. A metering
    read that cannot positively confirm real delivery must never over-charge a trial — a skipped
    charge only makes the trial last slightly longer, whereas a spurious charge is the exact bug
    this guards against. (This is the opposite default from ``_idle_run_ids``, which for DISPLAY
    errs toward showing a run; for BILLING the safe direction is to skip the charge.)
    """
    try:
        owner = getattr(account, "created_by_user", None)
        data_run_key = getattr(data_run, "data_run_key", "") or ""
        if owner is None or not data_run_key or not run_id:
            return True
        db_name = utils.get_database_name(owner)
        if not db_name:
            return True
        coll = _mongo()[db_name][data_run_key]
        doc = coll.find_one({IO_DATA_KEY: f"run_idle_{run_id}"}, {IO_DATA_KEY: 1})
        return doc is not None
    except Exception as e:
        logger.warning(
            "Trial metering: run_idle read failed for run %s; skipping charge: %s", run_id, e
        )
        return True


def handle_run_terminal(project, node, data_run, *, run_id="", did_succeed=True, is_idle=None):
    """Single entry point for the run-completion hook, scoped to GitZoid.

    WaveAssist deployments are completely unaffected: we resolve the account once and bail
    unless it's a GitZoid account, so no metering runs. For a trialling GitZoid account, a
    deliverable node that actually shipped work meters the trial. There is deliberately no failure
    handling: a crashing agent is left to retry (no auto-pause) — the only automatic stop is trial
    exhaustion, which is handled at the credit-check gate via stop_trial_deployments.

    A deliverable node reports did_succeed=True on every tick, so success alone does not mean work
    was delivered. An IDLE run (nothing to review/alert/digest, which the node marks via
    ``mark_run_idle()``) must not be charged. ``is_idle`` may be supplied by a caller that already
    knows (and by the unit tests); when left as None we read the run's ``run_idle`` flag from the
    per-user store via ``run_is_idle`` — only for a real metered candidate, so the lookup runs on a
    tiny subset of events. Best-effort; the caller also wraps in try/except.
    """
    if project is None:
        return
    account = resolve_account_for_project(project)
    if account is None or account.product != "gitzoid":
        return

    if not (did_succeed and node is not None and account_is_on_trial(account)):
        return
    action_type = map_node_to_action_type(
        getattr(node, "node_key", None), getattr(node, "chain_label", None)
    )
    if not action_type:
        return
    if is_idle is None:
        is_idle = run_is_idle(account, data_run, run_id)
    if is_idle:
        return
    meter_trial_success(
        account,
        action_type,
        project_key=getattr(project, "project_key", "") or "",
        run_id=run_id or "",
        node_key=getattr(node, "node_key", "") or "",
    )
