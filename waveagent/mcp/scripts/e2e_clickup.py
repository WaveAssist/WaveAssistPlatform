"""Live end-to-end driver for the ClickUp -> weekly-email demo.

Exercises the real MCP tool functions against the live WaveAssist API. Stages are
selected via argv so we can confirm a green test BEFORE arming the schedule:

    WAVEASSIST_UID=<uid> WAVEASSIST_HOME=/tmp/waveagent-e2e \
        python scripts/e2e_clickup.py deploy key test
    ... then ...
    WAVEASSIST_UID=<uid> WAVEASSIST_HOME=/tmp/waveagent-e2e \
        python scripts/e2e_clickup.py arm

This is a thin harness; the same calls happen when a coding agent drives the MCP
tools via the SKILL.
"""
import json
import sys
from pathlib import Path

from waveassist_mcp import registry, server

ROOT = Path(__file__).resolve().parents[2]  # scripts/ -> mcp/ -> WaveAgent/
EXAMPLE = ROOT / "examples/clickup-weekly"
SLUG = "clickup_weekly_summary"
NAME = "ClickUp Weekly Summary"
# Deliberately fake token: proves the full pipeline + error handling without a real
# ClickUp account. Swap for a real pk_... token to get a real summary.
CLICKUP_TOKEN = "pk_demo_not_a_real_token"


def show(label, obj):
    print(f"\n=== {label} ===")
    print(json.dumps(obj, indent=2, default=str))


def main(argv):
    stages = argv or ["deploy", "key", "test"]
    import waveassist_mcp.config as cfg
    print(f"api_base={cfg.api_base()}  uid={cfg.load_uid()}  home={cfg.CONFIG_DIR}")

    config_yaml = (EXAMPLE / "config.yaml").read_text()
    code_files = {
        "fetch_clickup.py": (EXAMPLE / "fetch_clickup.py").read_text(),
        "email_summary.py": (EXAMPLE / "email_summary.py").read_text(),
    }

    reg = registry.get(SLUG)
    project_key = reg.get("project_key") if reg else None

    if "deploy" in stages:
        res = server.waveassist_deploy_agent(
            name=NAME, config_yaml=config_yaml, code_files=code_files,
            description="ClickUp -> weekly email demo", slug=SLUG, timezone="UTC",
        )
        show("deploy_agent", res)
        if not res.get("ok"):
            return 1
        project_key = res["project_key"]

    if not project_key:
        print("No project_key yet; run the 'deploy' stage first.")
        return 1

    if "key" in stages:
        show("set_key clickup_token", server.waveassist_set_key(project_key, "clickup_token", CLICKUP_TOKEN))

    if "test" in stages:
        show("test_agent (dry run)", server.waveassist_test_agent(project_key, timeout_seconds=150))

    if "logs" in stages:
        show("run_logs", server.waveassist_run_logs(project_key, environment="test"))

    if "arm" in stages:
        show("arm_schedule", server.waveassist_arm_schedule(project_key))

    if "disarm" in stages:
        show("disarm_schedule", server.waveassist_disarm_schedule(project_key))

    print(f"\nproject_key = {project_key}")
    print(f"dashboard   = {cfg.dashboard_project_url(project_key)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
