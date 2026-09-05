"""One real (non-test) run that actually sends the email. Widens the window for a
rich summary, runs against the DEFAULT env with _is_test_run=false, polls to
SUCCESS, then restores the weekly (7-day) window.
"""
import os
import sys
import time

from waveassist_mcp.client import WaveAssistClient


def _need(k):
    v = os.environ.get(k)
    if not v:
        sys.exit(f"Set the {k} environment variable.")
    return v


def main():
    UID = _need("WAVEASSIST_UID")
    PROJECT = os.environ.get("PROJECT_KEY", "clickup_weekly_summary_a50d")
    ENV = f"{PROJECT}_default"
    WIDE = os.environ.get("LOOKBACK_DAYS", "400")

    c = WaveAssistClient()
    try:
        # rich window + REAL run (not a dry run)
        c.set_data_for_key(UID, PROJECT, ENV, "lookback_days", WIDE, "string")
        c.set_data_for_key(UID, PROJECT, ENV, "_is_test_run", "false", "string")

        before = {r.get("run_id") for r in c.fetch_dag_runs(UID, PROJECT, ENV)}
        run = c.run_dag(UID, PROJECT, ENV)
        print("run_dag ->", run.get("run_id"), "(celery id)")

        our, nodes, overall = None, [], None
        deadline = time.time() + 220
        while time.time() < deadline:
            time.sleep(3)
            fresh = [r for r in c.fetch_dag_runs(UID, PROJECT, ENV) if r.get("run_id") not in before]
            if not fresh:
                continue
            our = fresh[0]
            overall = our.get("status")
            try:
                nodes = c.fetch_node_runs(UID, PROJECT, ENV, our.get("run_id"))
            except Exception:  # noqa: BLE001
                nodes = []
            if overall in {"SUCCESS", "FAILED"}:
                break

        print("OVERALL:", overall)
        for n in nodes:
            print(f"  node {n.get('node_key'):<16} {n.get('status')}  {(n.get('traceback') or '')[:160]}")

        do = c.fetch_data_for_key(UID, PROJECT, ENV, "display_output", run_based=True, run_id=(our or {}).get("run_id")) \
            or c.fetch_data_for_key(UID, PROJECT, ENV, "display_output")
        print("display_output type:", (do or {}).get("type"))
        sent = bool(do) and (do.get("type") == "success")
        print("EMAIL SEND PATH EXECUTED:", sent)
    finally:
        # restore the product-correct weekly window for the live schedule
        c.set_data_for_key(UID, PROJECT, ENV, "lookback_days", "7", "string")
        c.close()
    print("restored default lookback_days = 7 (weekly)")


if __name__ == "__main__":
    main()
