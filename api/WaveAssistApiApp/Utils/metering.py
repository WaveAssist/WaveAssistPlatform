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
    NODE_ACTION_TYPE_PATTERNS,
    CIRCUIT_BREAKER_CONSECUTIVE_FAILURES,
)
from . import utils

logger = logging.getLogger(__name__)

# Plans that mean "still free / on trial". A GitZoid account leaves the trial the moment
# it lands on a paid plan (plan_name is what payments set — NOT is_premium).
_FREE_PLANS = {None, "", "starter"}


def account_is_on_trial(account):
    """True for a GitZoid account that hasn't upgraded to a paid plan yet."""
    return account.product == "gitzoid" and (account.plan_name in _FREE_PLANS)


def trial_blocks_run(account):
    """True when a GitZoid trial account has spent its budget and must be blocked from
    running until it upgrades. Always False for WaveAssist and paid accounts, so it can
    never block a non-trial run."""
    if not account or not account_is_on_trial(account):
        return False
    remaining = (account.trial_credits_limit or 0) - (account.trial_credits_used or 0)
    return remaining <= 0


def map_node_to_action_type(node_key, chain_label=None):
    """Map a node's identity to a trial action_type, or None if nothing matches.

    Matches specific substrings of the lowercased ``node_key``/``chain_label`` in the
    order defined by NODE_ACTION_TYPE_PATTERNS (most specific first).
    """
    haystack = " ".join(
        part for part in [str(node_key or ""), str(chain_label or "")] if part
    ).lower()
    if not haystack.strip():
        return None
    for action_type, patterns in NODE_ACTION_TYPE_PATTERNS:
        if any(pattern in haystack for pattern in patterns):
            return action_type
    return None


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

    idem = f"trial:{run_id}:{node_key}"
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


def _active_deployment_for(project, data_run):
    return (
        Deployments.objects.filter(
            project_object=project, data_run_object=data_run, is_running=True
        )
        .order_by("-created_at")
        .first()
    )


def register_run_success(project, data_run):
    """Reset a deployment's consecutive-failure counter after any successful run."""
    deployment = _active_deployment_for(project, data_run)
    if deployment is None or (deployment.consecutive_failures or 0) == 0:
        return
    deployment.consecutive_failures = 0
    deployment.save(update_fields=["consecutive_failures"])


def register_run_failure(project, data_run):
    """Increment the failure counter; auto-pause the deployment at the threshold.

    Returns True if the deployment was paused by this call.
    """
    deployment = _active_deployment_for(project, data_run)
    if deployment is None:
        return False
    deployment.consecutive_failures = (deployment.consecutive_failures or 0) + 1
    if deployment.consecutive_failures >= CIRCUIT_BREAKER_CONSECUTIVE_FAILURES:
        # utils.stop_deployment flips is_running + disables the celery-beat PeriodicTask.
        try:
            utils.stop_deployment(deployment)
        except Exception as e:  # never let a pause failure break run recording
            logger.warning("Circuit breaker: stop_deployment failed: %s", e)
        deployment.consecutive_failures = 0
        deployment.save(update_fields=["consecutive_failures", "is_running"])
        return True
    deployment.save(update_fields=["consecutive_failures"])
    return False


def handle_run_terminal(project, node, data_run, *, run_id="", did_succeed=True):
    """Single entry point for the run-completion hook, scoped to GitZoid.

    WaveAssist deployments are completely unaffected: we resolve the account once and bail
    unless it's a GitZoid account, so no metering runs and — crucially — the circuit
    breaker never auto-pauses an existing WaveAssist agent. For GitZoid: on success, meter
    the trial (if trialling and the node maps to an action) and reset the failure counter;
    on failure, advance the breaker. All best-effort; the caller also wraps in try/except.
    """
    if project is None:
        return
    account = resolve_account_for_project(project)
    if account is None or account.product != "gitzoid":
        return

    if did_succeed:
        if node is not None and account_is_on_trial(account):
            action_type = map_node_to_action_type(
                getattr(node, "node_key", None), getattr(node, "chain_label", None)
            )
            if action_type:
                meter_trial_success(
                    account,
                    action_type,
                    project_key=getattr(project, "project_key", "") or "",
                    run_id=run_id or "",
                    node_key=getattr(node, "node_key", "") or "",
                )
        register_run_success(project, data_run)
    else:
        register_run_failure(project, data_run)
