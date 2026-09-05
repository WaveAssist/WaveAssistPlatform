#!/usr/bin/env python3
"""Deterministic full-stack end-to-end test for the WaveAssist platform.

Proves the real path a run takes on a live Compose deployment:

    HTTP webhook -> API -> Redis -> Celery worker -> SDK store/fetch -> API -> Mongo
                 -> worker events -> camera -> MySQL (DagRuns/NodeRuns) -> runs API

It imports a committed two-node DAG fixture, triggers it over HTTP, polls the run
to completion via the same endpoints the dashboard uses, and asserts the EXACT
final value read back through the data API. It does not grep logs for "SUCCESS".

Exit code 0 only if every assertion passes; nonzero otherwise. A machine-readable
JSON report is written to stdout (and to --report if given).

Prerequisites (see tests/e2e/README.md):
  * The stack is up and healthy, with the fixture mounted at /agents, e.g.
      AGENTS_DIR=./tests/e2e/fixtures COMPOSE_PROFILES=mcp \\
        docker-compose -p wa-verify up -d
  * An admin User+Account exists (WA_BOOTSTRAP_ADMIN=1 seeds it) whose celery_queue
    matches the worker's consumed queue.

Config via env or flags:
  API_BASE            (default http://localhost:8000)
  WAVEASSIST_ADMIN_UID(default boxadmin000000000000admin)
  E2E_COMPOSE         compose command prefix for the import step
                      (default "docker-compose -p wa-verify")
  E2E_AGENT_PATH      in-container fixture path (default /agents/two_node_dag)
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.parse

import requests

PROJECT = "e2e_two_node"
DATA_RUN = f"{PROJECT}_default"
START_NODE = "produce"
INPUT_N = 21
EXPECTED = INPUT_N * 2  # consume computes seed * 2


def redact(uid: str) -> str:
    return (uid[:4] + "…") if uid else ""


class E2EError(Exception):
    pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-base", default=os.getenv("API_BASE", "http://localhost:8000"))
    ap.add_argument("--uid", default=os.getenv("WAVEASSIST_ADMIN_UID", "boxadmin000000000000admin"))
    ap.add_argument("--timeout", type=int, default=int(os.getenv("E2E_TIMEOUT", "150")),
                    help="seconds to wait for the run to reach a terminal state")
    ap.add_argument("--no-import", action="store_true",
                    help="skip deploy_local_agent (fixture already imported)")
    ap.add_argument("--report", default=os.getenv("E2E_REPORT", ""))
    args = ap.parse_args()

    api = args.api_base.rstrip("/")
    uid = args.uid.strip()
    report = {"passed": False, "api_base": api, "uid": redact(uid), "project": PROJECT,
              "expected_final": EXPECTED, "steps": []}

    def step(name, ok, **extra):
        entry = {"step": name, "ok": bool(ok)}
        entry.update(extra)
        report["steps"].append(entry)
        return ok

    try:
        # 1. Readiness
        r = requests.get(f"{api}/health/ready/", timeout=10)
        if r.status_code != 200 or r.json().get("status") != "ready":
            raise E2EError(f"API not ready: {r.status_code} {r.text[:200]}")
        step("health_ready", True, status=r.status_code)

        # 2. Import the fixture agent (idempotent)
        if not args.no_import:
            compose = os.getenv("E2E_COMPOSE", "docker-compose -p wa-verify").split()
            agent_path = os.getenv("E2E_AGENT_PATH", "/agents/two_node_dag")
            cmd = compose + ["exec", "-T", "api", "python", "manage.py", "deploy_local_agent",
                             "--path", agent_path, "--uid", uid, "--project", PROJECT]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            out = (proc.stdout or "") + (proc.stderr or "")
            if proc.returncode != 0:
                raise E2EError(f"deploy_local_agent failed (rc={proc.returncode}): {out[-500:]}")
            step("import_agent", True, output=out.strip()[-300:])
        else:
            step("import_agent", True, skipped=True)

        # 3. Baseline existing runs (so we can identify OUR new run)
        def dag_runs():
            q = urllib.parse.urlencode({"uid": uid, "project_key": PROJECT, "data_run_key": DATA_RUN})
            rr = requests.get(f"{api}/runs/fetch_dag_runs/?{q}", timeout=15)
            rr.raise_for_status()
            data = rr.json().get("data", {}) or {}
            return data.get("dag_run_array", []) or []

        baseline_ids = {d.get("run_id") for d in dag_runs()}
        step("baseline_runs", True, count=len(baseline_ids))

        # 4. Trigger via HTTP webhook (POST body is stored as produce_webhook_data)
        trig = requests.post(
            f"{api}/webhook/run/{uid}/{PROJECT}/{START_NODE}/{DATA_RUN}/",
            json={"n": INPUT_N}, timeout=30)
        if trig.status_code != 200 or str(trig.json().get("success")) != "1":
            raise E2EError(f"trigger failed: {trig.status_code} {trig.text[:300]}")
        step("trigger_webhook", True, status=trig.status_code)

        # 5. Poll for the new DagRun to reach a terminal state
        deadline = time.time() + args.timeout
        new_run_id, status = None, None
        while time.time() < deadline:
            for d in dag_runs():
                rid = d.get("run_id")
                if rid and rid not in baseline_ids:
                    new_run_id, status = rid, d.get("status")
                    break
            if new_run_id and status in ("SUCCESS", "FAILED"):
                break
            time.sleep(2)
        if not new_run_id:
            raise E2EError("no new DagRun appeared (camera not recording, or task not consumed)")
        if status != "SUCCESS":
            # Pull node-level detail for diagnostics
            nr = requests.post(f"{api}/runs/fetch_node_runs/",
                               data={"uid": uid, "project_key": PROJECT,
                                     "data_run_key": DATA_RUN, "dag_run_id": new_run_id}, timeout=15)
            raise E2EError(f"run status={status!r}; node_runs={nr.text[:400]}")
        step("run_success", True, run_id=new_run_id, status=status)

        # 6. Assert both nodes recorded SUCCESS
        nr = requests.post(f"{api}/runs/fetch_node_runs/",
                           data={"uid": uid, "project_key": PROJECT,
                                 "data_run_key": DATA_RUN, "dag_run_id": new_run_id}, timeout=15)
        nr.raise_for_status()
        node_runs = (nr.json().get("data", {}) or {}).get("node_runs", []) or []
        statuses = {n.get("node_key"): n.get("status") for n in node_runs}
        if statuses.get("produce") != "SUCCESS" or statuses.get("consume") != "SUCCESS":
            raise E2EError(f"node statuses not all SUCCESS: {statuses}")
        step("node_runs_success", True, statuses=statuses)

        # 7. Read back the exact final value through the data API
        fr = requests.get(f"{api}/data/fetch_data/{uid}/{PROJECT}/{DATA_RUN}/final_result/", timeout=15)
        fr.raise_for_status()
        payload = fr.json()
        raw = payload.get("data")
        try:
            actual = int(raw)
        except (TypeError, ValueError):
            raise E2EError(f"final_result not numeric: {payload!r}")
        if actual != EXPECTED:
            raise E2EError(f"final_result {actual} != expected {EXPECTED}")
        step("assert_final_value", True, actual=actual, expected=EXPECTED, data_type=payload.get("data_type"))

        report["passed"] = True
        report["run_id"] = new_run_id

    except Exception as exc:  # noqa: BLE001 - report everything as a failed step
        report["error"] = f"{type(exc).__name__}: {exc}"
        step("FAILED", False, error=report["error"])

    out = json.dumps(report, indent=2)
    print(out)
    if args.report:
        with open(args.report, "w") as fh:
            fh.write(out)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
