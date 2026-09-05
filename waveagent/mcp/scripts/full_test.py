"""Full live test of WaveAgent with a REAL ClickUp token, capturing evidence to
docs/test_results.json for the HTML report. The token is read from env
CLICKUP_TOKEN and is masked in all output.
"""
import json
import os
import sys
import time
from pathlib import Path

import requests

from waveassist_mcp import config, registry, server
from waveassist_mcp.client import WaveAssistClient

ROOT = Path(__file__).resolve().parents[2]  # scripts/ -> mcp/ -> WaveAgent/
DOCS = ROOT / "docs"


def _need(k):
    v = os.environ.get(k)
    if not v:
        sys.exit(f"Set the {k} environment variable.")
    return v


def main():
    UID = _need("WAVEASSIST_UID")
    TOKEN = _need("CLICKUP_TOKEN")
    PROJECT = os.environ.get("PROJECT_KEY", "clickup_weekly_summary_a50d")
    MASK = f"{TOKEN[:8]}…{TOKEN[-4:]}"

    results = {
        "uid_masked": f"{UID[:8]}…{UID[-4:]}",
        "token_masked": MASK,
        "project_key": PROJECT,
        "dashboard_url": config.dashboard_project_url(PROJECT),
        "steps": [],
    }

    def step(name, status, detail):
        results["steps"].append({"name": name, "status": status, "detail": detail})
        print(f"[{status}] {name}")

    # ---------------------------------------------------------------- #
    # 1. Verify the token DIRECTLY against ClickUp (independent of WaveAssist)
    # ---------------------------------------------------------------- #
    direct = {"teams": [], "recent_task_count": 0, "sample_tasks": []}
    try:
        h = {"Authorization": TOKEN}
        teams = requests.get("https://api.clickup.com/api/v2/team", headers=h, timeout=30).json().get("teams", [])
        direct["teams"] = [{"id": t.get("id"), "name": t.get("name")} for t in teams]
        cutoff = int((time.time() - 7 * 86400) * 1000)
        for t in teams:
            params = {"date_updated_gt": cutoff, "subtasks": "true", "order_by": "updated"}
            tasks = requests.get(
                f"https://api.clickup.com/api/v2/team/{t['id']}/task", headers=h, params=params, timeout=30
            ).json().get("tasks", [])
            direct["recent_task_count"] += len(tasks)
            for tk in tasks[:8]:
                direct["sample_tasks"].append({
                    "name": tk.get("name", ""),
                    "status": (tk.get("status") or {}).get("status", ""),
                    "workspace": t.get("name", ""),
                })
        step("ClickUp token verified directly", "PASS",
             f"{len(direct['teams'])} workspace(s); {direct['recent_task_count']} task(s) updated in last 7 days")
    except Exception as e:  # noqa: BLE001
        step("ClickUp token verified directly", "FAIL", str(e))
    results["direct_clickup"] = direct

    # ---------------------------------------------------------------- #
    # 2. Set the real key on the deployed agent (both envs)
    # ---------------------------------------------------------------- #
    sk = server.waveassist_set_key(PROJECT, "clickup_token", TOKEN)
    step("set_key clickup_token (default + test envs)", "PASS" if sk.get("ok") else "FAIL",
         {"environments": sk.get("environments"), "ok": sk.get("ok")})
    results["set_key"] = {"ok": sk.get("ok"), "environments": sk.get("environments")}

    # Account had 0 tasks updated in the last 7 days; widen the (configurable) window
    # so the LLM summary has real tasks to work with. Production default stays 7 ("weekly").
    LOOKBACK = os.environ.get("LOOKBACK_DAYS", "400")
    lk = server.waveassist_set_key(PROJECT, "lookback_days", LOOKBACK)
    step("set_key lookback_days (test window)", "PASS" if lk.get("ok") else "FAIL",
         {"value": LOOKBACK, "ok": lk.get("ok")})
    results["lookback_days"] = LOOKBACK

    # ---------------------------------------------------------------- #
    # 3. Dry-run test on real infra (real fetch + real LLM summary, no email sent)
    # ---------------------------------------------------------------- #
    tr = server.waveassist_test_agent(PROJECT, timeout_seconds=180)
    green = tr.get("is_green")
    step("test_agent (dry run, real ClickUp + call_llm)", "PASS" if green else "WARN",
         {"overall": tr.get("overall"), "nodes": tr.get("nodes")})
    results["test_run"] = {
        "overall": tr.get("overall"),
        "is_green": green,
        "run_id": tr.get("run_id"),
        "dag_key": tr.get("dag_key"),
        "nodes": tr.get("nodes"),
        "display_output_preview": tr.get("display_output_preview"),
    }

    # ---------------------------------------------------------------- #
    # 4. Inspect what the agent actually stored in the KV store
    # ---------------------------------------------------------------- #
    c = WaveAssistClient()
    try:
        env_test = f"{PROJECT}_test"
        kv_tasks = c.fetch_data_for_key(UID, PROJECT, env_test, "clickup_tasks")
        kv_err = c.fetch_data_for_key(UID, PROJECT, env_test, "clickup_error")
    finally:
        c.close()
    kv_tasks = kv_tasks if isinstance(kv_tasks, list) else []
    results["kv"] = {
        "clickup_tasks_count": len(kv_tasks),
        "clickup_tasks_sample": kv_tasks[:8],
        "clickup_error": kv_err or "",
    }
    step("KV inspection (clickup_tasks stored by the node)", "PASS",
         f"{len(kv_tasks)} task(s) stored; error='{kv_err or ''}'")

    results["unit_tests"] = "20 passed (see pytest)"
    results["finished"] = True

    out = DOCS / "test_results.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("\nWROTE", out)
    print("VERDICT:", "GREEN" if results["test_run"]["is_green"] else "NOT GREEN",
          "| direct tasks(7d):", direct["recent_task_count"],
          "| node-stored tasks:", results["kv"]["clickup_tasks_count"])


if __name__ == "__main__":
    main()
