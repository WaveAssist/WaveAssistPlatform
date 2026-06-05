"""WaveAssist MCP server — thin connectivity for building & deploying agents.

These tools are deliberately dumb pipes over the WaveAssist HTTP API. ALL of the
reasoning (gathering requirements, designing nodes, writing code) lives in the
WaveAgent SKILL that the host coding agent follows — so behaviour is identical in
Claude Code and Cursor.

Typical flow the skill drives:
    waveassist_login  ->  waveassist_deploy_agent (unarmed)  ->  waveassist_set_key
    ->  waveassist_test_agent (dry run)  ->  waveassist_arm_schedule (on green)
"""
from __future__ import annotations

import os
import time
import uuid
import webbrowser

from mcp.server.fastmcp import FastMCP

from . import config, registry
from .client import WaveAssistClient, WaveAssistError

mcp = FastMCP("waveassist")


def _client() -> WaveAssistClient:
    return WaveAssistClient()


def _uid_from_request() -> str | None:
    """HOSTED (HTTP) transport: read the UID from the request's
    `Authorization: Bearer <uid>` header (or `X-WaveAssist-UID`). Returns None under
    stdio / when no request is active, so every hosted request is authenticated
    independently — multi-tenant safe."""
    try:
        req = mcp.get_context().request_context.request
    except Exception:
        return None
    if req is None:
        return None
    try:
        auth = (req.headers.get("authorization", "") or "")
        if auth.lower().startswith("bearer "):
            tok = auth[7:].strip()
            if tok:
                return tok
        return (req.headers.get("x-waveassist-uid", "") or "").strip() or None
    except Exception:
        return None


def _is_http_request() -> bool:
    try:
        return mcp.get_context().request_context.request is not None
    except Exception:
        return False


def _resolve_uid() -> str | None:
    """UID from the HTTP header (hosted) first, else local env / config file (stdio)."""
    return _uid_from_request() or config.load_uid()


def _require_uid() -> str:
    uid = _resolve_uid()
    if not uid:
        raise WaveAssistError(
            "Not authenticated. Hosted: set `Authorization: Bearer <your-WaveAssist-UID>` "
            "in your MCP client config. Local: call waveassist_login with your uid, or set "
            "the WAVEASSIST_UID environment variable."
        )
    return uid


def _err(e: Exception) -> dict:
    if isinstance(e, WaveAssistError):
        return {"ok": False, "error": e.message, "status": e.status}
    return {"ok": False, "error": str(e)}


def _mask(secret: str) -> str:
    """Mask a credential for inclusion in tool output (it's already persisted)."""
    s = (secret or "").strip()
    return f"{s[:8]}…{s[-4:]}" if len(s) > 12 else "***"


# --------------------------------------------------------------------------- #
# auth
# --------------------------------------------------------------------------- #
@mcp.tool()
def waveassist_login(uid: str = "") -> dict:
    """Authenticate to WaveAssist.

    If you already know your WaveAssist UID, pass it as `uid` and it is saved
    locally (~/.waveassist/config.json) for all subsequent tools. Otherwise this
    starts the browser CLI-login handshake and waits up to ~3 minutes for you to
    log in, then saves the resulting UID.
    """
    # Hosted (HTTP) server: auth is the Authorization header, not a saved file.
    if _is_http_request():
        cur = _uid_from_request()
        if cur:
            return {"ok": True, "uid": _mask(cur), "auth": "header",
                    "note": "Authenticated via the Authorization header — no login call needed."}
        return {"ok": False, "auth": "header",
                "message": "Hosted server: set `Authorization: Bearer <your-WaveAssist-UID>` "
                           "in your MCP client config; no login call is used."}

    if uid.strip():
        path = config.save_uid(uid.strip())
        return {"ok": True, "uid": _mask(uid.strip()), "saved_to": str(path),
                "note": "UID saved. You can now build and deploy agents."}

    session_id = str(uuid.uuid4())
    login_url = f"{config.app_base()}/login?session_id={session_id}"
    try:
        webbrowser.open(login_url)
    except Exception:
        pass
    client = _client()
    try:
        deadline = time.time() + 180
        while time.time() < deadline:
            got = client.cli_login_status(session_id)
            if got:
                path = config.save_uid(got)
                return {"ok": True, "uid": _mask(got), "saved_to": str(path)}
            time.sleep(2)
    except Exception as e:  # noqa: BLE001
        return _err(e)
    finally:
        client.close()
    return {"ok": False, "status": "pending", "login_url": login_url,
            "message": "Login not completed. Open the URL, sign in, then run waveassist_login again."}


@mcp.tool()
def waveassist_status() -> dict:
    """Show login status (configured UID + API base) and the agents this machine
    has built with WaveAgent (from the local registry)."""
    uid = _resolve_uid()
    return {
        "ok": True,
        "logged_in": bool(uid),
        "uid_present": bool(uid),
        "uid": _mask(uid) if uid else None,
        "transport": "http" if _is_http_request() else "stdio",
        "api_base": config.api_base(),
        "app_base": config.app_base(),
        "agents": registry.all_agents(uid),
    }


# --------------------------------------------------------------------------- #
# build + deploy
# --------------------------------------------------------------------------- #
@mcp.tool()
def waveassist_deploy_agent(
    name: str,
    config_yaml: str,
    code_files: dict[str, str],
    description: str = "",
    readme_md: str = "",
    timezone: str = "UTC",
    slug: str = "",
) -> dict:
    """Create or update a WaveAssist agent and install its nodes — UNARMED (the
    schedule does NOT fire yet).

    Idempotent: the first deploy of a given agent `slug` CREATES it; later deploys
    UPDATE it in place (so editing an agent is just calling this again).

    Args:
        name: human assistant name (also used to derive the project key).
        config_yaml: the full config.yaml as a YAML string.
        code_files: {"node_key.py": "<python source>"} — one flat script per node.
        slug: optional stable id for idempotency; defaults to a slug of `name`.

    Next steps after this: waveassist_set_key (integration keys) -> waveassist_test_agent
    -> waveassist_arm_schedule. Returns {project_key, repo_url, env_default, env_test,
    dashboard_url, mode}.
    """
    try:
        uid = _require_uid()
        slug = slug.strip() or registry.slugify(name)
        client = _client()
        try:
            existing = registry.get(uid, slug)
            if existing and existing.get("project_key") and existing.get("repo_url"):
                # UPDATE: push new commit, then upgrade nodes in place.
                client.materialize_assistant(
                    uid, name, config_yaml, code_files, readme_md or None,
                    existing_repo_url=existing["repo_url"],
                )
                upg = client.upgrade_assistant(uid, existing["project_key"], timezone=timezone)
                project_key = existing["project_key"]
                repo_url = existing["repo_url"]
                mode = "updated"
                extra = {"upgrade": upg}
            else:
                # CREATE: materialize a fresh repo, then install nodes.
                mat = client.materialize_assistant(
                    uid, name, config_yaml, code_files, readme_md or None
                )
                repo_url = mat.get("repo_url")
                proj = client.deploy_template(
                    uid, repo_url, timezone=timezone, should_install_requirements=True
                )
                project_key = proj.get("project_key")
                mode = "created"
                extra = {}
        finally:
            client.close()

        if not project_key or not repo_url:
            return {"ok": False,
                    "error": "Deploy did not return a project_key/repo_url; nothing recorded.",
                    "mode": mode, "project_key": project_key, "repo_url": repo_url}

        entry = {
            "project_key": project_key,
            "repo_url": repo_url,
            "env_default": f"{project_key}_default",
            "env_test": f"{project_key}_test",
            "name": name,
        }
        registry.put(uid, slug, entry)
        return {
            "ok": True, "mode": mode, "slug": slug, **entry,
            "dashboard_url": config.dashboard_project_url(project_key), **extra,
        }
    except Exception as e:  # noqa: BLE001
        return _err(e)


@mcp.tool()
def waveassist_set_key(
    project_key: str, data_key: str, value: str, data_type: str = "string"
) -> dict:
    """Store an integration key/secret in the agent's key-value store, in BOTH the
    default and test environments (so test runs and live runs both see it).

    Example: data_key="clickup_token". Generated nodes read it via
    waveassist.fetch_data("clickup_token").

    Note: for the private beta the value travels through the host's tool channel;
    avoid pasting highly-sensitive long-lived secrets until out-of-band entry lands.
    """
    try:
        uid = _require_uid()
        client = _client()
        written = []
        try:
            for env in (f"{project_key}_default", f"{project_key}_test"):
                client.set_data_for_key(uid, project_key, env, data_key, value, data_type)
                written.append(env)
        finally:
            client.close()
        return {"ok": True, "data_key": data_key, "environments": written}
    except Exception as e:  # noqa: BLE001
        return _err(e)


# --------------------------------------------------------------------------- #
# test
# --------------------------------------------------------------------------- #
@mcp.tool()
def waveassist_test_agent(
    project_key: str, start_node_key: str = "", timeout_seconds: int = 120
) -> dict:
    """Dry-run the agent on WaveAssist infra against its TEST environment.

    Sets the `_is_test_run` flag first, so any node guarded with
    waveassist.is_test_run() skips real side-effects (emails / external writes).
    Polls until the run finishes (or timeout). Returns overall status, per-node
    status + tracebacks, and any display_output preview.

    ALWAYS run this and confirm it is green before waveassist_arm_schedule.
    """
    try:
        uid = _require_uid()
        env_test = f"{project_key}_test"
        client = _client()
        terminal = {"SUCCESS", "FAILED"}
        our = None
        node_runs: list = []
        overall = None
        dag_key = None
        try:
            # Baseline existing runs so we can identify the one we trigger. The
            # celery task id from run_dag is NOT the DagRuns.run_id, so we correlate
            # by finding the newest dag run that wasn't there before.
            before = {r.get("run_id") for r in client.fetch_dag_runs(uid, project_key, env_test)}
            client.set_data_for_key(uid, project_key, env_test, "_is_test_run", "true", "string")
            run = client.run_dag(uid, project_key, env_test, start_node_key or None)
            dag_key = (run.get("dag") or {}).get("key")

            deadline = time.time() + max(15, int(timeout_seconds))
            while time.time() < deadline:
                time.sleep(3)
                dag_runs = client.fetch_dag_runs(uid, project_key, env_test)
                fresh = [r for r in dag_runs if r.get("run_id") not in before]
                if not fresh:
                    continue
                our = fresh[0]  # newest first (ordered by -created_at)
                overall = our.get("status")
                try:
                    node_runs = client.fetch_node_runs(uid, project_key, env_test, our.get("run_id"))
                except WaveAssistError:
                    node_runs = []
                if overall in terminal:
                    break

            dag_run_id = our.get("run_id") if our else None
            preview = None
            if dag_run_id:
                preview = client.fetch_data_for_key(
                    uid, project_key, env_test, "display_output", run_based=True, run_id=dag_run_id
                ) or client.fetch_data_for_key(uid, project_key, env_test, "display_output")
        finally:
            client.close()

        nodes = [
            {
                "node_key": n.get("node_key"),
                "node_name": n.get("node_name"),
                "status": n.get("status"),
                "error": n.get("traceback") or n.get("error") or n.get("logs"),
            }
            for n in node_runs
        ]
        overall = overall or "UNKNOWN"
        return {
            "ok": True,
            "overall": overall,
            "is_green": overall == "SUCCESS",
            "run_id": dag_run_id,
            "dag_key": dag_key,
            "nodes": nodes,
            "display_output_preview": preview,
        }
    except Exception as e:  # noqa: BLE001
        return _err(e)


@mcp.tool()
def waveassist_run_logs(
    project_key: str, environment: str = "test", dag_run_id: str = ""
) -> dict:
    """Fetch recent run statuses (and node-level tracebacks for a specific
    dag_run_id) to debug a failing agent. environment: "test" or "default"."""
    try:
        uid = _require_uid()
        env = f"{project_key}_{'default' if environment == 'default' else 'test'}"
        client = _client()
        try:
            dag_runs = client.fetch_dag_runs(uid, project_key, env)
            node_runs = (
                client.fetch_node_runs(uid, project_key, env, dag_run_id)
                if dag_run_id else []
            )
        finally:
            client.close()
        return {"ok": True, "environment": env, "dag_runs": dag_runs[:10], "node_runs": node_runs}
    except Exception as e:  # noqa: BLE001
        return _err(e)


# --------------------------------------------------------------------------- #
# arm / disarm schedule
# --------------------------------------------------------------------------- #
@mcp.tool()
def waveassist_arm_schedule(project_key: str, version: str = "") -> dict:
    """Arm the recurring schedule for a TESTED agent — it will now run on its
    cron/interval. Only call after waveassist_test_agent is green. Clears the test
    flag in the default environment. Returns {deployment_key, version, status}."""
    try:
        uid = _require_uid()
        env_default = f"{project_key}_default"
        version = version.strip() or f"wa-{int(time.time())}"
        client = _client()
        try:
            client.set_data_for_key(uid, project_key, env_default, "_is_test_run", "false", "string")
            dep = client.deploy_project(uid, project_key, env_default, version)
        finally:
            client.close()
        deployment_key = (dep.get("deployment") or {}).get("key")
        # record deployment_key against any matching slug — only if we actually got one
        if deployment_key:
            for slug, entry in registry.all_agents(uid).items():
                if entry.get("project_key") == project_key:
                    registry.put(uid, slug, {"deployment_key": deployment_key, "version": version})
                    break
        result = {"ok": True, "status": "armed", "deployment_key": deployment_key, "version": version}
        if not deployment_key:
            result["warning"] = ("Backend returned no deployment.key; "
                                 "disarm will require an explicit deployment_key.")
        return result
    except Exception as e:  # noqa: BLE001
        return _err(e)


@mcp.tool()
def waveassist_disarm_schedule(project_key: str, deployment_key: str = "") -> dict:
    """Stop/pause a live agent's schedule. If deployment_key is omitted, uses the
    one recorded when the agent was armed."""
    try:
        uid = _require_uid()
        if not deployment_key:
            for entry in registry.all_agents(uid).values():
                if entry.get("project_key") == project_key and entry.get("deployment_key"):
                    deployment_key = entry["deployment_key"]
                    break
        if not deployment_key:
            return {"ok": False, "error": "No deployment_key recorded for this project; pass one explicitly."}
        client = _client()
        try:
            dep = client.stop_deployment(uid, deployment_key, project_key, f"{project_key}_default")
        finally:
            client.close()
        return {"ok": True, "status": "disarmed", "deployment": dep}
    except Exception as e:  # noqa: BLE001
        return _err(e)


def main() -> None:
    """Local (stdio) entry point — used by Claude Code/Cursor when running the server
    on the user's machine. UID comes from WAVEASSIST_UID env or ~/.waveassist/config.json."""
    mcp.run()


def serve_http() -> None:
    """Hosted (streamable-HTTP) entry point — WaveAssist runs this behind
    https://mcp.waveassist.io/mcp. Auth is per-request via the
    `Authorization: Bearer <WaveAssist-UID>` header (multi-tenant). Configure host/port
    with WAVEASSIST_MCP_HOST / PORT (or WAVEASSIST_MCP_PORT)."""
    from mcp.server.transport_security import TransportSecuritySettings

    mcp.settings.host = os.environ.get("WAVEASSIST_MCP_HOST", "0.0.0.0")
    mcp.settings.port = int(os.environ.get("PORT") or os.environ.get("WAVEASSIST_MCP_PORT", "8000"))
    # The SDK's DNS-rebinding protection only accepts localhost Host headers (it
    # exists to protect LOCAL servers from malicious browser pages). A hosted,
    # public, header-authenticated server is exactly the case it must be off for —
    # otherwise every request via run.app / mcp.waveassist.io gets HTTP 421.
    mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
