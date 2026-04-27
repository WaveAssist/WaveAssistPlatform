"""
integrations_view.py — read-only catalog of Composio toolkits, actions,
and model recommendations.

Backed by Mongo `waveassist_integrations` (collections: tool_toolkits,
tool_actions, model_recommendations). Populated by:
  - Scripts/IntegrationAgent (toolkits, actions)
  - Scripts/ModelRegistry/load_recommendations.py (model_recommendations)
No auth — browsing the catalog is public.
"""

import json
import os

from .Utils.responseParser import ResponseParser
from .Utils.constants import COMPOSIO_API_KEY
from .Utils import validator as validator
from .Utils import utils as utils
from .Utils.utils import get_param
from pymongo import MongoClient, DESCENDING, ASCENDING
from WaveAssistApi.settings import MONGO_CONNECTION_STRING

os.environ.setdefault("COMPOSIO_API_KEY", COMPOSIO_API_KEY)


INTEGRATIONS_DB = "waveassist_integrations"
TOOLKITS_COLL = "tool_toolkits"
ACTIONS_COLL = "tool_actions"
MODEL_RECOMMENDATIONS_COLL = "model_recommendations"

_MODEL_RECOMMENDATION_FIELDS = {
    "_id": 0,
    "purpose": 1,
    "default": 1,
    "pro": 1,
    "description": 1,
    "updated_at": 1,
}

_TOOLKIT_FIELDS = {
    "_id": 0,
    "slug": 1,
    "name": 1,
    "description": 1,
    "logo": 1,
    "app_url": 1,
    "categories": 1,
    "tools_count": 1,
    "triggers_count": 1,
    "auth_schemes": 1,
    "no_auth": 1,
    "importance": 1,
}

_ACTION_COMPACT_FIELDS = {
    "_id": 0,
    "slug": 1,
    "toolkit_slug": 1,
    "name": 1,
    "description": 1,
    "composio_tags": 1,
    "required_scopes": 1,
    "enrichment": 1,
}


_client = None


def _db():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_CONNECTION_STRING)
    return _client[INTEGRATIONS_DB]


def _parse_bool(v, default=False):
    if v is None:
        return default
    return str(v).lower() in ("1", "true", "yes")


def list_toolkits(request):
    """GET /api/v1/tools/toolkits"""
    category = (request.GET.get("category") or "").strip()
    q = (request.GET.get("q") or "").strip()

    query = {}
    if category:
        query["categories"] = category

    try:
        coll = _db()[TOOLKITS_COLL]
        if q:
            query["$text"] = {"$search": q}
            projection = dict(_TOOLKIT_FIELDS)
            projection["_text_score"] = {"$meta": "textScore"}
            candidates = list(
                coll.find(query, projection).sort([("_text_score", {"$meta": "textScore"})])
            )
            if candidates:
                max_ts = max((c.get("_text_score") or 0.0) for c in candidates) or 1.0
                for c in candidates:
                    ts = (c.get("_text_score") or 0.0) / max_ts
                    imp = c.get("importance") or 0.0
                    c["_rank_score"] = round(0.5 * ts + 0.5 * imp, 4)
                candidates.sort(key=lambda x: x["_rank_score"], reverse=True)
            toolkits = candidates
            for t in toolkits:
                t.pop("_text_score", None)
        else:
            toolkits = list(
                coll.find(query, _TOOLKIT_FIELDS).sort(
                    [("importance", DESCENDING), ("name", ASCENDING)]
                )
            )
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(f"Failed to fetch toolkits: {str(e)[:200]}")

    return ResponseParser.getParsedSuccessMessage(
        data={"toolkits": toolkits, "count": len(toolkits)},
        status="200",
        message="OK",
    )


def list_actions(request, slug):
    """GET /api/v1/tools/toolkits/<slug>/actions"""
    try:
        limit = int(request.GET.get("limit", 30))
    except (TypeError, ValueError):
        limit = 30
    limit = max(1, min(limit, 500))

    q = (request.GET.get("q") or "").strip()
    include_blocked = _parse_bool(request.GET.get("include_blocked"), default=False)

    # Verify toolkit exists.
    toolkits = _db()[TOOLKITS_COLL]
    if not toolkits.find_one({"slug": slug}, {"_id": 1}):
        return ResponseParser.getParsedErrorMessage(f"Toolkit not found: {slug}", error_code="404")

    query = {"toolkit_slug": slug}
    if not include_blocked:
        query["enrichment.danger_level"] = {"$ne": "blocked"}

    actions_coll = _db()[ACTIONS_COLL]
    try:
        if q:
            # Text match across name/description/use_cases; blend with importance.
            query["$text"] = {"$search": q}
            projection = dict(_ACTION_COMPACT_FIELDS)
            projection["_text_score"] = {"$meta": "textScore"}
            cursor = actions_coll.find(query, projection).sort(
                [("_text_score", {"$meta": "textScore"})]
            ).limit(limit * 3)
            candidates = list(cursor)
            # Blend: 0.5 * normalized_text_score + 0.5 * importance
            if candidates:
                max_ts = max((c.get("_text_score") or 0.0) for c in candidates) or 1.0
                for c in candidates:
                    ts = (c.get("_text_score") or 0.0) / max_ts
                    imp = ((c.get("enrichment") or {}).get("importance") or 0.0)
                    c["_rank_score"] = round(0.5 * ts + 0.5 * imp, 4)
                candidates.sort(key=lambda x: x["_rank_score"], reverse=True)
            actions = candidates[:limit]
            for a in actions:
                a.pop("_text_score", None)
        else:
            cursor = actions_coll.find(query, _ACTION_COMPACT_FIELDS).sort(
                [("enrichment.importance", DESCENDING), ("slug", ASCENDING)]
            ).limit(limit)
            actions = list(cursor)
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(f"Failed to fetch actions: {str(e)[:200]}")

    return ResponseParser.getParsedSuccessMessage(
        data={"toolkit_slug": slug, "actions": actions, "count": len(actions)},
        status="200",
        message="OK",
    )


def list_model_recommendations(request):
    """GET /api/v1/models/recommendations — full purpose → {default, pro} catalog."""
    try:
        coll = _db()[MODEL_RECOMMENDATIONS_COLL]
        rows = list(
            coll.find({}, _MODEL_RECOMMENDATION_FIELDS).sort("purpose", ASCENDING)
        )
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(
            f"Failed to fetch model recommendations: {str(e)[:200]}"
        )

    return ResponseParser.getParsedSuccessMessage(
        data={"recommendations": rows, "count": len(rows)},
        status="200",
        message="OK",
    )


_composio_client = None


def _composio():
    global _composio_client
    if _composio_client is None:
        from composio import Composio
        _composio_client = Composio()
    return _composio_client


def initiate_connection(request):
    """POST /api/v1/tools/connect — create a Composio OAuth URL for (user, project, toolkit).

    Returns a redirect URL the frontend sends the user to. On completion,
    Composio stores the connection under user_id={uid}_{project_key}.
    """
    is_valid, err_msg, user_object, project_object = validator.validate_user_and_project(
        request, access_level_gte=1
    )
    if not is_valid:
        return ResponseParser.getParsedErrorMessage(err_msg)

    toolkit_slug = (get_param(request, "toolkit_slug", "") or "").strip().lower()
    if not toolkit_slug:
        return ResponseParser.getParsedErrorMessage("Missing toolkit_slug")

    # Some toolkits (e.g. Confluence/Jira) require extra init fields like `subdomain`.
    # Accept `extra_params` as a JSON object (string or dict) and forward to Composio.
    raw_extra = get_param(request, "extra_params", "")
    if isinstance(raw_extra, dict):
        extra_params = raw_extra
    elif raw_extra:
        try:
            extra_params = json.loads(raw_extra)
            if not isinstance(extra_params, dict):
                return ResponseParser.getParsedErrorMessage("extra_params must be a JSON object")
        except Exception as e:
            return ResponseParser.getParsedErrorMessage(f"Invalid JSON in extra_params: {str(e)[:120]}")
    else:
        extra_params = {}

    toolkit = _db()[TOOLKITS_COLL].find_one(
        {"slug": toolkit_slug},
        {"_id": 0, "slug": 1, "name": 1, "oauth_config_id": 1, "apikey_config_id": 1, "other_auth_id": 1},
    )
    if not toolkit:
        return ResponseParser.getParsedErrorMessage(
            f"Toolkit not found or not connectable: {toolkit_slug}", error_code="404"
        )

    auth_config_id = (
        toolkit.get("oauth_config_id")
        or toolkit.get("apikey_config_id")
        or toolkit.get("other_auth_id")
    )
    if not auth_config_id:
        return ResponseParser.getParsedErrorMessage(
            f"Toolkit has no auth config: {toolkit_slug}", error_code="400"
        )

    user_id = f"{user_object.uid}_{project_object.project_key}"

    try:
        initiate_kwargs = {
            "user_id": user_id,
            "auth_config_id": auth_config_id,
        }
        if extra_params:
            initiate_kwargs["config"] = extra_params
        req = _composio().connected_accounts.initiate(**initiate_kwargs)
        redirect_url = getattr(req, "redirect_url", None) or getattr(req, "redirectUrl", None)
        connection_id = getattr(req, "id", None) or getattr(req, "connection_id", None)
        status_val = getattr(req, "status", None)
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(
            f"Failed to initiate connection: {str(e)[:2000]}", error_code="E_EXEC"
        )

    return ResponseParser.getParsedSuccessMessage(
        data={
            "toolkit_slug": toolkit_slug,
            "user_id": user_id,
            "auth_config_id": auth_config_id,
            "redirect_url": redirect_url,
            "connection_id": connection_id,
            "status": status_val,
        },
        status="200",
        message="OK",
    )


def list_connections(request):
    """GET or POST /api/v1/tools/connections — list this project's Composio connections.

    Accepts uid and project_key via query string or POST body.
    """
    is_valid, err_msg, user_object, project_object = validator.validate_user_and_project(
        request, access_level_gte=1
    )
    if not is_valid:
        return ResponseParser.getParsedErrorMessage(err_msg)

    user_id = f"{user_object.uid}_{project_object.project_key}"
    try:
        res = _composio().connected_accounts.list(user_ids=[user_id])
        items = res.items if hasattr(res, "items") else list(res)
        conns = []
        for i in items:
            d = i.model_dump() if hasattr(i, "model_dump") else dict(i)
            conns.append({
                "connection_id": d.get("id"),
                "toolkit_slug": (d.get("toolkit") or {}).get("slug"),
                "status": d.get("status"),
                "created_at": d.get("created_at"),
                "auth_config_id": (d.get("auth_config") or {}).get("id"),
            })
    except Exception as e:
        return ResponseParser.getParsedErrorMessage(
            f"Failed to list connections: {str(e)[:200]}", error_code="E_EXEC"
        )

    return ResponseParser.getParsedSuccessMessage(
        data={"user_id": user_id, "connections": conns, "count": len(conns)},
        status="200",
        message="OK",
    )


def execute_tool(request):
    """POST /api/v1/tools/execute — run a Composio action, gating writes in test mode."""
    # 1. Auth
    is_valid, err_msg, user_object, project_object = validator.validate_user_and_project(
        request, access_level_gte=1
    )
    if not is_valid:
        return ResponseParser.getParsedErrorMessage(err_msg)

    uid = user_object.uid
    project_key = project_object.project_key

    # 2. Params
    action_slug = (get_param(request, "action_slug", "") or "").strip()
    if not action_slug:
        return ResponseParser.getParsedErrorMessage("Missing action_slug")

    is_test_run = str(get_param(request, "is_test_run", "false")).lower() in ("1", "true", "yes")

    raw_args = get_param(request, "arguments", "")
    if isinstance(raw_args, (dict, list)):
        arguments = raw_args
    elif raw_args:
        try:
            arguments = json.loads(raw_args)
        except Exception as e:
            return ResponseParser.getParsedErrorMessage(f"Invalid JSON in arguments: {str(e)[:120]}")
    else:
        arguments = {}

    # 3. Look up action metadata
    action_doc = _db()[ACTIONS_COLL].find_one(
        {"slug": action_slug},
        {"_id": 0, "slug": 1, "toolkit_slug": 1, "enrichment": 1, "version": 1},
    )
    if not action_doc:
        return ResponseParser.getParsedErrorMessage(
            f"Action not found: {action_slug}", error_code="404"
        )

    enrichment = action_doc.get("enrichment") or {}
    danger_level = enrichment.get("danger_level")
    read_or_write = enrichment.get("read_or_write")
    toolkit_slug = action_doc.get("toolkit_slug")

    # 4. Safety gate
    if danger_level == "blocked":
        return ResponseParser.getParsedErrorMessage(
            f"Action blocked by safety policy: {action_slug}", error_code="403"
        )

    # 5. Test-run gating for writes
    user_id = f"{uid}_{project_key}"
    is_write = (read_or_write == "write")
    if is_test_run and is_write:
        utils.logger.info(
            f"[tool_execute] PREVIEW uid={uid} project={project_key} slug={action_slug} "
            f"toolkit={toolkit_slug}"
        )
        return ResponseParser.getParsedSuccessMessage(
            data={
                "test_preview": True,
                "action_slug": action_slug,
                "toolkit_slug": toolkit_slug,
                "arguments": arguments,
                "note": "Write skipped because is_test_run=true. Would have executed in production.",
            },
            status="200",
            message="OK (test preview)",
        )

    # 6. Real execution via Composio
    try:
        client = _composio()
        exec_kwargs = {"arguments": arguments, "user_id": user_id}
        version = action_doc.get("version")
        if version:
            exec_kwargs["version"] = version
        result = client.tools.execute(action_slug, **exec_kwargs)
        payload = result.model_dump() if hasattr(result, "model_dump") else (
            dict(result) if not isinstance(result, dict) else result
        )
    except Exception as e:
        utils.logger.error(
            f"[tool_execute] ERROR uid={uid} project={project_key} slug={action_slug} "
            f"err={type(e).__name__}: {str(e)}"
        )
        return ResponseParser.getParsedErrorMessage(
            f"Tool execution failed: {str(e)[:200]}",
            error_code="E_EXEC",
        )

    utils.logger.info(
        f"[tool_execute] OK uid={uid} project={project_key} slug={action_slug} "
        f"toolkit={toolkit_slug} test={is_test_run}"
    )
    return ResponseParser.getParsedSuccessMessage(
        data={
            "test_preview": False,
            "action_slug": action_slug,
            "toolkit_slug": toolkit_slug,
            "result": payload,
        },
        status="200",
        message="OK",
    )


def get_action_schema(request, slug, action_slug):
    """GET /api/v1/tools/toolkits/<slug>/actions/<action_slug>"""
    actions_coll = _db()[ACTIONS_COLL]
    doc = actions_coll.find_one(
        {"slug": action_slug, "toolkit_slug": slug},
        {"_id": 0, "synced_at": 0},
    )
    if not doc:
        return ResponseParser.getParsedErrorMessage(
            f"Action not found: {slug}/{action_slug}", error_code="404"
        )
    return ResponseParser.getParsedSuccessMessage(
        data={"action": doc}, status="200", message="OK"
    )
