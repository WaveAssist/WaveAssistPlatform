"""Thin HTTP client for the WaveAssist API.

Design notes (verified against the Django backend — see docs/api-contracts.md):
  * EVERY endpoint returns HTTP 200. Success/failure is the JSON `"success"`
    field ("1"/"0", a *string*). We branch on that, never on the HTTP status.
  * Auth is a plain `uid` field in the body/query — no header/JWT.
  * Some endpoints read `request.POST` directly and are FORM-ONLY
    (create_project, deploy_template, deploy_project, run_dag). Others accept
    form OR json. materialize_assistant needs JSON (it carries a dict).

This client is intentionally dumb: it shapes requests, parses the envelope, and
raises WaveAssistError on `success != "1"`. All reasoning lives in the skill.
"""
from __future__ import annotations

from typing import Any

import httpx

from . import config


class WaveAssistError(Exception):
    def __init__(self, message: str, status: Any = None, body: Any = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.body = body


class WaveAssistClient:
    def __init__(self, base_url: str | None = None, timeout: float = 60.0):
        self.base_url = (base_url or config.api_base()).rstrip("/")
        self._client = httpx.Client(timeout=timeout, follow_redirects=True)

    def close(self) -> None:
        self._client.close()

    # ------------------------------------------------------------------ #
    # envelope handling
    # ------------------------------------------------------------------ #
    @staticmethod
    def _parse(resp: httpx.Response, *, allow_failure: bool = False) -> Any:
        try:
            body = resp.json()
        except Exception:
            raise WaveAssistError(
                f"Non-JSON response (HTTP {resp.status_code}): {resp.text[:300]}"
            )
        # The path-style fetch_data returns a bare object (no envelope).
        if not isinstance(body, dict) or "success" not in body:
            return body
        if body.get("success") == "1":
            return body.get("data")
        if allow_failure:
            return body
        raise WaveAssistError(
            body.get("message") or "Request failed",
            status=body.get("status"),
            body=body,
        )

    def _post_form(self, path: str, data: dict, *, timeout: float | None = None) -> Any:
        # Drop None values so we don't send the literal string "None".
        clean = {k: v for k, v in data.items() if v is not None}
        resp = self._client.post(f"{self.base_url}{path}", data=clean, timeout=timeout)
        return self._parse(resp)

    def _post_json(self, path: str, payload: dict, *, timeout: float | None = None) -> Any:
        clean = {k: v for k, v in payload.items() if v is not None}
        resp = self._client.post(f"{self.base_url}{path}", json=clean, timeout=timeout)
        return self._parse(resp)

    def _get(self, path: str, params: dict, *, allow_failure: bool = False) -> Any:
        clean = {k: v for k, v in params.items() if v is not None}
        resp = self._client.get(f"{self.base_url}{path}", params=clean)
        return self._parse(resp, allow_failure=allow_failure)

    # ------------------------------------------------------------------ #
    # auth / login
    # ------------------------------------------------------------------ #
    def cli_login_status(self, session_id: str) -> str | None:
        """Poll the CLI-login session. Returns the uid string once ready, else None."""
        body = self._get(
            f"/cli_login/session/{session_id}/status", {}, allow_failure=True
        )
        if isinstance(body, dict):
            if body.get("success") == "1":
                data = body.get("data")
                return data if isinstance(data, str) and data else None
            return None
        return None

    # ------------------------------------------------------------------ #
    # projects + code + deploy
    # ------------------------------------------------------------------ #
    def materialize_assistant(
        self,
        uid: str,
        assistant_name: str,
        config_yaml: str,
        code_files: dict[str, str],
        readme_md: str | None = None,
        existing_repo_url: str | None = None,
    ) -> dict:
        """Push config.yaml + node files to a GitHub repo. Returns {repo_url, is_update, files_pushed}."""
        return self._post_json(
            "/api/v1/wavemaker/materialize_assistant",
            {
                "uid": uid,
                "assistant_name": assistant_name,
                "config_yaml": config_yaml,
                "code_files": code_files,
                "readme_md": readme_md,
                "existing_repo_url": existing_repo_url,
            },
            timeout=180.0,
        )

    def deploy_template(
        self,
        uid: str,
        repo_url: str,
        target_project_key: str | None = None,
        timezone: str = "UTC",
        should_install_requirements: bool = True,
    ) -> dict:
        """Install nodes from a repo into a project (UNARMED — no schedule fires). Returns the project dict."""
        return self._post_form(
            "/template/deploy_template/",
            {
                "uid": uid,
                "repo_url": repo_url,
                "target_project_key": target_project_key,
                "timezone": timezone,
                "should_install_requirements": "1" if should_install_requirements else "0",
            },
            timeout=180.0,
        )

    def upgrade_assistant(
        self, uid: str, project_key: str, data_run_key: str | None = None, timezone: str = "UTC"
    ) -> dict:
        """Re-create nodes from the latest commit on the project's repo. Returns {new_sha, commit_message}."""
        return self._post_form(
            "/assistant/upgrade/",
            {
                "uid": uid,
                "project_key": project_key,
                "data_run_key": data_run_key,
                "timezone": timezone,
            },
            timeout=180.0,
        )

    def check_update(self, uid: str, project_key: str) -> dict:
        return self._post_form(
            "/assistant/check_update/", {"uid": uid, "project_key": project_key}
        )

    def fetch_all_projects(self, uid: str) -> list:
        """List the user's projects (the uid is the token). Returns the
        project_array (each dict carries project_key, name, github_url, …), or
        [] if absent."""
        data = self._post_form("/manage/fetch_all_projects/", {"uid": uid})
        return (data or {}).get("project_array", []) if isinstance(data, dict) else []

    # ------------------------------------------------------------------ #
    # key-value store
    # ------------------------------------------------------------------ #
    def set_data_for_key(
        self,
        uid: str,
        project_key: str,
        data_run_key: str,
        data_key: str,
        data: Any,
        data_type: str = "string",
    ) -> dict:
        return self._post_json(
            "/data/set_data_for_key/",
            {
                "uid": uid,
                "project_key": project_key,
                "data_run_key": data_run_key,
                "data_key": data_key,
                "data": data,
                "data_type": data_type,
            },
        )

    def fetch_data_for_key(
        self,
        uid: str,
        project_key: str,
        data_run_key: str,
        data_key: str,
        run_based: bool = False,
        run_id: str | None = None,
    ) -> Any:
        """Return the stored value, or None if not found."""
        try:
            data = self._get(
                "/data/fetch_data_for_key/",
                {
                    "uid": uid,
                    "project_key": project_key,
                    "data_run_key": data_run_key,
                    "data_key": data_key,
                    "run_based": "1" if run_based else "0",
                    "run_id": run_id,
                },
            )
        except WaveAssistError:
            return None
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return data

    # ------------------------------------------------------------------ #
    # run / test / schedule
    # ------------------------------------------------------------------ #
    def run_dag(
        self, uid: str, project_key: str, data_run_key: str, start_node_key: str | None = None
    ) -> dict:
        """Fire a one-off (unscheduled) DAG run. Returns {dag:{key,is_running}, run_id}."""
        return self._post_form(
            "/deploy/run_dag/",
            {
                "uid": uid,
                "project_key": project_key,
                "data_run_key": data_run_key,
                "start_node_key": start_node_key,
            },
            timeout=120.0,
        )

    def fetch_dag_runs(self, uid: str, project_key: str, data_run_key: str) -> list:
        data = self._post_form(
            "/runs/fetch_dag_runs/",
            {"uid": uid, "project_key": project_key, "data_run_key": data_run_key},
        )
        return (data or {}).get("dag_run_array", []) if isinstance(data, dict) else []

    def fetch_node_runs(
        self, uid: str, project_key: str, data_run_key: str, dag_run_id: str
    ) -> list:
        data = self._post_form(
            "/runs/fetch_node_runs/",
            {
                "uid": uid,
                "project_key": project_key,
                "data_run_key": data_run_key,
                "dag_run_id": dag_run_id,
            },
        )
        return (data or {}).get("node_runs", []) if isinstance(data, dict) else []

    def deploy_project(
        self, uid: str, project_key: str, data_run_key: str, version: str
    ) -> dict:
        """Arm the recurring schedule (creates PeriodicTask enabled=True). Returns {deployment:{...}}."""
        return self._post_form(
            "/deploy/deploy_project/",
            {
                "uid": uid,
                "project_key": project_key,
                "data_run_key": data_run_key,
                "version": version,
            },
            timeout=120.0,
        )

    def stop_deployment(
        self, uid: str, deployment_key: str, project_key: str | None = None, data_run_key: str | None = None
    ) -> dict:
        return self._post_form(
            "/deploy/stop_deployment/",
            {
                "uid": uid,
                "deployment_key": deployment_key,
                "project_key": project_key,
                "data_run_key": data_run_key,
            },
        )
