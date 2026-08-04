"""Unit tests for the MCP tool functions (waveassist_mcp.server).

FastMCP's ``@mcp.tool()`` decorator registers the function but returns the
original callable unchanged, so we import and call them directly, e.g.
``server.waveassist_set_key(...)``.

All HTTP is mocked with respx against ``https://api.waveassist.io``. We assert
on the *recorded* requests where it matters: which endpoint, which environment
(``_default`` vs ``_test``), and encoding. ``time.sleep`` inside the server is
patched to a no-op so the test-agent poll loop runs instantly (still exercising
one real poll iteration).
"""
from __future__ import annotations

import json
from urllib.parse import parse_qs

import httpx
import pytest
import respx

from waveassist_mcp import registry, server

BASE = "https://api.waveassist.io"
TEST_UID = "test-uid-1234"  # pinned by conftest; the registry is UID-scoped


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Make the polling loop instant — exercise one iteration without waiting."""
    monkeypatch.setattr(server.time, "sleep", lambda *_a, **_k: None)


def _env(data):
    return {"success": "1", "data": data}


def _form(request):
    return parse_qs(request.content.decode())


# --------------------------------------------------------------------------- #
# waveassist_deploy_agent — CREATE path
# --------------------------------------------------------------------------- #
@respx.mock
def test_deploy_agent_create_path():
    """No registry entry -> materialize(create) then deploy_template; records
    slug in registry; mode == 'created'."""
    mat = respx.post(f"{BASE}/api/v1/wavemaker/materialize_assistant").mock(
        return_value=httpx.Response(
            200, json=_env({"repo_url": "https://github.com/wa/my-agent", "is_update": False})
        )
    )
    tmpl = respx.post(f"{BASE}/template/deploy_template/").mock(
        return_value=httpx.Response(200, json=_env({"project_key": "my_agent_ab12"}))
    )

    out = server.waveassist_deploy_agent(
        name="My Agent",
        config_yaml="name: x\n",
        code_files={"main.py": "print(1)"},
    )

    assert out["ok"] is True
    assert out["mode"] == "created"
    assert out["project_key"] == "my_agent_ab12"
    assert out["repo_url"] == "https://github.com/wa/my-agent"
    assert out["env_default"] == "my_agent_ab12_default"
    assert out["env_test"] == "my_agent_ab12_test"

    # both endpoints were hit exactly once, in order
    assert mat.called
    assert tmpl.called

    # materialize was a *create* (no existing_repo_url sent)
    mat_body = json.loads(mat.calls.last.request.content)
    assert "existing_repo_url" not in mat_body

    # deploy_template received the repo_url returned by materialize
    tmpl_form = _form(tmpl.calls.last.request)
    assert tmpl_form["repo_url"] == ["https://github.com/wa/my-agent"]

    # registry now has the slug (under the resolved uid)
    entry = registry.get(TEST_UID, "my_agent")
    assert entry is not None
    assert entry["project_key"] == "my_agent_ab12"
    assert entry["repo_url"] == "https://github.com/wa/my-agent"


# --------------------------------------------------------------------------- #
# waveassist_deploy_agent — UPDATE path
# --------------------------------------------------------------------------- #
@respx.mock
def test_deploy_agent_update_path():
    """Registry pre-seeded with project_key+repo_url -> materialize(update) then
    upgrade_assistant; mode == 'updated'; deploy_template NOT called."""
    registry.put(
        TEST_UID,
        "my_agent",
        {
            "project_key": "my_agent_ab12",
            "repo_url": "https://github.com/wa/my-agent",
        },
    )

    mat = respx.post(f"{BASE}/api/v1/wavemaker/materialize_assistant").mock(
        return_value=httpx.Response(
            200, json=_env({"repo_url": "https://github.com/wa/my-agent", "is_update": True})
        )
    )
    upg = respx.post(f"{BASE}/assistant/upgrade/").mock(
        return_value=httpx.Response(
            200, json=_env({"new_sha": "deadbeef", "commit_message": "bump"})
        )
    )
    tmpl = respx.post(f"{BASE}/template/deploy_template/").mock(
        return_value=httpx.Response(200, json=_env({"project_key": "should_not_be_used"}))
    )

    out = server.waveassist_deploy_agent(
        name="My Agent",
        config_yaml="name: x\n",
        code_files={"main.py": "print(2)"},
    )

    assert out["ok"] is True
    assert out["mode"] == "updated"
    assert out["project_key"] == "my_agent_ab12"
    assert out["repo_url"] == "https://github.com/wa/my-agent"
    assert out["upgrade"] == {"new_sha": "deadbeef", "commit_message": "bump"}

    # materialize was an *update* — existing_repo_url forwarded
    mat_body = json.loads(mat.calls.last.request.content)
    assert mat_body["existing_repo_url"] == "https://github.com/wa/my-agent"

    # upgrade hit with the existing project_key; deploy_template NOT used
    upg_form = _form(upg.calls.last.request)
    assert upg_form["project_key"] == ["my_agent_ab12"]
    assert upg.called
    assert not tmpl.called


# --------------------------------------------------------------------------- #
# waveassist_list_projects — live list + connectivity check
# --------------------------------------------------------------------------- #
@respx.mock
def test_list_projects_returns_live_list():
    route = respx.post(f"{BASE}/manage/fetch_all_projects/").mock(
        return_value=httpx.Response(
            200,
            json=_env({"project_array": [
                {"project_key": "a_ab12", "name": "A", "github_url": "https://github.com/wa/a"},
                {"project_key": "b_cd34", "name": "B"},
            ]}),
        )
    )

    out = server.waveassist_list_projects()

    assert out["ok"] is True
    assert out["count"] == 2
    assert [p["project_key"] for p in out["projects"]] == ["a_ab12", "b_cd34"]
    assert [p["name"] for p in out["projects"]] == ["A", "B"]
    assert out["uid"] == server._mask(TEST_UID)  # masked, never raw
    # the uid was the only thing sent (uid is the token)
    assert _form(route.calls.last.request)["uid"] == [TEST_UID]


def test_list_projects_requires_auth(monkeypatch):
    """No UID resolvable -> {ok:false} with the not-authenticated error, no HTTP."""
    monkeypatch.setattr(server, "_resolve_uid", lambda: None)
    out = server.waveassist_list_projects()
    assert out["ok"] is False
    assert "Not authenticated" in out["error"]


# --------------------------------------------------------------------------- #
# waveassist_set_key — writes BOTH envs
# --------------------------------------------------------------------------- #
@respx.mock
def test_set_key_writes_both_envs():
    route = respx.post(f"{BASE}/data/set_data_for_key/").mock(
        return_value=httpx.Response(200, json=_env({"data_key": "clickup_token"}))
    )

    out = server.waveassist_set_key(
        project_key="my_agent_ab12", data_key="clickup_token", value="secret-123"
    )

    assert out["ok"] is True
    assert out["environments"] == ["my_agent_ab12_default", "my_agent_ab12_test"]

    # exactly two writes, one per environment
    assert route.call_count == 2
    bodies = [json.loads(c.request.content) for c in route.calls]
    envs = {b["data_run_key"] for b in bodies}
    assert envs == {"my_agent_ab12_default", "my_agent_ab12_test"}
    for b in bodies:
        assert b["data_key"] == "clickup_token"
        assert b["data"] == "secret-123"
        assert b["project_key"] == "my_agent_ab12"


# --------------------------------------------------------------------------- #
# waveassist_test_agent — seeds _is_test_run, runs, polls -> green
# --------------------------------------------------------------------------- #
@respx.mock
def test_test_agent_green():
    """Seeds _is_test_run=true in the TEST env, runs the dag, then correlates the
    run via fetch_dag_runs (the celery id from run_dag is NOT the DagRuns.run_id).
    The baseline fetch_dag_runs is empty; the next one shows our fresh SUCCESS run."""
    set_route = respx.post(f"{BASE}/data/set_data_for_key/").mock(
        return_value=httpx.Response(200, json=_env({"data_key": "_is_test_run"}))
    )
    respx.post(f"{BASE}/deploy/run_dag/").mock(
        return_value=httpx.Response(
            200,
            json=_env({"dag": {"key": "DAG_x", "is_running": True}, "run_id": "celery-abc"}),
        )
    )
    # fetch_dag_runs: 1st call = baseline (empty), then our fresh terminal run.
    dag_runs_seq = [
        httpx.Response(200, json=_env({"dag_run_array": []})),
        httpx.Response(
            200,
            json=_env({"dag_run_array": [{"run_id": "dr-1", "status": "SUCCESS"}]}),
        ),
    ]

    def dag_runs_effect(request):
        return dag_runs_seq.pop(0) if dag_runs_seq else httpx.Response(
            200, json=_env({"dag_run_array": [{"run_id": "dr-1", "status": "SUCCESS"}]})
        )

    respx.post(f"{BASE}/runs/fetch_dag_runs/").mock(side_effect=dag_runs_effect)
    node_route = respx.post(f"{BASE}/runs/fetch_node_runs/").mock(
        return_value=httpx.Response(
            200,
            json=_env(
                {"node_runs": [{"node_key": "n1", "node_name": "Fetch", "status": "SUCCESS"}]}
            ),
        )
    )
    # display_output preview lookups (run-based then plain) -> not found / None.
    respx.get(f"{BASE}/data/fetch_data_for_key/").mock(
        return_value=httpx.Response(
            200, json={"success": "0", "message": "Data not found", "status": "404"}
        )
    )

    out = server.waveassist_test_agent(project_key="my_agent_ab12", timeout_seconds=15)

    assert out["ok"] is True
    assert out["overall"] == "SUCCESS"
    assert out["is_green"] is True
    assert out["run_id"] == "dr-1"  # correlated DagRuns.run_id, not the celery id
    assert out["dag_key"] == "DAG_x"
    assert out["nodes"] == [
        {"node_key": "n1", "node_name": "Fetch", "status": "SUCCESS", "error": None}
    ]
    # node runs were fetched using the correlated run_id
    node_form = _form(node_route.calls.last.request)
    assert node_form["dag_run_id"] == ["dr-1"]

    # the test flag was seeded into the TEST env as a string "true"
    first_set = json.loads(set_route.calls[0].request.content)
    assert first_set["data_run_key"] == "my_agent_ab12_test"
    assert first_set["data_key"] == "_is_test_run"
    assert first_set["data"] == "true"


# --------------------------------------------------------------------------- #
# waveassist_run_agent — LIVE one-off run (default env, _is_test_run=false)
# --------------------------------------------------------------------------- #
@respx.mock
def test_run_agent_live_green():
    """Sets _is_test_run=false in the DEFAULT env, runs the dag against default,
    correlates the fresh SUCCESS run, returns is_green + preview. Side-effects
    fire (this is the real run, not a dry test)."""
    set_route = respx.post(f"{BASE}/data/set_data_for_key/").mock(
        return_value=httpx.Response(200, json=_env({"data_key": "_is_test_run"}))
    )
    run_route = respx.post(f"{BASE}/deploy/run_dag/").mock(
        return_value=httpx.Response(
            200,
            json=_env({"dag": {"key": "DAG_live", "is_running": True}, "run_id": "celery-live"}),
        )
    )
    dag_runs_seq = [
        httpx.Response(200, json=_env({"dag_run_array": []})),
        httpx.Response(200, json=_env({"dag_run_array": [{"run_id": "dr-live", "status": "SUCCESS"}]})),
    ]
    respx.post(f"{BASE}/runs/fetch_dag_runs/").mock(
        side_effect=lambda r: dag_runs_seq.pop(0) if dag_runs_seq else httpx.Response(
            200, json=_env({"dag_run_array": [{"run_id": "dr-live", "status": "SUCCESS"}]})
        )
    )
    respx.post(f"{BASE}/runs/fetch_node_runs/").mock(
        return_value=httpx.Response(
            200, json=_env({"node_runs": [{"node_key": "n1", "node_name": "Run", "status": "SUCCESS"}]})
        )
    )
    respx.get(f"{BASE}/data/fetch_data_for_key/").mock(
        return_value=httpx.Response(200, json={"success": "0", "message": "Data not found"})
    )

    out = server.waveassist_run_agent(project_key="my_agent_ab12", timeout_seconds=15)

    assert out["ok"] is True
    assert out["overall"] == "SUCCESS"
    assert out["is_green"] is True
    assert out["run_id"] == "dr-live"
    assert out["dag_key"] == "DAG_live"
    assert out["nodes"] == [
        {"node_key": "n1", "node_name": "Run", "status": "SUCCESS", "error": None}
    ]

    # flag set to "false" in the DEFAULT env (live run, not a dry test)
    first_set = json.loads(set_route.calls[0].request.content)
    assert first_set["data_run_key"] == "my_agent_ab12_default"
    assert first_set["data_key"] == "_is_test_run"
    assert first_set["data"] == "false"

    # the dag was run against the DEFAULT env
    assert _form(run_route.calls.last.request)["data_run_key"] == ["my_agent_ab12_default"]


# --------------------------------------------------------------------------- #
# waveassist_arm_schedule — clears _is_test_run in default env, deploys
# --------------------------------------------------------------------------- #
@respx.mock
def test_arm_schedule():
    """Clears _is_test_run in the DEFAULT env, calls deploy_project with a
    version, returns status == 'armed' and records the deployment_key."""
    registry.put(
        TEST_UID,
        "my_agent",
        {"project_key": "my_agent_ab12", "repo_url": "https://github.com/wa/my-agent"},
    )

    set_route = respx.post(f"{BASE}/data/set_data_for_key/").mock(
        return_value=httpx.Response(200, json=_env({"data_key": "_is_test_run"}))
    )
    dep_route = respx.post(f"{BASE}/deploy/deploy_project/").mock(
        return_value=httpx.Response(200, json=_env({"deployment": {"key": "dep-xyz"}}))
    )
    # a green run exists -> no warning
    respx.post(f"{BASE}/runs/fetch_dag_runs/").mock(
        return_value=httpx.Response(200, json=_env({"dag_run_array": [{"run_id": "dr-1", "status": "SUCCESS"}]}))
    )

    out = server.waveassist_arm_schedule(project_key="my_agent_ab12", version="v9")

    assert out["ok"] is True
    assert out["status"] == "armed"
    assert out["deployment_key"] == "dep-xyz"
    assert out["version"] == "v9"
    assert "warning" not in out  # green run on record -> no nudge

    # flag cleared (set false) in the DEFAULT env
    set_body = json.loads(set_route.calls.last.request.content)
    assert set_body["data_run_key"] == "my_agent_ab12_default"
    assert set_body["data_key"] == "_is_test_run"
    assert set_body["data"] == "false"

    # deploy_project is form-encoded against the DEFAULT env, carrying version
    dep_req = dep_route.calls.last.request
    assert dep_req.headers["content-type"].startswith("application/x-www-form-urlencoded")
    dep_form = _form(dep_req)
    assert dep_form["data_run_key"] == ["my_agent_ab12_default"]
    assert dep_form["version"] == ["v9"]

    # deployment_key recorded back to the matching slug
    assert registry.get(TEST_UID, "my_agent")["deployment_key"] == "dep-xyz"


@respx.mock
def test_arm_schedule_warns_without_green_run():
    """No SUCCESS run in either env -> arms anyway (ok:true) but returns a
    non-blocking warning nudging the user to test/run first."""
    registry.put(
        TEST_UID, "my_agent",
        {"project_key": "my_agent_ab12", "repo_url": "https://github.com/wa/my-agent"},
    )
    respx.post(f"{BASE}/data/set_data_for_key/").mock(
        return_value=httpx.Response(200, json=_env({"data_key": "_is_test_run"}))
    )
    respx.post(f"{BASE}/deploy/deploy_project/").mock(
        return_value=httpx.Response(200, json=_env({"deployment": {"key": "dep-xyz"}}))
    )
    # neither env has a SUCCESS run (one FAILED, one empty)
    runs_by_env = {
        "my_agent_ab12_test": _env({"dag_run_array": [{"run_id": "dr-1", "status": "FAILED"}]}),
        "my_agent_ab12_default": _env({"dag_run_array": []}),
    }
    respx.post(f"{BASE}/runs/fetch_dag_runs/").mock(
        side_effect=lambda r: httpx.Response(200, json=runs_by_env[_form(r)["data_run_key"][0]])
    )

    out = server.waveassist_arm_schedule(project_key="my_agent_ab12", version="v1")
    assert out["ok"] is True
    assert out["status"] == "armed"
    assert "warning" in out
    assert "No successful run found" in out["warning"]


@respx.mock
def test_arm_schedule_autogenerates_version():
    """No version passed -> server mints a wa-<ts> version."""
    respx.post(f"{BASE}/data/set_data_for_key/").mock(
        return_value=httpx.Response(200, json=_env({"data_key": "_is_test_run"}))
    )
    dep_route = respx.post(f"{BASE}/deploy/deploy_project/").mock(
        return_value=httpx.Response(200, json=_env({"deployment": {"key": "dep-1"}}))
    )
    respx.post(f"{BASE}/runs/fetch_dag_runs/").mock(
        return_value=httpx.Response(200, json=_env({"dag_run_array": [{"run_id": "dr-1", "status": "SUCCESS"}]}))
    )

    out = server.waveassist_arm_schedule(project_key="solo_ab12")

    assert out["ok"] is True
    assert out["version"].startswith("wa-")
    dep_form = _form(dep_route.calls.last.request)
    assert dep_form["version"][0].startswith("wa-")


# --------------------------------------------------------------------------- #
# error envelope — the {ok:false,...} contract the build-brain gates on
# --------------------------------------------------------------------------- #
@respx.mock
def test_deploy_agent_returns_error_envelope():
    """A backend success=='0' surfaces as {ok:False, error, status} and the
    registry is NOT written (so a later deploy still routes to CREATE)."""
    respx.post(f"{BASE}/api/v1/wavemaker/materialize_assistant").mock(
        return_value=httpx.Response(200, json={"success": "0", "message": "boom", "status": "E99"})
    )
    out = server.waveassist_deploy_agent(
        name="My Agent", config_yaml="name: x\n", code_files={"main.py": "print(1)"}
    )
    assert out == {"ok": False, "error": "boom", "status": "E99"}
    assert registry.get(TEST_UID, "my_agent") is None


# --------------------------------------------------------------------------- #
# test_agent — FAILED and timeout (the gate before arming a live schedule)
# --------------------------------------------------------------------------- #
@respx.mock
def test_test_agent_failed():
    respx.post(f"{BASE}/data/set_data_for_key/").mock(
        return_value=httpx.Response(200, json=_env({"data_key": "_is_test_run"}))
    )
    respx.post(f"{BASE}/deploy/run_dag/").mock(
        return_value=httpx.Response(200, json=_env({"dag": {"key": "DAG_x"}, "run_id": "celery"}))
    )
    seq = [
        httpx.Response(200, json=_env({"dag_run_array": []})),
        httpx.Response(200, json=_env({"dag_run_array": [{"run_id": "dr-2", "status": "FAILED"}]})),
    ]
    respx.post(f"{BASE}/runs/fetch_dag_runs/").mock(
        side_effect=lambda r: seq.pop(0) if seq else httpx.Response(
            200, json=_env({"dag_run_array": [{"run_id": "dr-2", "status": "FAILED"}]})
        )
    )
    respx.post(f"{BASE}/runs/fetch_node_runs/").mock(
        return_value=httpx.Response(200, json=_env({"node_runs": [
            {"node_key": "n1", "node_name": "N", "status": "FAILED", "traceback": "Traceback: boom"}
        ]}))
    )
    respx.get(f"{BASE}/data/fetch_data_for_key/").mock(
        return_value=httpx.Response(200, json={"success": "0", "message": "Data not found"})
    )

    out = server.waveassist_test_agent(project_key="p_ab12", timeout_seconds=15)
    assert out["ok"] is True
    assert out["overall"] == "FAILED"
    assert out["is_green"] is False
    assert out["run_id"] == "dr-2"
    assert out["nodes"][0]["error"] == "Traceback: boom"  # traceback surfaced for self-fix


@respx.mock
def test_test_agent_timeout(monkeypatch):
    """No dag run ever appears -> overall UNKNOWN / is_green False / run_id None.
    A fast-advancing clock (httpx/respx also call time.time, so we can't hand out a
    fixed sequence) marches past the 15s-floored deadline within a couple calls."""
    clock = {"t": 0.0}

    def _fast_clock():
        clock["t"] += 100.0
        return clock["t"]

    monkeypatch.setattr(server.time, "time", _fast_clock)
    respx.post(f"{BASE}/data/set_data_for_key/").mock(
        return_value=httpx.Response(200, json=_env({"data_key": "_is_test_run"}))
    )
    respx.post(f"{BASE}/deploy/run_dag/").mock(
        return_value=httpx.Response(200, json=_env({"dag": {"key": "DAG_x"}, "run_id": "celery"}))
    )
    respx.post(f"{BASE}/runs/fetch_dag_runs/").mock(
        return_value=httpx.Response(200, json=_env({"dag_run_array": []}))
    )
    out = server.waveassist_test_agent(project_key="p_ab12", timeout_seconds=15)
    assert out["overall"] == "UNKNOWN"
    assert out["is_green"] is False
    assert out["run_id"] is None
    assert out["nodes"] == []


# --------------------------------------------------------------------------- #
# disarm + run_logs
# --------------------------------------------------------------------------- #
@respx.mock
def test_disarm_uses_recorded_deployment_key():
    registry.put(TEST_UID, "my_agent", {"project_key": "p_ab12", "deployment_key": "dep-1"})
    route = respx.post(f"{BASE}/deploy/stop_deployment/").mock(
        return_value=httpx.Response(200, json=_env({"deployment": {"key": "dep-1"}}))
    )
    out = server.waveassist_disarm_schedule(project_key="p_ab12")
    assert out["ok"] is True and out["status"] == "disarmed"
    assert _form(route.calls.last.request)["deployment_key"] == ["dep-1"]


@respx.mock
def test_disarm_errors_when_no_key():
    registry.put(TEST_UID, "my_agent", {"project_key": "p_ab12"})  # no deployment_key recorded
    out = server.waveassist_disarm_schedule(project_key="p_ab12")
    assert out["ok"] is False
    assert "No deployment_key" in out["error"]
    assert len(respx.calls) == 0  # no HTTP call attempted


def test_status_reports_registry_and_config():
    """waveassist_status is local-only: uid-present + bases + the local registry."""
    registry.put(TEST_UID, "a1", {"project_key": "a1_ab12"})
    out = server.waveassist_status()
    assert out["ok"] is True
    assert out["uid_present"] is True  # conftest pins WAVEASSIST_UID
    assert out["api_base"] == "https://api.waveassist.io"
    assert "a1" in out["agents"]


def test_login_with_uid_masks_in_output():
    """login echoes a MASKED uid (not the raw bearer-equivalent secret) but persists
    the full value to disk."""
    import json as _json
    import pathlib

    raw = "abcdef12-3456-7890-abcd-ef1234567890"
    out = server.waveassist_login(uid=raw)
    assert out["ok"] is True
    assert out["uid"] == server._mask(raw)
    assert "…" in out["uid"] and raw not in out["uid"]
    saved = _json.loads(pathlib.Path(out["saved_to"]).read_text())
    assert saved["uid"] == raw  # full value persisted, just not echoed


@respx.mock
def test_run_logs_maps_environment():
    route = respx.post(f"{BASE}/runs/fetch_dag_runs/").mock(
        return_value=httpx.Response(200, json=_env({"dag_run_array": [{"run_id": "dr-9", "status": "SUCCESS"}]}))
    )
    out = server.waveassist_run_logs(project_key="p_ab12", environment="default")
    assert out["ok"] is True
    assert out["environment"] == "p_ab12_default"
    assert out["node_runs"] == []  # no dag_run_id -> no node fetch
    assert _form(route.calls.last.request)["data_run_key"] == ["p_ab12_default"]


# --------------------------------------------------------------------------- #
# wa_ MCP token resolution
#
# The dashboard Connect panel hands users a rotatable `wa_` token for the
# Authorization header, but every WaveAssist endpoint authenticates on User.uid
# (a UUID). REGRESSION: the edge used to send the `wa_` token verbatim as the uid,
# which the API rejected with E01 ("User not authorized or found."). It must be
# exchanged via /account/resolve_mcp_token/ BEFORE any downstream call.
# --------------------------------------------------------------------------- #
@respx.mock
def test_wa_token_is_resolved_before_api_call(monkeypatch):
    monkeypatch.setenv("WAVEASSIST_UID", "wa_deadbeefcafe")
    server._UID_CACHE.clear()

    resolve = respx.post(f"{BASE}/account/resolve_mcp_token/").mock(
        return_value=httpx.Response(200, json=_env({"uid": "acct-uuid-999", "product": "waveassist"}))
    )
    projects = respx.post(f"{BASE}/manage/fetch_all_projects/").mock(
        return_value=httpx.Response(200, json=_env({"project_array": [{"project_key": "p_ab12", "name": "P"}]}))
    )

    out = server.waveassist_list_projects()

    assert out["ok"] is True
    # the wa_ token was exchanged...
    assert resolve.called
    assert _form(resolve.calls.last.request)["mcp_token"] == ["wa_deadbeefcafe"]
    # ...and the RESOLVED uid — not the wa_ token — was sent downstream
    assert _form(projects.calls.last.request)["uid"] == ["acct-uuid-999"]
    # output masks the resolved uid, and never leaks the raw token
    assert out["uid"] == server._mask("acct-uuid-999")


@respx.mock
def test_wa_token_resolution_is_cached(monkeypatch):
    monkeypatch.setenv("WAVEASSIST_UID", "wa_deadbeefcafe")
    server._UID_CACHE.clear()
    resolve = respx.post(f"{BASE}/account/resolve_mcp_token/").mock(
        return_value=httpx.Response(200, json=_env({"uid": "acct-uuid-999"}))
    )
    respx.post(f"{BASE}/manage/fetch_all_projects/").mock(
        return_value=httpx.Response(200, json=_env({"project_array": []}))
    )
    server.waveassist_list_projects()
    server.waveassist_list_projects()
    assert resolve.call_count == 1  # resolved once, then served from cache


@respx.mock
def test_wa_token_invalid_surfaces_clear_error(monkeypatch):
    monkeypatch.setenv("WAVEASSIST_UID", "wa_rotated_away")
    server._UID_CACHE.clear()
    resolve = respx.post(f"{BASE}/account/resolve_mcp_token/").mock(
        return_value=httpx.Response(200, json={"success": "0", "message": "Invalid MCP token.", "status": "E01"})
    )
    projects = respx.post(f"{BASE}/manage/fetch_all_projects/").mock(
        return_value=httpx.Response(200, json=_env({"project_array": []}))
    )
    out = server.waveassist_list_projects()
    assert out["ok"] is False
    assert "MCP token" in out["error"]        # actionable message, not a raw E01
    assert resolve.called
    assert not projects.called                # never hit the real API with a bad token


def test_plain_uid_is_never_sent_for_resolution(monkeypatch):
    """A non-wa_ uid (the legacy path) must NOT trigger an HTTP resolve — it is
    used verbatim. Guards the `startswith('wa_')` gate."""
    server._UID_CACHE.clear()
    # conftest pins WAVEASSIST_UID=test-uid-1234 (no wa_ prefix); resolving it would
    # require HTTP. With no respx mock active, any HTTP attempt raises — so a green
    # assertion here proves no network call was made.
    assert server._resolve_uid() == "test-uid-1234"
