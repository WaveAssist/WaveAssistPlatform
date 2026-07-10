"""Account-level, multi-brand endpoints (Phase 0).

All additive: existing flows never call these, so shipping them changes nothing for
current users. They back the rebrand's MCP-token rotation and the GitZoid trial meter.
"""

from django.db.models import Sum, Count

from .Utils.responseParser import ResponseParser
from .Utils.utils import get_param
from .models import Account, UsageLedger


def _get_account_by_uid(uid):
    """Resolve an account by its uid (== account_uid). Returns None if missing."""
    if not uid:
        return None
    try:
        return Account.objects.get(account_uid=uid)
    except Account.DoesNotExist:
        return None


def _trial_dict(account):
    """User-facing trial state for an account (numbers the frontend can render)."""
    used = account.trial_credits_used or 0
    limit = account.trial_credits_limit or 0
    remaining = max(0.0, limit - used)
    return {
        "product": account.product,
        "plan_name": account.plan_name,
        "is_premium": account.is_premium,
        "mcp_token": account.mcp_token or account.ensure_mcp_token(),
        "trial_credits_used": used,
        "trial_credits_limit": limit,
        "trial_credits_remaining": remaining,
        "trial_exhausted": remaining <= 0,
    }


def regenerate_mcp_token(request):
    """Issue a fresh MCP bearer token for the account, invalidating the old one.

    Identity (uid) is untouched, so no other API is affected. This is the 'Regenerate'
    button on the WaveAssist Credits page.
    """
    uid = get_param(request, "uid")
    account = _get_account_by_uid(uid)
    if account is None:
        return ResponseParser.getParsedErrorMessage("Account not found.")

    account.mcp_token = Account.generate_mcp_token()
    account.save(update_fields=["mcp_token"])
    return ResponseParser.getParsedSuccessMessage(
        {"mcp_token": account.mcp_token}, "200", "MCP token regenerated."
    )


def resolve_mcp_token(request):
    """Exchange an MCP bearer token for its account identity.

    Called at the MCP edge (the WaveAgent server) to turn the rotatable token back into
    the uid that every downstream API already expects. Internal-only resolver.
    """
    token = get_param(request, "mcp_token") or get_param(request, "token")
    if not token:
        return ResponseParser.getParsedErrorMessage("Missing mcp_token.")
    try:
        account = Account.objects.get(mcp_token=token)
    except Account.DoesNotExist:
        return ResponseParser.getParsedErrorMessage("Invalid MCP token.")

    return ResponseParser.getParsedSuccessMessage(
        {"uid": account.account_uid, "product": account.product},
        "200",
        "Token resolved.",
    )


def get_trial_status(request):
    """Read-only trial / plan state for the account (drives the GitZoid Billing page)."""
    uid = get_param(request, "uid")
    account = _get_account_by_uid(uid)
    if account is None:
        return ResponseParser.getParsedErrorMessage("Account not found.")

    return ResponseParser.getParsedSuccessMessage(
        _trial_dict(account), "200", "Trial status."
    )


def get_run_usage(request):
    """Per-run LLM usage for a project, aggregated from the analytics ledger.

    Read-only. Drives the runs-page usage display (WaveAssist only — the frontend
    gates it by brand). Optionally narrowed to a single run_id. Returns one row per
    run with summed tokens/cost and the distinct models used. Empty until the
    instrumented SDK (>=0.8.11) records rows, so it degrades to "no data" cleanly.
    """
    uid = get_param(request, "uid")
    account = _get_account_by_uid(uid)
    if account is None:
        return ResponseParser.getParsedErrorMessage("Account not found.")

    project_key = get_param(request, "project_key") or ""
    run_id = get_param(request, "run_id")

    qs = UsageLedger.objects.filter(account=account, source="llm")
    if project_key:
        qs = qs.filter(project_key=project_key)
    if run_id:
        qs = qs.filter(run_id=run_id)

    # Aggregate in the DB (GROUP BY run_id), not by pulling the whole — potentially large —
    # row set into Python. Returns one row per run. Models are collected via a second,
    # equally-bounded DISTINCT query (MySQL has no portable array-agg).
    agg_rows = qs.values("run_id").annotate(
        calls=Count("id"),
        input_tokens=Sum("input_tokens"),
        output_tokens=Sum("output_tokens"),
        cost_usd=Sum("cost_usd"),
    )

    models_by_run = {}
    for rid, model in qs.exclude(model="").values_list("run_id", "model").distinct():
        models_by_run.setdefault(rid or "", set()).add(model)

    runs = []
    for a in agg_rows:
        rid = a["run_id"] or ""
        runs.append({
            "run_id": rid,
            "calls": a["calls"] or 0,
            "input_tokens": a["input_tokens"] or 0,
            "output_tokens": a["output_tokens"] or 0,
            "cost_usd": round(a["cost_usd"] or 0.0, 6),
            "models": sorted(models_by_run.get(rid, set())),
        })

    return ResponseParser.getParsedSuccessMessage({"runs": runs}, "200", "Run usage.")
