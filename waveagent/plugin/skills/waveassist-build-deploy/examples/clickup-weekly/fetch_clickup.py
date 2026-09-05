"""
FetchClickUp — pull ClickUp tasks updated in the last 7 days across the user's
workspaces. Reads the ClickUp personal API token from the KV store (clickup_token)
and stores the collected tasks for the email node.

No Composio, no call_tool: plain requests + a key the user put in the KV store.

IMPORTANT runtime contract: the platform wraps this whole file into a
`def run_task():` and calls it. So:
  * do NOT use exit()/sys.exit()/raise SystemExit — that aborts before the worker
    records the node as finished (it gets stuck "STARTED"). Use if/else and let the
    code fall through to the end.
  * helper functions may `return`; the top-level orchestration must not.
"""
import time

import requests
import waveassist

waveassist.init()

API_BASE = "https://api.clickup.com/api/v2"
DEFAULT_LOOKBACK_DAYS = 7  # "weekly"; override via the lookback_days KV variable


def classify_http_error(status_code: int) -> str:
    if status_code in (401, 403):
        return ("Your ClickUp token was rejected (401/403). Generate a new personal "
                "token at https://app.clickup.com/settings/apps and update the "
                "clickup_token setting.")
    if status_code == 429:
        return "ClickUp rate limit hit (429). It will retry on the next run."
    if status_code >= 500:
        return f"ClickUp had a server error ({status_code}). It will retry on the next run."
    return f"ClickUp request failed ({status_code})."


def error_output(message: str) -> dict:
    return {
        "html_content": (
            "<div style=\"font-family:Inter,-apple-system,sans-serif;padding:16px;\">"
            "<h2 style=\"font-size:18px;margin:0 0 6px;\">ClickUp summary could not run</h2>"
            f"<p style=\"font-size:14px;color:#444;\">{message}</p></div>"
        ),
        "type": "error",
    }


def fetch_json(url: str, headers: dict, params: dict = None) -> dict:
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(classify_http_error(resp.status_code))
    return resp.json()


def collect_tasks(token: str, lookback_days: int):
    """Return (tasks, error_message). Never raises."""
    headers = {"Authorization": token}  # ClickUp uses the raw token, NOT Bearer.
    cutoff_ms = int((time.time() - lookback_days * 86400) * 1000)
    tasks = []
    try:
        teams = fetch_json(f"{API_BASE}/team", headers).get("teams", [])
        print(f"ClickUp: found {len(teams)} workspace(s).")
        for team in teams:
            team_id = team.get("id")
            params = {"date_updated_gt": cutoff_ms, "subtasks": "true", "order_by": "updated"}
            try:
                data = fetch_json(f"{API_BASE}/team/{team_id}/task", headers, params=params)
            except RuntimeError as exc:
                print(f"ClickUp: workspace {team_id} task fetch failed: {exc}")
                continue
            for t in data.get("tasks", []):
                tasks.append({
                    "name": t.get("name", "(untitled)"),
                    "status": (t.get("status") or {}).get("status", ""),
                    "assignees": [a.get("username", "") for a in (t.get("assignees") or [])],
                    "url": t.get("url", ""),
                    "list": (t.get("list") or {}).get("name", ""),
                    "workspace": team.get("name", ""),
                })
        return tasks, ""
    except RuntimeError as exc:
        return tasks, str(exc)
    except Exception as exc:  # noqa: BLE001
        return tasks, f"Unexpected error talking to ClickUp: {exc}"


# orchestration (flat — falls through to the end, no early exit)
print("ClickUp: starting fetch...")
token = waveassist.fetch_data("clickup_token", default="")
collected = []
error_message = ""

if not token:
    error_message = ("No ClickUp token is set. Add your personal API token in the "
                     "assistant settings (clickup_token).")
    print("ClickUp: no token configured.")
else:
    try:
        lookback_days = int(waveassist.fetch_data("lookback_days", default=DEFAULT_LOOKBACK_DAYS)
                            or DEFAULT_LOOKBACK_DAYS)
    except Exception:  # noqa: BLE001
        lookback_days = DEFAULT_LOOKBACK_DAYS
    print(f"ClickUp: lookback window = {lookback_days} day(s).")
    collected, error_message = collect_tasks(token, lookback_days)

if error_message and not collected:
    print(f"ClickUp: finishing with error — {error_message}")
    waveassist.store_data("clickup_error", error_message, data_type="string")
    waveassist.store_data("display_output", error_output(error_message), run_based=True, data_type="json")
else:
    print(f"ClickUp: collected {len(collected)} recently-updated task(s).")
    waveassist.store_data("clickup_tasks", collected, data_type="json")
    waveassist.store_data("clickup_error", "", data_type="string")

print("ClickUp: done.")
