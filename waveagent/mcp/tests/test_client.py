"""Unit tests for the thin HTTP client (waveassist_mcp.client).

All HTTP is mocked with respx against the production base
``https://api.waveassist.io``. We assert on the *recorded* requests where
encoding/shape matters (JSON vs form), and we exercise the response-envelope
rules from docs/api-contracts.md: every endpoint returns HTTP 200, success is
the *string* field ``"success" == "1"/"0"``, and the path-style fetch returns a
bare body with no envelope.
"""
from __future__ import annotations

import json
from urllib.parse import parse_qs

import httpx
import pytest
import respx

from waveassist_mcp.client import WaveAssistClient, WaveAssistError

BASE = "https://api.waveassist.io"


@pytest.fixture
def client():
    c = WaveAssistClient(base_url=BASE)
    try:
        yield c
    finally:
        c.close()


# --------------------------------------------------------------------------- #
# _parse — envelope handling
# --------------------------------------------------------------------------- #
def test_parse_returns_data_on_success():
    """success == "1" -> returns body['data']."""
    resp = httpx.Response(200, json={"success": "1", "data": {"hello": "world"}})
    assert WaveAssistClient._parse(resp) == {"hello": "world"}


def test_parse_raises_on_failure_envelope_even_with_http_200():
    """success == "0" (HTTP still 200) -> raises WaveAssistError w/ message+status."""
    resp = httpx.Response(
        200,
        json={"success": "0", "message": "Boom went the dynamite", "status": "E07"},
    )
    with pytest.raises(WaveAssistError) as ei:
        WaveAssistClient._parse(resp)
    err = ei.value
    assert err.message == "Boom went the dynamite"
    assert err.status == "E07"
    assert err.body == {"success": "0", "message": "Boom went the dynamite", "status": "E07"}


def test_parse_returns_bare_body_when_no_success_key():
    """Path-style fetch returns a bare object (no envelope) -> returned as-is."""
    resp = httpx.Response(200, json={"data": [1, 2, 3], "data_type": "json"})
    assert WaveAssistClient._parse(resp) == {"data": [1, 2, 3], "data_type": "json"}


def test_parse_allow_failure_returns_body_instead_of_raising():
    resp = httpx.Response(200, json={"success": "0", "message": "nope"})
    out = WaveAssistClient._parse(resp, allow_failure=True)
    assert out == {"success": "0", "message": "nope"}


# --------------------------------------------------------------------------- #
# materialize_assistant — JSON body carrying code_files
# --------------------------------------------------------------------------- #
@respx.mock
def test_materialize_assistant_posts_json(client):
    route = respx.post(f"{BASE}/api/v1/wavemaker/materialize_assistant").mock(
        return_value=httpx.Response(
            200,
            json={"success": "1", "data": {"repo_url": "https://github.com/wa/x", "is_update": False, "files_pushed": 3}},
        )
    )
    out = client.materialize_assistant(
        uid="test-uid-1234",
        assistant_name="My Agent",
        config_yaml="name: x\n",
        code_files={"main.py": "print('hi')"},
        readme_md="# readme",
    )
    assert out == {"repo_url": "https://github.com/wa/x", "is_update": False, "files_pushed": 3}

    req = route.calls.last.request
    assert "application/json" in req.headers["content-type"]
    sent = json.loads(req.content)
    assert sent["code_files"] == {"main.py": "print('hi')"}
    assert sent["assistant_name"] == "My Agent"
    assert sent["uid"] == "test-uid-1234"


@respx.mock
def test_materialize_drops_none_values(client):
    """existing_repo_url=None should not be sent as a key at all."""
    route = respx.post(f"{BASE}/api/v1/wavemaker/materialize_assistant").mock(
        return_value=httpx.Response(200, json={"success": "1", "data": {"repo_url": "r"}})
    )
    client.materialize_assistant(
        uid="u", assistant_name="A", config_yaml="y", code_files={"n.py": "x"}
    )
    sent = json.loads(route.calls.last.request.content)
    assert "existing_repo_url" not in sent
    assert "readme_md" not in sent


# --------------------------------------------------------------------------- #
# form-encoded endpoints
# --------------------------------------------------------------------------- #
@respx.mock
def test_deploy_template_posts_form(client):
    route = respx.post(f"{BASE}/template/deploy_template/").mock(
        return_value=httpx.Response(200, json={"success": "1", "data": {"project_key": "myagent_ab12"}})
    )
    out = client.deploy_template(uid="u", repo_url="https://github.com/wa/x")
    assert out == {"project_key": "myagent_ab12"}

    req = route.calls.last.request
    assert req.headers["content-type"].startswith("application/x-www-form-urlencoded")
    form = parse_qs(req.content.decode())
    assert form["repo_url"] == ["https://github.com/wa/x"]
    assert form["should_install_requirements"] == ["1"]
    assert form["timezone"] == ["UTC"]


@respx.mock
def test_run_dag_posts_form(client):
    route = respx.post(f"{BASE}/deploy/run_dag/").mock(
        return_value=httpx.Response(
            200,
            json={"success": "1", "data": {"dag": {"key": "DAG_x", "is_running": True}, "run_id": "celery-123"}},
        )
    )
    out = client.run_dag(uid="u", project_key="p", data_run_key="p_test")
    assert out["run_id"] == "celery-123"
    assert out["dag"]["key"] == "DAG_x"

    req = route.calls.last.request
    assert req.headers["content-type"].startswith("application/x-www-form-urlencoded")
    form = parse_qs(req.content.decode())
    assert form["data_run_key"] == ["p_test"]
    # start_node_key is None -> dropped
    assert "start_node_key" not in form


@respx.mock
def test_deploy_project_posts_form(client):
    route = respx.post(f"{BASE}/deploy/deploy_project/").mock(
        return_value=httpx.Response(
            200, json={"success": "1", "data": {"deployment": {"key": "dep-1"}}}
        )
    )
    out = client.deploy_project(uid="u", project_key="p", data_run_key="p_default", version="v1")
    assert out == {"deployment": {"key": "dep-1"}}

    req = route.calls.last.request
    assert req.headers["content-type"].startswith("application/x-www-form-urlencoded")
    form = parse_qs(req.content.decode())
    assert form["version"] == ["v1"]
    assert form["data_run_key"] == ["p_default"]


# --------------------------------------------------------------------------- #
# fetch_all_projects — live project list (uid is the token)
# --------------------------------------------------------------------------- #
@respx.mock
def test_fetch_all_projects_unwraps_project_array(client):
    """POST /manage/fetch_all_projects/ with just uid -> returns project_array."""
    route = respx.post(f"{BASE}/manage/fetch_all_projects/").mock(
        return_value=httpx.Response(
            200,
            json={
                "success": "1",
                "data": {
                    "project_array": [
                        {"project_key": "a_ab12", "name": "A", "github_url": "https://github.com/wa/a"},
                        {"project_key": "b_cd34", "name": "B", "github_url": ""},
                    ]
                },
            },
        )
    )
    out = client.fetch_all_projects(uid="test-uid-1234")
    assert out == [
        {"project_key": "a_ab12", "name": "A", "github_url": "https://github.com/wa/a"},
        {"project_key": "b_cd34", "name": "B", "github_url": ""},
    ]
    req = route.calls.last.request
    assert req.headers["content-type"].startswith("application/x-www-form-urlencoded")
    assert parse_qs(req.content.decode())["uid"] == ["test-uid-1234"]


@respx.mock
def test_fetch_all_projects_empty_when_missing_key(client):
    respx.post(f"{BASE}/manage/fetch_all_projects/").mock(
        return_value=httpx.Response(200, json={"success": "1", "data": {}})
    )
    assert client.fetch_all_projects(uid="u") == []


# --------------------------------------------------------------------------- #
# fetch_data_for_key — None on "Data not found"
# --------------------------------------------------------------------------- #
@respx.mock
def test_fetch_data_for_key_returns_none_on_not_found(client):
    respx.get(f"{BASE}/data/fetch_data_for_key/").mock(
        return_value=httpx.Response(
            200, json={"success": "0", "message": "Data not found", "status": "404"}
        )
    )
    out = client.fetch_data_for_key(
        uid="u", project_key="p", data_run_key="p_test", data_key="missing"
    )
    assert out is None


@respx.mock
def test_fetch_data_for_key_unwraps_data_envelope(client):
    """Success returns data={"data": value, "data_type": ...}; client unwraps to value."""
    respx.get(f"{BASE}/data/fetch_data_for_key/").mock(
        return_value=httpx.Response(
            200,
            json={"success": "1", "data": {"data": "hello", "data_type": "string"}},
        )
    )
    out = client.fetch_data_for_key(
        uid="u", project_key="p", data_run_key="p_test", data_key="greeting"
    )
    assert out == "hello"


# --------------------------------------------------------------------------- #
# fetch_dag_runs / fetch_node_runs — nested-array unwrapping
# --------------------------------------------------------------------------- #
@respx.mock
def test_fetch_dag_runs_unwraps_nested_array(client):
    respx.post(f"{BASE}/runs/fetch_dag_runs/").mock(
        return_value=httpx.Response(
            200,
            json={"success": "1", "data": {"dag_run_array": [{"id": "r1"}, {"id": "r2"}]}},
        )
    )
    out = client.fetch_dag_runs(uid="u", project_key="p", data_run_key="p_test")
    assert out == [{"id": "r1"}, {"id": "r2"}]


@respx.mock
def test_fetch_dag_runs_empty_when_missing_key(client):
    respx.post(f"{BASE}/runs/fetch_dag_runs/").mock(
        return_value=httpx.Response(200, json={"success": "1", "data": {}})
    )
    assert client.fetch_dag_runs(uid="u", project_key="p", data_run_key="p_test") == []


@respx.mock
def test_fetch_node_runs_unwraps_nested_array(client):
    respx.post(f"{BASE}/runs/fetch_node_runs/").mock(
        return_value=httpx.Response(
            200,
            json={
                "success": "1",
                "data": {"node_runs": [{"node_key": "n1", "status": "SUCCESS"}]},
            },
        )
    )
    out = client.fetch_node_runs(
        uid="u", project_key="p", data_run_key="p_test", dag_run_id="r1"
    )
    assert out == [{"node_key": "n1", "status": "SUCCESS"}]


# --------------------------------------------------------------------------- #
# resolve_mcp_token — wa_ token -> account uid
# --------------------------------------------------------------------------- #
@respx.mock
def test_resolve_mcp_token_returns_account_uid(client):
    """POST /account/resolve_mcp_token/ with the wa_ token -> returns data['uid']."""
    route = respx.post(f"{BASE}/account/resolve_mcp_token/").mock(
        return_value=httpx.Response(
            200, json={"success": "1", "data": {"uid": "acct-uuid-999", "product": "waveassist"}}
        )
    )
    assert client.resolve_mcp_token("wa_deadbeefcafe") == "acct-uuid-999"
    assert parse_qs(route.calls.last.request.content.decode())["mcp_token"] == ["wa_deadbeefcafe"]


@respx.mock
def test_resolve_mcp_token_raises_on_invalid(client):
    """A rotated/unknown token -> the failure envelope raises WaveAssistError."""
    respx.post(f"{BASE}/account/resolve_mcp_token/").mock(
        return_value=httpx.Response(
            200, json={"success": "0", "message": "Invalid MCP token.", "status": "E01"}
        )
    )
    with pytest.raises(WaveAssistError) as ei:
        client.resolve_mcp_token("wa_rotated_away")
    assert ei.value.status == "E01"
